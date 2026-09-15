#!/usr/bin/env python3
"""Assemble the drop-in bundle for the DCP AI harness.

Produces `dist/harness/` laid out exactly as it must sit inside the harness
repo's `.github/`, so installing is a copy rather than a merge:

    dist/harness/
      skills/cr-estimate/{SKILL.md,scripts/,assets/,references/}
      validators/cr_complete.py

Run after changing anything under `src/`, then copy into the harness repo.

Usage:  python tools/build_harness_bundle.py [dist/harness]
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DEST = ROOT / "dist" / "harness"

ENTRY_POINT = '''#!/usr/bin/env python3
"""Entry point for the cr-estimate skill.

Bundled so the skill runs with no pip install:
    python3 .github/skills/cr-estimate/scripts/cr_estimate.py <workspace>
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cr_harness.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
'''


def copy_tree(source: Path, dest: Path) -> None:
    shutil.copytree(source, dest, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))


def build(dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)

    skill = dest / "skills" / "cr-estimate"
    scripts = skill / "scripts"
    scripts.mkdir(parents=True)

    # The two packages travel together: cr_tool renders the workbook, cr_harness
    # reads the batch artifacts. Vendored so the harness needs no pip install.
    copy_tree(ROOT / "src" / "cr_tool", scripts / "cr_tool")
    copy_tree(ROOT / "src" / "cr_harness", scripts / "cr_harness")

    entry = scripts / "cr_estimate.py"
    entry.write_text(ENTRY_POINT, encoding="utf-8")
    entry.chmod(0o755)

    # cr_tool locates its template three levels up from the package; inside the
    # bundle the template lives in the skill's assets/ folder instead.
    render = scripts / "cr_tool" / "render.py"
    render.write_text(
        render.read_text(encoding="utf-8").replace(
            'TEMPLATE_PATH = Path(__file__).resolve().parent.parent.parent / "templates" / K.TEMPLATE_NAME',
            'TEMPLATE_PATH = Path(__file__).resolve().parent.parent.parent / "assets" / K.TEMPLATE_NAME',
        ),
        encoding="utf-8",
    )

    assets = skill / "assets"
    assets.mkdir()
    shutil.copyfile(ROOT / "templates" / "cr_framework_template.xlsx",
                    assets / "cr_framework_template.xlsx")

    references = skill / "references"
    references.mkdir()
    shutil.copyfile(ROOT / "docs" / "estimation-rules.md",
                    references / "estimation-rules.md")

    shutil.copyfile(ROOT / "harness" / "skill" / "SKILL.md", skill / "SKILL.md")

    validators = dest / "validators"
    validators.mkdir(parents=True)
    shutil.copyfile(ROOT / "harness" / "validators" / "cr_complete.py",
                    validators / "cr_complete.py")

    files = sorted(p.relative_to(dest).as_posix() for p in dest.rglob("*") if p.is_file())
    print(f"Bundle written to {dest}  ({len(files)} files)")
    for path in files:
        print(f"  {path}")


if __name__ == "__main__":
    build(Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DEST)
