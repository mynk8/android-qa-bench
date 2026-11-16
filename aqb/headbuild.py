"""Build APKs from ONE source tree per app: the pinned head plus forward-ported patches.

Plan: private/forwardport/plan.json  (build_id -> {app, patches: [bug ids]})
    patch for bug B: private/forwardport/B.patch

Per app, one persistent worktree (work/head/<app>) at the pinned head:
  1. the clean head is built first (full build, warms the incremental state)
  2. each later build: restore tracked files to the head, apply its patches,
     run Gradle. Only the touched sources recompile, so builds take seconds
     to a minute. Ignored build/ outputs are kept between builds on purpose.
Builds with the same patch set are built once and copied (every "-fixed"
build of an app is the clean head).

Same safety as aqb.build: one Gradle at a time per app, systemd memory cap,
waits for free RAM. Records land in artifacts/build_manifest.jsonl.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

from aqb.build import (DATASET, JDKS, MANIFEST, MEM_SCOPE, ROOT, SDK, TASKS, EXTRA_ARGS, classify_failure,
                       badging, find_apk, gradle_version, patch_tree, pick_jdk, record, sha256, wait_for_memory)

PLAN = ROOT / "private" / "forwardport" / "plan.json"
FP = ROOT / "private" / "forwardport"
HEAD_WT = ROOT / "work" / "head"


def _run(cmd, cwd, log, env=None, timeout=3600) -> int:
    log.write(f"\n$ {' '.join(map(str, cmd))}\n")
    log.flush()
    return subprocess.run(cmd, cwd=cwd, stdout=log, stderr=subprocess.STDOUT, env=env, timeout=timeout).returncode


def ensure_worktree(app: str, pin: str) -> Path:
    repo = ROOT / "private" / "apps" / app / "src"
    wt = HEAD_WT / app
    if not (wt / ".git").exists():
        wt.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "-C", str(repo), "worktree", "add", "--detach", "--force", str(wt), pin],
                       check=True, capture_output=True)
    return wt


def reset_to_head(wt: Path, pin: str, log) -> None:
    """Tracked files back to the head; untracked non-ignored files removed; build/ outputs kept."""
    _run(["git", "checkout", "-q", "--detach", "--force", pin], wt, log)
    _run(["git", "reset", "-q", "--hard", pin], wt, log)
    _run(["git", "clean", "-fdq"], wt, log)


def apply_patches(wt: Path, bugs: list[str], log, rec: dict) -> bool:
    rec["applied"] = {}
    for b in bugs:
        p = FP / f"{b}.patch"
        if _run(["git", "apply", "--whitespace=nowarn", str(p)], wt, log) == 0:
            rec["applied"][b] = "apply"
            continue
        # overlapping patches (same file): 3-way merge against the head
        if _run(["git", "apply", "--3way", "--whitespace=nowarn", str(p)], wt, log) == 0:
            conflicted = subprocess.run(["git", "diff", "--name-only", "--diff-filter=U"], cwd=wt,
                                        capture_output=True, text=True).stdout.split()
            if not conflicted:
                rec["applied"][b] = "apply --3way"
                continue
        rec["error"] = f"patch {b} does not combine with {list(rec['applied'])}"
        return False
    return True


def app_tree_patches(app: str, wt: Path) -> list[str]:
    """Build-only changes for this machine; recorded per APK. App code is untouched."""
    done = []
    if app == "amaze":
        toml = wt / "gradle" / "libs.versions.toml"
        installed = sorted(p.name for p in (SDK / "ndk").iterdir()) if (SDK / "ndk").exists() else []
        if installed and toml.exists():
            txt = toml.read_text()
            new = re.sub(r'^ndk = "[^"]+"', f'ndk = "{installed[-1]}"', txt, flags=re.M)
            if new != txt:
                toml.write_text(new)
                done.append(f"ndk -> installed {installed[-1]}")
        fo = wt / "file_operations" / "build.gradle"
        if fo.exists():
            txt = fo.read_text()
            new = re.sub(r'targets = \[[^\]]*\]', 'targets = ["x86_64"]', txt)
            if new != txt:
                fo.write_text(new)
                done.append("rust targets -> x86_64 only (emulator ABI)")
    return done


def gradle(app: str, wt: Path, log) -> tuple[str | None, str]:
    gv = gradle_version(wt)
    jdk = pick_jdk(gv)
    env = dict(os.environ, JAVA_HOME=str(jdk), ANDROID_HOME=str(SDK), ANDROID_SDK_ROOT=str(SDK),
               GRADLE_USER_HOME=str(ROOT / "work" / "gradle-home"), PATH=f"{jdk}/bin:{os.environ.get('PATH', '')}")
    installs = ",".join(str(JDKS / f"jdk{v}") for v in (11, 17, 21))
    (wt / "gradlew").chmod(0o755)
    for task in TASKS[app]:
        code = _run(MEM_SCOPE + ["./gradlew", task, "--no-daemon", "--console=plain", "-x", "lint", "--build-cache",
                                 f"-Porg.gradle.java.installations.paths={installs}",
                                 "-Porg.gradle.java.installations.auto-download=false",
                                 "--max-workers=2", "-Dorg.gradle.workers.max=2", "-Dorg.gradle.parallel=false",
                                 "-Dorg.gradle.jvmargs=-Xmx2g -XX:MaxMetaspaceSize=768m",
                                 "-Pkotlin.compiler.execution.strategy=in-process",
                                 "-Dkotlin.compiler.execution.strategy=in-process"] + EXTRA_ARGS.get(app, []),
                    wt, log, env=env)
        if code == 0:
            return task, f"{gv[0]}.{gv[1]}/{jdk.name}"
        if "not found in project" not in Path(log.name).read_text()[-4000:]:
            break
    return None, f"{gv[0]}.{gv[1]}/{jdk.name}"


def build_app(app: str, bids: list[str], plan: dict, log_print=print) -> list[dict]:
    pin = json.loads((DATASET / "apps" / app / "app.json").read_text())["pinned_commit"]
    pkg = json.loads((DATASET / "apps" / app / "app.json").read_text())["package"]
    wt = ensure_worktree(app, pin)
    # group identical patch sets; clean head first so it warms the incremental state
    groups: dict[tuple, list[str]] = {}
    for bid in bids:
        groups.setdefault(tuple(plan[bid]["patches"]), []).append(bid)
    order = sorted(groups, key=lambda k: (len(k), k))
    out = []
    for key in order:
        ids = groups[key]
        bid = ids[0]
        logp = ROOT / "work" / "logs" / "build" / f"{bid}.log"
        logp.parent.mkdir(parents=True, exist_ok=True)
        rec = {"build_id": bid, "app": app, "commit": pin, "base": "head", "patches_of": list(key),
               "copies": ids[1:], "log": str(logp.relative_to(ROOT)), "ok": False}
        t0 = time.time()
        wait_for_memory()
        with logp.open("w") as log:
            try:
                reset_to_head(wt, pin, log)
                if apply_patches(wt, list(key), log, rec):
                    rec["tree_patches"] = patch_tree(wt) + app_tree_patches(app, wt)
                    task, tool = gradle(app, wt, log)
                    rec["toolchain"] = tool
                    if task is None:
                        rec["error"] = classify_failure(logp.read_text()[-20000:])
                    else:
                        rec["task"] = task
                        apk = find_apk(wt, app)
                        b = badging(apk) if apk else {}
                        rec.update(b)
                        if apk is None:
                            rec["error"] = "no apk produced"
                        elif b and b.get("package") != pkg:
                            rec["error"] = f"package {b.get('package')} != {pkg}"
                        else:
                            dest = DATASET / "apps" / app / "builds"
                            for i in ids:
                                shutil.copy2(apk, dest / f"{i}.apk")
                            rec["sha256"] = sha256(dest / f"{bid}.apk")
                            rec["ok"] = True
            except subprocess.TimeoutExpired:
                rec["error"] = "timeout"
        rec["seconds"] = round(time.time() - t0, 1)
        record(rec)
        log_print(f"{'OK  ' if rec['ok'] else 'FAIL'} {bid:26} +{len(key)} patch {rec['seconds']}s "
                  f"{('-> ' + str(len(ids) - 1) + ' copies') if len(ids) > 1 else ''} {rec.get('error', '')}")
        out.append(rec)
    return out


def build(tier: str | None = "core", apps: set[str] | None = None, only: set[str] | None = None,
          rebuild: bool = False, dry_run: bool = False) -> int:
    plan = json.loads(PLAN.read_text())["builds"]
    todo: dict[str, list[str]] = {}
    for idxp in sorted((DATASET / "apps").glob("*/builds/index.json")):
        app = idxp.parts[-3]
        if apps and app not in apps:
            continue
        for bid, meta in json.loads(idxp.read_text()).items():
            if tier and meta.get("tier") != tier:
                continue
            if only and bid not in only:
                continue
            if not rebuild and meta.get("sha256") not in (None, "UNBUILT") and (idxp.parent / f"{bid}.apk").exists():
                continue
            todo.setdefault(app, []).append(bid)
    n_src = sum(len({tuple(plan[b]["patches"]) for b in v}) for v in todo.values())
    print(f"{sum(map(len, todo.values()))} APKs from {n_src} patch sets across {len(todo)} apps (one head each)",
          flush=True)
    if dry_run:
        for app, v in todo.items():
            print(f"  {app:12} {len(v)} APKs, {len({tuple(plan[b]['patches']) for b in v})} distinct builds")
        return 0
    fails = 0
    for app, bids in todo.items():  # strictly one app at a time
        fails += sum(1 for r in build_app(app, bids, plan, lambda s: print(s, flush=True)) if not r["ok"])
    print(f"done: {fails} failed. Manifest: {MANIFEST.relative_to(ROOT)}")
    return 1 if fails else 0
