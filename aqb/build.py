"""Build benchmark APKs from pinned commits.

Each index entry in dataset/apps/<app>/builds/index.json is built from
private/build/build_plan.json:
  buggy / fixed     -> `commit`
  episode_subset    -> `base_commit` with `revert_fixes` reverted (in order)

Reproducibility record: artifacts/build_manifest.jsonl gets one line per APK
(build id, commit, reverts, patches, JDK, Gradle task, sha256, package,
versionCode, seconds, log). Logs: work/logs/build/<build_id>.log.
Identical (commit, reverts) pairs are built once and copied.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "dataset"
PLAN = ROOT / "private" / "build" / "build_plan.json"
WORK = ROOT / "work"
MANIFEST = ROOT / "artifacts" / "build_manifest.jsonl"
JDKS = Path(os.environ.get("AQB_JDKS", Path.home() / ".local" / "jdks"))
SDK = Path(os.environ.get("ANDROID_HOME") or Path.home() / "Android" / "Sdk")

# Gradle task candidates per app, tried in order (flavor names changed over history).
TASKS = {
    "amaze": [":app:assembleFdroidDebug", ":app:assembleDebug"],
    "ankidroid": [":AnkiDroid:assembleFullDebug", ":AnkiDroid:assembleDebug"],
    "tasks": [":app:assembleGenericDebug", ":app:assembleDebug"],
    "markor": [":app:assembleFlavorDefaultDebug", ":app:assembleDebug"],
    "minus": [":app:assembleFossDebug", ":app:assembleDebug"],
    "iris": [":app:assembleDebug"],
    "featherline": [":app:assembleDebug"],
    "idlefantasy": [":app:assembleDebug"],
    "nerdcalci": [":app:assembleDebug"],
}
MODULE = {"ankidroid": "AnkiDroid"}
# Extra Gradle arguments per app.
# AnkiDroid copies git hooks into .git/hooks, which is a file inside a git worktree.
EXTRA_ARGS = {"ankidroid": ["-x", "installGitHook"],
              # a cached hiltJavaCompile output without the Hilt app injector was restored into patched builds
              "idlefantasy": ["-Pksp.incremental=false", "--no-build-cache"]}
# Apps whose old commits need artifacts rebuilt into work/m2 (see work/vendor/README.md).
VENDOR_APPS = {"amaze"}
VENDOR_M2 = ROOT / "work" / "m2"


@dataclass
class Job:
    app: str
    build_id: str
    commit: str
    reverts: list[str]
    out: Path
    extra_ids: list[str] = field(default_factory=list)  # same source, copied

    @property
    def key(self) -> str:
        return hashlib.sha1((self.commit + ":" + ",".join(self.reverts)).encode()).hexdigest()[:12]


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _vendored(coord: str) -> bool:
    g, a, v = coord.split(":")[:3]
    return (VENDOR_M2 / g.replace(".", "/") / a / v).is_dir()


def known_unbuildable() -> dict[str, str]:
    """Builds whose last attempt failed on rot we cannot fix (dependency gone and not
    vendored, or a native toolchain we don't provide). Retried only with --rebuild."""
    out: dict[str, str] = {}
    if not MANIFEST.exists():
        return out
    last = {}
    for line in MANIFEST.read_text().splitlines():
        r = json.loads(line)
        last[r["build_id"]] = r
    for bid, r in last.items():
        err = r.get("error") or ""
        m = re.match(r"missing dependency (\S+)", err)
        if (m and not _vendored(m.group(1))) or err.startswith("native Rust"):
            out[bid] = err
    return out


def load_jobs(tier: str | None, apps: set[str] | None, only: set[str] | None, rebuild: bool) -> list[Job]:
    plan = json.loads(PLAN.read_text())["builds"]
    skip = {} if rebuild else known_unbuildable()
    by_key: dict[tuple, Job] = {}
    # already-built APKs by source, so identical sources are copied, not rebuilt
    built: dict[tuple, Path] = {}
    for idxp in sorted((DATASET / "apps").glob("*/builds/index.json")):
        for bid, meta in json.loads(idxp.read_text()).items():
            apk = idxp.parent / f"{bid}.apk"
            pb = plan.get(bid, {})
            if apk.exists() and meta.get("sha256") not in (None, "UNBUILT") and not pb.get("revert_fixes"):
                built[(idxp.parts[-3], pb.get("commit") or pb.get("base_commit"), ())] = apk
    for idxp in sorted((DATASET / "apps").glob("*/builds/index.json")):
        app = idxp.parts[-3]
        if apps and app not in apps:
            continue
        for bid, meta in json.loads(idxp.read_text()).items():
            if tier and meta.get("tier") != tier:
                continue
            if only and bid not in only:
                continue
            out = idxp.parent / f"{bid}.apk"
            if out.exists() and not rebuild and meta.get("sha256") not in (None, "UNBUILT"):
                continue
            if bid in skip and not only:
                continue
            p = plan[bid]
            commit = p.get("commit") or p["base_commit"]
            reverts = list(p.get("revert_fixes") or [])
            alias = start_alias(app, meta, plan) if meta.get("tier") == "core" and reverts else None
            if rebuild:
                built.pop((app, alias or commit, ()), None)
            if alias:
                commit, reverts = alias, []
            k = (app, commit, tuple(reverts))
            same = built.get(k)
            if same is not None and same != out:
                shutil.copy2(same, out)
                record({"build_id": bid, "app": app, "commit": commit, "reverts": reverts, "copies": [],
                        "copied_from": same.stem, "ok": True, "sha256": sha256(out), "seconds": 0,
                        "strategy": "episode start = earliest bug's buggy commit" if alias else "same source"})
                continue
            if k in by_key:
                by_key[k].extra_ids.append(bid)
            else:
                by_key[k] = Job(app, bid, commit, reverts, out)
    return list(by_key.values())


def _commit_time(app: str, sha: str) -> int:
    out = subprocess.run(["git", "show", "-s", "--format=%ct", sha], cwd=ROOT / "private" / "apps" / app / "src",
                         capture_output=True, text=True)
    return int(out.stdout.strip() or 0)


def start_alias(app: str, meta: dict, plan: dict) -> str | None:
    """Episode start build (all bugs present) without reverts.

    The parent of the earliest fix among the episode's bugs predates every
    other fix, so all episode bugs are unfixed there; that is the earliest
    bug's own buggy commit (already built for cases). Calibration confirms
    each bug's target check fails on it (aqb calibrate --episodes)."""
    bugs = meta.get("bugs_present") or []
    fixes = [(b, plan.get(f"{b}-fixed", {}).get("commit")) for b in bugs]
    if not bugs or any(c is None for _, c in fixes):
        return None
    earliest = min(fixes, key=lambda bc: _commit_time(app, bc[1]))[0]
    return plan.get(f"{earliest}-buggy", {}).get("commit")


def gradle_version(wt: Path) -> tuple[int, int]:
    props = wt / "gradle" / "wrapper" / "gradle-wrapper.properties"
    m = re.search(r"gradle-(\d+)\.(\d+)", props.read_text()) if props.exists() else None
    return (int(m.group(1)), int(m.group(2))) if m else (8, 0)


def pick_jdk(gv: tuple[int, int]) -> Path:
    if gv < (7, 3):
        v = 11
    elif gv < (8, 5):
        v = 17
    else:
        v = 21
    return JDKS / f"jdk{v}"


def patch_tree(wt: Path) -> list[str]:
    """Keep the real package name on debug builds: drop applicationIdSuffix lines."""
    applied = []
    for f in list(wt.glob("*/build.gradle")) + list(wt.glob("*/build.gradle.kts")):
        txt = f.read_text()
        new = re.sub(r"^[ \t]*applicationIdSuffix\b(?!.*customSuffix).*\n", "", txt, flags=re.M)
        if new != txt:
            f.write_text(new)
            applied.append(f"strip applicationIdSuffix: {f.relative_to(wt)}")
    dj = wt / "gradle" / "gradle-daemon-jvm.properties"
    if dj.exists():
        # Gradle 9 daemon-toolchain pin (e.g. JetBrains JDK 21 via foojay); use the pinned JDK instead
        dj.unlink()
        applied.append("drop gradle/gradle-daemon-jvm.properties")
    gp = wt / "gradle.properties"
    if gp.exists():
        txt = gp.read_text()
        # some authors build on Termux and pin a phone-local aapt2; use the SDK's
        new = re.sub(r"^[ \t]*android\.aapt2FromMavenOverride=.*\n?", "", txt, flags=re.M)
        if new != txt:
            gp.write_text(new)
            applied.append("drop android.aapt2FromMavenOverride from gradle.properties")
    (wt / "local.properties").write_text(f"sdk.dir={SDK}\n")
    return applied


def find_apk(wt: Path, app: str) -> Path | None:
    base = wt / MODULE.get(app, "app") / "build" / "outputs" / "apk"
    apks = [p for p in base.rglob("*.apk") if "debug" in str(p).lower() and "androidTest" not in str(p)]
    if not apks:
        return None
    def rank(p: Path) -> tuple:
        n = p.name.lower()
        return (0 if "universal" in n else 1 if "x86_64" in n else 2 if not re.search(r"arm|x86", n) else 3,
                -p.stat().st_mtime)
    return sorted(apks, key=rank)[0]


def badging(apk: Path) -> dict:
    aapt = sorted(SDK.glob("build-tools/*/aapt2"))
    if not aapt:
        return {}
    out = subprocess.run([str(aapt[-1]), "dump", "badging", str(apk)], capture_output=True, text=True).stdout
    m = re.search(r"package: name='([^']+)' versionCode='([^']*)'", out)
    return {"package": m.group(1), "versionCode": m.group(2)} if m else {}


def _fix_bug_of(app: str) -> dict[str, str]:
    """fix commit -> bug id, from each bug's fixed build in the plan."""
    plan = json.loads(PLAN.read_text())["builds"]
    return {v["commit"]: k[: -len("-fixed")] for k, v in plan.items()
            if k.startswith(app + "-") and k.endswith("-fixed") and v.get("commit")}


def revert_fixes(job: "Job", wt: Path, log, rec: dict) -> bool:
    """Re-introduce bugs: undo each fix, newest commit first.

    Whole-commit revert first; on conflict, reverse-apply the bug's diff from
    private/diffs/ with a 3-way merge. Records the method per fix in rec."""
    git = ["git", "-c", "user.name=aqb", "-c", "user.email=aqb@localhost"]
    dates = {}
    for sha in job.reverts:
        out = subprocess.run(["git", "show", "-s", "--format=%ct", sha], cwd=wt, capture_output=True, text=True)
        dates[sha] = int(out.stdout.strip() or 0)
    order = sorted(job.reverts, key=lambda x: dates[x], reverse=True)
    bug_of = _fix_bug_of(job.app)
    rec["revert_methods"] = {}
    for sha in order:
        # one commit per revert, so an abort only drops the failed one
        if run(git + ["revert", "--no-edit", sha], wt, log) == 0:
            rec["revert_methods"][sha[:12]] = "git revert"
            continue
        run(git + ["revert", "--abort"], wt, log)
        diff = ROOT / "private" / "diffs" / f"{bug_of.get(sha, '?')}.diff"
        if diff.exists() and run(git + ["apply", "-R", "--3way", "--whitespace=nowarn", str(diff)], wt, log) == 0 \
                and run(git + ["commit", "-qam", f"aqb: reverse {diff.name}"], wt, log) == 0:
            rec["revert_methods"][sha[:12]] = f"apply -R {diff.name}"
            continue
        run(["git", "reset", "--hard", "-q", "HEAD"], wt, log)
        rec["error"] = f"revert conflict {sha[:12]} ({bug_of.get(sha, 'unknown bug')})"
        return False
    return True


def classify_failure(tail: str) -> str:
    """One-line reason for the manifest (most specific first)."""
    m = re.search(r"Could not find ([\w.\-]+:[\w.\-]+:[\w.\-]+)", tail)
    if m:
        return f"missing dependency {m.group(1).rstrip('.')} (gone from public repos)"
    if "Temporary failure in name resolution" in tail:
        return "network unavailable"
    if "cargo" in tail and "non-zero exit value" in tail:
        return "native Rust build (cargo) failed"
    if "Cannot find a Java installation" in tail:
        return "JDK toolchain not satisfied"
    if "OutOfMemoryError" in tail or "Killed" in tail:
        return "out of memory (capped scope)"
    m = re.search(r"\* What went wrong:\n(.{0,160})", tail)
    return "gradle failed: " + (m.group(1).strip() if m else "see log")


def run(cmd: list[str], cwd: Path, log, env=None, timeout=3600) -> int:
    log.write(f"\n$ {' '.join(cmd)}\n")
    log.flush()
    p = subprocess.run(cmd, cwd=cwd, stdout=log, stderr=subprocess.STDOUT, env=env, timeout=timeout)
    return p.returncode


MIN_FREE_GB = float(os.environ.get("AQB_MIN_FREE_GB", "4"))
# Hard ceiling: the kernel kills the build, not the desktop, if Gradle overshoots.
BUILD_MEM = os.environ.get("AQB_BUILD_MEM", "6G")
MEM_SCOPE = (["systemd-run", "--user", "--scope", "--quiet", "-p", f"MemoryMax={BUILD_MEM}", "-p", "MemorySwapMax=0"]
             if shutil.which("systemd-run") else [])


def wait_for_memory(log=print) -> None:
    from aqb.lock import mem_available_gb
    waited = False
    while mem_available_gb() < MIN_FREE_GB:
        if not waited:
            log(f"waiting: {mem_available_gb():.1f} GB free < {MIN_FREE_GB} GB")
            waited = True
        time.sleep(10)


def build_one(job: Job) -> dict:
    wait_for_memory()
    app = job.app
    repo = ROOT / "private" / "apps" / app / "src"
    wt = WORK / "wt" / f"{app}-{job.key}"
    logp = WORK / "logs" / "build" / f"{job.build_id}.log"
    logp.parent.mkdir(parents=True, exist_ok=True)
    rec = {"build_id": job.build_id, "app": app, "commit": job.commit, "reverts": job.reverts,
           "copies": job.extra_ids, "log": str(logp.relative_to(ROOT)), "ok": False}
    t0 = time.time()
    pkg_want = json.loads((DATASET / "apps" / app / "app.json").read_text())["package"]
    with logp.open("w") as log:
        try:
            if wt.exists():
                subprocess.run(["git", "worktree", "remove", "--force", str(wt)], cwd=repo, capture_output=True)
                shutil.rmtree(wt, ignore_errors=True)
            if run(["git", "worktree", "add", "--detach", "--force", str(wt), job.commit], repo, log):
                rec["error"] = "checkout failed"
                return rec
            if not revert_fixes(job, wt, log, rec):
                return rec
            rec["patches"] = patch_tree(wt)
            if app in VENDOR_APPS:
                subs = {k: v for k, v in json.loads((ROOT / "aqb" / "substitutions.json").read_text()).items()
                        if not k.startswith("_")}
                rec["patches"].append(f"vendor repo work/m2 + substitutions {sorted(subs.items())}")
            gv = gradle_version(wt)
            jdk = pick_jdk(gv)
            rec["gradle"] = f"{gv[0]}.{gv[1]}"
            rec["jdk"] = jdk.name
            env = dict(os.environ, JAVA_HOME=str(jdk), ANDROID_HOME=str(SDK), ANDROID_SDK_ROOT=str(SDK),
                       GRADLE_USER_HOME=str(WORK / "gradle-home"),
                       PATH=f"{jdk}/bin:{os.environ.get('PATH', '')}")
            installs = ",".join(str(JDKS / f"jdk{v}") for v in (11, 17, 21))
            (wt / "gradlew").chmod(0o755)
            ok_task = None
            tasks = list(TASKS[app])
            retried = False
            while tasks:
                task = tasks[0]
                code = run(MEM_SCOPE + ["./gradlew", task, "--no-daemon", "--console=plain", "-x", "lint",
                            f"-Porg.gradle.java.installations.paths={installs}",
                            "-Porg.gradle.java.installations.auto-download=false",
                            "--max-workers=2", "-Dorg.gradle.workers.max=2", "-Dorg.gradle.parallel=false",
                            "-Dorg.gradle.jvmargs=-Xmx2g -XX:MaxMetaspaceSize=768m",
                            "-Pkotlin.compiler.execution.strategy=in-process",
                            "-Dkotlin.compiler.execution.strategy=in-process"]
                           + EXTRA_ARGS.get(app, [])
                           + (["--init-script", str(ROOT / "aqb" / "vendor-init.gradle"), f"-Daqb.m2={VENDOR_M2}",
                               f"-Daqb.subs={ROOT / 'aqb' / 'substitutions.json'}"]
                              if app in VENDOR_APPS else []), wt, log, env=env)
                if code == 0:
                    ok_task = task
                    break
                tail = logp.read_text()[-6000:]
                if not retried and ("Temporary failure in name resolution" in tail or "Read timed out" in tail
                                    or "Connection reset" in tail):
                    retried = True  # transient network error: one retry, same task
                    log.write("\n# aqb: network error, retrying once in 30s\n")
                    time.sleep(30)
                    continue
                if "not found in project" in tail or "ambiguous" in tail:
                    tasks.pop(0)
                    continue
                break
            if not ok_task:
                rec["error"] = classify_failure(logp.read_text()[-20000:])
                return rec
            rec["task"] = ok_task
            apk = find_apk(wt, app)
            if apk is None:
                rec["error"] = "no apk produced"
                return rec
            b = badging(apk)
            rec.update(b)
            if b and b.get("package") != pkg_want:
                rec["error"] = f"package {b.get('package')} != {pkg_want}"
                return rec
            job.out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(apk, job.out)
            for extra in job.extra_ids:
                shutil.copy2(apk, job.out.parent / f"{extra}.apk")
            rec["sha256"] = sha256(job.out)
            rec["ok"] = True
            return rec
        except subprocess.TimeoutExpired:
            rec["error"] = "timeout"
            return rec
        finally:
            rec["seconds"] = round(time.time() - t0, 1)
            if rec.get("ok") or os.environ.get("AQB_KEEP_FAILED") != "1":
                subprocess.run(["git", "worktree", "remove", "--force", str(wt)], cwd=repo, capture_output=True)
                shutil.rmtree(wt, ignore_errors=True)


def record(rec: dict) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with MANIFEST.open("a") as f:
        f.write(json.dumps(rec) + "\n")
    if not rec["ok"]:
        return
    idxp = DATASET / "apps" / rec["app"] / "builds" / "index.json"
    idx = json.loads(idxp.read_text())
    for bid in [rec["build_id"]] + rec["copies"]:
        idx[bid]["sha256"] = rec["sha256"]
        idx[bid]["status"] = "built"
    idxp.write_text(json.dumps(idx, indent=2) + "\n")


def build(tier: str | None = "core", apps: set[str] | None = None, only: set[str] | None = None,
          jobs: int = 1, rebuild: bool = False, dry_run: bool = False) -> int:
    todo = load_jobs(tier, apps, only, rebuild)
    n_apks = sum(1 + len(j.extra_ids) for j in todo)
    print(f"{len(todo)} source trees -> {n_apks} APKs (tier={tier or 'all'})", flush=True)
    if dry_run:
        for j in todo:
            print(f"  {j.app:12} {j.build_id:26} {j.commit[:12]} reverts={len(j.reverts)} copies={j.extra_ids}")
        return 0
    # one Gradle build per app at a time (shared caches and worktree locks); apps in parallel
    by_app: dict[str, list[Job]] = {}
    for j in todo:
        by_app.setdefault(j.app, []).append(j)

    def run_app(js: list[Job]) -> list[dict]:
        out = []
        for j in js:
            r = build_one(j)
            record(r)
            print(f"{'OK  ' if r['ok'] else 'FAIL'} {r['build_id']:26} {r.get('seconds')}s {r.get('error', '')}", flush=True)
            out.append(r)
        return out

    fails = 0
    with ThreadPoolExecutor(max_workers=max(1, jobs)) as ex:
        futs = [ex.submit(run_app, js) for js in by_app.values()]
        for f in as_completed(futs):
            fails += sum(1 for r in f.result() if not r["ok"])
    print(f"done: {len(todo) - fails} ok, {fails} failed. Manifest: {MANIFEST.relative_to(ROOT)}")
    return 1 if fails else 0
