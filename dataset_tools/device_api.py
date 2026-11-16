"""Device API shared by the dataset bot (scripts, checks) and the harness (implementation).

The dataset bot writes seed.py, repro.py and checks.py against `Device`.
Your sandbox provides a concrete subclass (e.g. AdbDevice) that talks to the emulator.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

Selector = dict  # {"id": ...} | {"text": ...} | {"desc": ...}


@dataclass
class CheckResult:
    passed: bool                      # True = behaves as intended (bug absent)
    observed: dict = field(default_factory=dict)
    tier: str = "A"                   # "A" stored data, "B" structural UI, "C" pixel-based


class Device:
    """Interface only. Implement every method in your sandbox."""

    # harness-only
    def install(self, build_id: str) -> None: raise NotImplementedError

    # app lifecycle
    def launch(self, package: str) -> None: raise NotImplementedError
    def force_stop(self, package: str) -> None: raise NotImplementedError
    def rotate(self, landscape: bool) -> None: raise NotImplementedError

    # input
    def tap(self, selector: Selector) -> None: raise NotImplementedError
    def input_text(self, selector: Selector, text: str) -> None: raise NotImplementedError
    def back(self) -> None: raise NotImplementedError
    def home(self) -> None: raise NotImplementedError
    def scroll_to(self, selector: Selector) -> bool: raise NotImplementedError
    def wait_idle(self, timeout_s: float = 5) -> None: raise NotImplementedError

    # observation
    def ui(self) -> list[dict]: raise NotImplementedError
    def screenshot(self) -> bytes: raise NotImplementedError

    # app data (debug builds)
    def sql(self, db_name: str, query: str, params: tuple = ()) -> list[dict[str, Any]]: raise NotImplementedError
    def read_file(self, app_relative_path: str) -> bytes: raise NotImplementedError
    def write_seed_sql(self, db_name: str, statements: list[str]) -> None: raise NotImplementedError
    def settings(self, namespace: str, key: str) -> str: raise NotImplementedError
