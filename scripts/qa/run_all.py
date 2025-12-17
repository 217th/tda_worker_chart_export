from __future__ import annotations

import argparse
import os
import sys
import unittest
from pathlib import Path


def _repo_root() -> Path:
    # scripts/qa/run_all.py -> scripts/qa -> scripts -> repo root
    return Path(__file__).resolve().parents[2]


def _iter_task_dirs(repo_root: Path) -> list[Path]:
    tasks_root = repo_root / "tests" / "tasks"
    if not tasks_root.exists():
        return []
    return sorted([p for p in tasks_root.iterdir() if p.is_dir() and p.name.startswith("T-")])


def _run_discover(start_dir: Path, *, pattern: str = "test_*.py") -> unittest.TestResult:
    # Important: task directories contain hyphens (e.g. T-002), which are not valid
    # Python package names. To keep discovery importable, we set top_level_dir to the
    # task directory itself so modules are imported as plain filenames.
    suite = unittest.defaultTestLoader.discover(
        start_dir=str(start_dir),
        pattern=pattern,
        top_level_dir=str(start_dir),
    )
    runner = unittest.TextTestRunner(verbosity=2)
    return runner.run(suite)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="qa-run-all")
    parser.add_argument(
        "--task",
        action="append",
        default=[],
        help="Run a single task directory (repeatable), e.g. --task T-002",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List discovered task test directories and exit",
    )
    args = parser.parse_args(argv)

    repo_root = _repo_root()
    os.chdir(repo_root)

    # Ensure repo-root imports work for tests that import runtime modules.
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    task_dirs = _iter_task_dirs(repo_root)
    if args.task:
        selected = []
        wanted = set(args.task)
        for d in task_dirs:
            if d.name in wanted:
                selected.append(d)
        task_dirs = selected

    if args.list:
        for d in task_dirs:
            print(d.as_posix())
        return 0

    if not task_dirs:
        print("No task test directories found under tests/tasks/T-*", file=sys.stderr)
        return 2

    any_failures = False
    for task_dir in task_dirs:
        print(f"\n=== {task_dir.name} ===", flush=True)
        result = _run_discover(task_dir)
        if not result.wasSuccessful():
            any_failures = True

    return 1 if any_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
