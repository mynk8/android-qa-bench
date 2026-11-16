"""Scripted path that reveals amaze-0016 on a buggy build: the target check's trigger."""
from __future__ import annotations
import importlib.util
from pathlib import Path


def run(dev) -> None:
    spec = importlib.util.spec_from_file_location("c", Path(__file__).with_name("checks.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.target(dev, {})
