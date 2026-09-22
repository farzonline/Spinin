# SPDX-License-Identifier: GPL-3.0-or-later
# check_portable.py
# Guards the macOS port from a Windows machine.
#
# The Mac build cannot be run here, so the thing most likely to break it silently is an
# innocent-looking `import win32gui` added at the top of a shared module: everything still
# works on Windows, and macOS fails at startup with an ImportError nobody sees until someone
# runs it. This walks the source and fails if any shared module reaches for a Windows-only
# package outside a platform branch.
#
# Run it directly, or let CI do it:  python check_portable.py

import ast
import pathlib
import sys

# Packages that exist only on Windows. Importing one at module scope in a shared module
# breaks macOS at startup.
WINDOWS_ONLY = {"win32gui", "win32process", "win32api", "win32con", "winreg",
                "pycaw", "comtypes", "AppOpener"}

# Likewise for macOS, so the Windows build cannot be broken from the other direction.
MAC_ONLY = {"Quartz", "AppKit", "Foundation", "objc", "CoreFoundation"}

# The per-platform backends are allowed to import their own platform's packages freely:
# nothing loads them unless that platform is the one running.
WINDOWS_BACKENDS = {"_input_win.py", "_audio_win.py"}
MAC_BACKENDS = {"_input_mac.py", "macos_system.py"}


def top_level_imports(tree):
    """Every module imported at column 0 — that is, not inside a function or an if."""
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield node.lineno, alias.name
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            yield node.lineno, node.module or ""


def check(root="."):
    problems = []
    for path in sorted(pathlib.Path(root).glob("*.py")):
        if path.name == "check_portable.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for lineno, module in top_level_imports(tree):
            package = module.split(".")[0]
            if package in WINDOWS_ONLY and path.name not in WINDOWS_BACKENDS:
                problems.append(f"{path.name}:{lineno} imports {module} at module scope — "
                                "macOS cannot load this. Put it behind a platform branch, "
                                "or move it into _input_win.py / _audio_win.py.")
            if package in MAC_ONLY and path.name not in MAC_BACKENDS:
                problems.append(f"{path.name}:{lineno} imports {module} at module scope — "
                                "Windows cannot load this. Put it behind a platform branch.")
    return problems


if __name__ == "__main__":
    # The check must catch what it is for, or it is worth nothing.
    sample = ast.parse("import os\nimport win32gui\n\ndef f():\n    import win32api\n")
    found = [m for _, m in top_level_imports(sample)]
    assert found == ["os", "win32gui"], found
    assert "win32api" not in found, "an import inside a function is fine and must not trip"
    guarded = ast.parse("import sys\nif sys.platform == 'win32':\n    import pycaw\n")
    assert [m for _, m in top_level_imports(guarded)] == ["sys"], "a guarded import is fine"

    issues = check()
    for issue in issues:
        print(f"  {issue}")
    if issues:
        print(f"\n{len(issues)} portability problem(s).")
        sys.exit(1)
    print(f"check_portable OK — no unguarded platform imports in "
          f"{len(list(pathlib.Path('.').glob('*.py')))} modules")
