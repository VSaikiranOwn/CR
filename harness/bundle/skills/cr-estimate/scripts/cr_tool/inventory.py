"""Discover and classify the CR input pack.

Copilot needs to know what it has been given before it can analyse anything.
This module walks an input folder, sorts the files into the four kinds of
evidence a CR estimate is built from, and (optionally) rasterises PDF pages so
Figma exports delivered as PDF can be read as images.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
TEXT_SUFFIXES = {".md", ".markdown", ".txt"}

KIND_FIGMA = "figma"
KIND_STORY = "user_story"
KIND_HLD = "hld"
KIND_LLD = "lld"
KIND_OTHER = "other"

STORY_HINTS = ("story", "stories", "jira", "acceptance", "ac", "us-", "backlog", "epic")
HLD_HINTS = ("hld", "high-level", "high_level", "highlevel", "architecture")
LLD_HINTS = ("lld", "low-level", "low_level", "lowlevel", "detailed-design")
FIGMA_HINTS = ("figma", "screen", "mockup", "wireframe", "design", "ui")


@dataclass
class InputFile:
    path: str
    kind: str
    size_bytes: int
    note: str = ""


def _hint_match(haystack: str, hints: tuple[str, ...]) -> bool:
    return any(hint in haystack for hint in hints)


def classify(path: Path, root: Path) -> str:
    """Decide what a file is from its suffix, name and containing folder."""
    suffix = path.suffix.lower()
    relative = path.relative_to(root).as_posix().lower()

    if suffix in IMAGE_SUFFIXES:
        return KIND_FIGMA

    if suffix in TEXT_SUFFIXES:
        if _hint_match(relative, LLD_HINTS):
            return KIND_LLD
        if _hint_match(relative, HLD_HINTS):
            return KIND_HLD
        if _hint_match(relative, STORY_HINTS):
            return KIND_STORY
        return KIND_OTHER

    if suffix == ".pdf":
        if _hint_match(relative, LLD_HINTS):
            return KIND_LLD
        if _hint_match(relative, HLD_HINTS):
            return KIND_HLD
        if _hint_match(relative, FIGMA_HINTS):
            return KIND_FIGMA
        return KIND_FIGMA  # PDFs in a CR pack are usually exported screens

    return KIND_OTHER


def split_pdf(path: Path, out_dir: Path, dpi: int = 144) -> list[Path]:
    """Render each PDF page to a PNG so image-only models can read it.

    Requires PyMuPDF. Returns the pages written, or raises with a clear message.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:  # pragma: no cover - depends on the host environment
        raise RuntimeError(
            "PDF splitting needs PyMuPDF. Install it with:  pip install pymupdf\n"
            "Or export the Figma frames as PNG/JPG instead."
        ) from None

    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    zoom = dpi / 72
    with fitz.open(path) as doc:
        for number, page in enumerate(doc, start=1):
            pixmap = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
            target = out_dir / f"{path.stem}-p{number:02d}.png"
            pixmap.save(target)
            written.append(target)
    return written


def scan(root: str | Path, *, split_pdfs: bool = False) -> dict:
    """Build the manifest Copilot reads before analysing the CR."""
    root = Path(root)
    if not root.is_dir():
        raise NotADirectoryError(f"Input folder not found: {root}")

    files: list[InputFile] = []
    generated: list[InputFile] = []

    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name.startswith("."):
            continue
        if "_rendered" in path.parts:
            continue
        kind = classify(path, root)
        entry = InputFile(
            path=path.relative_to(root).as_posix(),
            kind=kind,
            size_bytes=path.stat().st_size,
        )
        files.append(entry)

        if split_pdfs and path.suffix.lower() == ".pdf" and kind == KIND_FIGMA:
            pages = split_pdf(path, root / "_rendered")
            for page in pages:
                generated.append(InputFile(
                    path=page.relative_to(root).as_posix(),
                    kind=KIND_FIGMA,
                    size_bytes=page.stat().st_size,
                    note=f"rendered from {entry.path}",
                ))

    files.extend(generated)

    by_kind: dict[str, list[str]] = {}
    for entry in files:
        by_kind.setdefault(entry.kind, []).append(entry.path)

    manifest = {
        "root": str(root),
        "counts": {kind: len(paths) for kind, paths in sorted(by_kind.items())},
        "files": [asdict(entry) for entry in files],
        "gaps": _gaps(by_kind),
    }
    return manifest


def _gaps(by_kind: dict[str, list[str]]) -> list[str]:
    """What is missing from the pack, so the estimate can flag its own blind spots."""
    gaps = []
    if not by_kind.get(KIND_STORY):
        gaps.append("No user story / acceptance criteria file found -- "
                    "Business Requirement text will be thin.")
    if not by_kind.get(KIND_FIGMA):
        gaps.append("No Figma screens found -- UI complexity and the TSP "
                    "'Pages' / 'User Interaction' sizing will be guesswork.")
    if not by_kind.get(KIND_HLD):
        gaps.append("No HLD found -- service boundaries, integrations and the "
                    "TSP 'Interface' reusability will be guesswork.")
    if not by_kind.get(KIND_LLD):
        gaps.append("No LLD found -- endpoint-level detail in Technical "
                    "Component(s) will be less specific (this is often fine).")
    if by_kind.get(KIND_OTHER):
        gaps.append("Some files could not be classified; rename them to include "
                    "'story', 'hld', 'lld' or 'figma' to route them correctly.")
    return gaps


def render_text(manifest: dict) -> str:
    """A human- and Copilot-readable rendering of the manifest."""
    lines = [f"Input pack: {manifest['root']}", ""]
    if not manifest["files"]:
        lines.append("  (empty)")
    for kind, paths in sorted(_group(manifest).items()):
        lines.append(f"  {kind}  ({len(paths)})")
        for path in paths:
            lines.append(f"    - {path}")
    if manifest["gaps"]:
        lines.append("")
        lines.append("Gaps:")
        for gap in manifest["gaps"]:
            lines.append(f"  ! {gap}")
    return "\n".join(lines)


def _group(manifest: dict) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for entry in manifest["files"]:
        grouped.setdefault(entry["kind"], []).append(entry["path"])
    return grouped


def write_manifest(manifest: dict, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return path
