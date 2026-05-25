"""
`html` domain — read, render, convert, and **create** self-contained HTML
reports.

Why this domain exists
----------------------
Anthropic's engineering team (Thariq Shihipar et al., May 2026) made HTML
the default agent-output format for plans, reports, audits, and status
updates because it offers richer information density than Markdown,
survives past ~100 lines, and ships pre-rendered in any browser. This
domain exposes that capability as ordinary tool calls.

Conventions (same as the pdf / pptx domains)
--------------------------------------------
- Every tool returns a ``ToolResult`` envelope; no exceptions escape.
- Heavy deps (``pypdfium2`` for ``html.see``, ``soffice`` for both
  ``html.see`` and ``html.to_pdf``) are probed lazily inside the
  function that needs them.
- File operations never mutate the input file — transforms write to a
  fresh ``output`` path.
- ``html.see`` rasterises pages of the HTML (after a one-off PDF
  conversion) and returns at most 5 page images per call, mirroring the
  ``pdf.see`` / ``pptx.see`` contract.
- ``html.create`` always emits a **single-file, dependency-free** HTML
  document: inline ``<style>`` in ``<head>``, inline ``<script>``
  (if any), inline SVG charts, base64 images, system font stack, no
  network calls — the file must work offline forever.
"""

from __future__ import annotations

import base64
import io
import re
import shutil
import subprocess
import tempfile
from html.parser import HTMLParser
from pathlib import Path
from typing import List, Optional, Tuple

from runtime.tool_registry import ToolCtx, ToolError, ToolImage, ToolResult


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


_HTML_SUFFIXES = (".html", ".htm")


def _err(code: str, message: str, retriable: bool = False) -> ToolResult:
    return ToolResult(ok=False, error=ToolError(code=code, message=message, retriable=retriable))


def _require_input(path_str: str) -> Tuple[Optional[Path], Optional[ToolResult]]:
    p = Path(path_str)
    if not p.is_file():
        return None, _err("file_not_found", f"No file at {path_str!r}.")
    if p.suffix.lower() not in _HTML_SUFFIXES:
        return None, _err(
            "unsupported_format",
            f"{p.suffix!r} is not a .html / .htm file.",
        )
    return p, None


def _check_output(path_str: str, overwrite: bool, *, suffixes=_HTML_SUFFIXES) -> Tuple[Optional[Path], Optional[ToolResult]]:
    out = Path(path_str)
    if out.suffix.lower() not in suffixes:
        return None, _err(
            "invalid_input",
            f"`output` must end in one of {suffixes}.",
        )
    if out.exists() and not overwrite:
        return None, _err("output_exists", f"{path_str!r} exists; pass overwrite=true to replace.")
    return out, None


def _parse_pages(spec: Optional[str], total: int) -> Tuple[Optional[List[int]], Optional[ToolResult]]:
    """Parse a 1-based page spec like '1,3-5,8' into 0-based indices."""
    if spec is None:
        return list(range(total)), None
    out: List[int] = []
    for chunk in spec.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "-" in chunk:
            a, _, b = chunk.partition("-")
            try:
                start, end = int(a), int(b)
            except ValueError:
                return None, _err("invalid_input", f"Bad range {chunk!r} in pages spec.")
            if start < 1 or end < start or end > total:
                return None, _err("page_out_of_range", f"Range {chunk!r} is outside 1..{total}.")
            out.extend(range(start - 1, end))
        else:
            try:
                n = int(chunk)
            except ValueError:
                return None, _err("invalid_input", f"Bad page number {chunk!r}.")
            if n < 1 or n > total:
                return None, _err("page_out_of_range", f"Page {n} is outside 1..{total}.")
            out.append(n - 1)
    if not out:
        return None, _err("invalid_input", "pages spec is empty after parsing.")
    return out, None


# ---------------------------------------------------------------------------
# Lightweight HTML walker (stdlib only) for read / extract_text
# ---------------------------------------------------------------------------


_BLOCK_TAGS = {
    "p", "div", "section", "article", "header", "footer", "main", "aside",
    "li", "tr", "td", "th", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote",
    "pre", "br", "hr", "figure", "figcaption",
}
_SKIP_TAGS = {"script", "style", "noscript", "template"}


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: List[str] = []
        self._skip_depth = 0
        self.title: Optional[str] = None
        self._in_title = False
        # Counters
        self.counts: dict = {
            "headings": 0,
            "paragraphs": 0,
            "tables": 0,
            "images": 0,
            "links": 0,
            "scripts": 0,
            "styles": 0,
        }

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
            if tag == "script":
                self.counts["scripts"] += 1
            elif tag == "style":
                self.counts["styles"] += 1
            return
        if tag == "title":
            self._in_title = True
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self.counts["headings"] += 1
            self._chunks.append("\n")
        elif tag == "p":
            self.counts["paragraphs"] += 1
            self._chunks.append("\n")
        elif tag == "table":
            self.counts["tables"] += 1
        elif tag == "img":
            self.counts["images"] += 1
            alt = dict(attrs).get("alt")
            if alt:
                self._chunks.append(f"[image: {alt}]")
        elif tag == "a":
            self.counts["links"] += 1
        elif tag in _BLOCK_TAGS:
            self._chunks.append("\n")

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in _SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if tag == "title":
            self._in_title = False
        elif tag in _BLOCK_TAGS:
            self._chunks.append("\n")

    def handle_data(self, data):
        if self._skip_depth:
            return
        if self._in_title:
            self.title = (self.title or "") + data
            return
        self._chunks.append(data)

    def get_text(self) -> str:
        raw = "".join(self._chunks)
        # Collapse runs of whitespace within lines, but keep line breaks.
        lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in raw.splitlines()]
        # Collapse runs of blank lines.
        out: List[str] = []
        blank = False
        for ln in lines:
            if not ln:
                if not blank and out:
                    out.append("")
                blank = True
            else:
                out.append(ln)
                blank = False
        return "\n".join(out).strip()


def _read_html_file(path: Path) -> str:
    # Try utf-8 first, fall back to latin-1.
    raw = path.read_bytes()
    for enc in ("utf-8", "utf-16", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


# ---------------------------------------------------------------------------
# html.read — title + counts + size
# ---------------------------------------------------------------------------


def read(params, ctx: ToolCtx) -> ToolResult:
    src, err = _require_input(params.path)
    if err:
        return err
    try:
        text = _read_html_file(src)
    except Exception as e:
        return _err("unsupported_format", f"Failed to read HTML: {e}")

    parser = _TextExtractor()
    try:
        parser.feed(text)
    except Exception as e:
        return _err("parse_failed", f"HTML parse error: {e}")

    size = src.stat().st_size
    # Crude "external resource" check — useful because the
    # single-file rule is the central convention of html.create.
    external_refs = bool(
        re.search(r'<link[^>]+rel\s*=\s*["\']?stylesheet', text, re.I)
        or re.search(r'<script[^>]+src\s*=\s*["\']?https?:', text, re.I)
        or re.search(r'<img[^>]+src\s*=\s*["\']?https?:', text, re.I)
    )

    return ToolResult(ok=True, data={
        "path": str(src),
        "title": (parser.title or "").strip() or None,
        "size_bytes": size,
        "self_contained": not external_refs,
        "counts": parser.counts,
    })


# ---------------------------------------------------------------------------
# html.extract_text
# ---------------------------------------------------------------------------


def extract_text(params, ctx: ToolCtx) -> ToolResult:
    src, err = _require_input(params.path)
    if err:
        return err
    try:
        text = _read_html_file(src)
    except Exception as e:
        return _err("unsupported_format", f"Failed to read HTML: {e}")

    parser = _TextExtractor()
    try:
        parser.feed(text)
    except Exception as e:
        return _err("parse_failed", f"HTML parse error: {e}")

    out_text = parser.get_text()
    max_chars = max(0, int(params.max_chars or 0))
    truncated = False
    if max_chars and len(out_text) > max_chars:
        out_text = out_text[:max_chars]
        truncated = True

    return ToolResult(ok=True, data={
        "title": (parser.title or "").strip() or None,
        "text": out_text,
        "char_count": len(out_text),
        "truncated": truncated,
    })


# ---------------------------------------------------------------------------
# html.to_pdf — convert HTML → PDF via LibreOffice
# ---------------------------------------------------------------------------


def _run_soffice_convert(src: Path, fmt: str, out_dir: Path, timeout: int) -> Tuple[Optional[Path], Optional[ToolResult]]:
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        return None, _err(
            "dependency_missing",
            "LibreOffice (`soffice`) is required but was not found on PATH. "
            "Install with `brew install --cask libreoffice` (mac) or "
            "`apt-get install libreoffice` (debian).",
        )

    # macOS Homebrew installs a wrapper that points at LibreOffice.app;
    # if that bundle is missing or quarantined the wrapper dies with an
    # opaque exit 137. Detect before invoking.
    from tools.pdf.create import _check_libreoffice_app_bundle, _interpret_libreoffice_failure
    bundle_problem = _check_libreoffice_app_bundle(soffice)
    if bundle_problem:
        return None, _err("dependency_missing", bundle_problem)

    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        soffice, "--headless",
        "--convert-to", fmt,
        "--outdir", str(out_dir),
        str(src),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=max(5, int(timeout)))
    except subprocess.TimeoutExpired:
        return None, _err("timeout", f"LibreOffice did not finish within {timeout}s.", retriable=True)
    except Exception as e:
        return None, _err("convert_failed", f"Could not invoke LibreOffice: {e}")

    if proc.returncode != 0:
        stderr = proc.stderr.decode("utf-8", "replace").strip()
        stdout = proc.stdout.decode("utf-8", "replace").strip()
        combined = (stderr + "\n" + stdout).strip()
        hint = _interpret_libreoffice_failure(proc.returncode, combined)
        return None, _err(
            "convert_failed",
            f"LibreOffice exited {proc.returncode}. {hint}\n--- stderr ---\n{combined[:800] or '(empty)'}",
        )
    produced = out_dir / f"{src.stem}.{fmt}"
    if not produced.is_file():
        candidates = [c for c in out_dir.iterdir() if c.is_file()]
        if not candidates:
            return None, _err("convert_failed", "LibreOffice produced no output file.")
        produced = candidates[0]
    return produced, None


def to_pdf(params, ctx: ToolCtx) -> ToolResult:
    src, err = _require_input(params.path)
    if err:
        return err
    out = Path(params.output)
    if out.suffix.lower() != ".pdf":
        return _err("invalid_input", "`output` must end in .pdf.")
    if out.exists() and not params.overwrite:
        return _err("output_exists", f"{params.output!r} exists; pass overwrite=true to replace.")

    with tempfile.TemporaryDirectory() as tmpd:
        produced, perr = _run_soffice_convert(src, "pdf", Path(tmpd), params.timeout_seconds)
        if perr:
            return perr
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(produced, out)

    return ToolResult(ok=True, data={
        "output": str(out),
        "size_bytes": out.stat().st_size,
    })


# ---------------------------------------------------------------------------
# html.see — render pages as images (HTML → PDF → PNG, max 5 pages)
# ---------------------------------------------------------------------------


SEE_MAX_PAGES = 5


def see(params, ctx: ToolCtx) -> ToolResult:
    try:
        import pypdfium2 as pdfium  # type: ignore
    except ImportError:
        return _err("dependency_missing", "pypdfium2 is not installed.")

    src, err = _require_input(params.path)
    if err:
        return err

    with tempfile.TemporaryDirectory() as tmpd:
        pdf_path, cerr = _run_soffice_convert(src, "pdf", Path(tmpd), params.timeout_seconds)
        if cerr:
            return cerr

        try:
            pdf = pdfium.PdfDocument(str(pdf_path))
        except Exception as e:
            return _err("render_failed", f"Could not open intermediate PDF: {e}")

        try:
            total = len(pdf)
            spec = params.pages if params.pages is not None else "1"
            indices, perr = _parse_pages(spec, total)
            if perr:
                return perr
            if len(indices) > SEE_MAX_PAGES:
                return _err(
                    "too_many_pages",
                    f"see can render at most {SEE_MAX_PAGES} pages per call; requested {len(indices)}.",
                )

            images: List[ToolImage] = []
            page_meta: List[dict] = []
            for i in indices:
                try:
                    bitmap = pdf[i].render(scale=params.scale)
                    pil = bitmap.to_pil()
                    buf = io.BytesIO()
                    pil.save(buf, format="PNG")
                    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
                except Exception as e:
                    return _err("render_failed", f"Failed to render page {i + 1}: {e}")
                label = f"Page {i + 1} of {total} — {Path(src).name}"
                images.append(ToolImage(mime="image/png", b64=b64, label=label))
                page_meta.append({"page": i + 1, "bytes": len(b64)})
        finally:
            try:
                pdf.close()
            except Exception:
                pass

    return ToolResult(
        ok=True,
        data={
            "path": str(src),
            "page_count": total,
            "rendered": page_meta,
            "scale": params.scale,
        },
        images=images,
    )


# ---------------------------------------------------------------------------
# html.create — author a self-contained HTML report
# ---------------------------------------------------------------------------


def create(params, ctx: ToolCtx) -> ToolResult:
    out, oerr = _check_output(params.output, params.overwrite)
    if oerr:
        return oerr
    out.parent.mkdir(parents=True, exist_ok=True)

    if not isinstance(params.elements, list) or not params.elements:
        return _err("invalid_input", "`elements` must be a non-empty list.")

    from . import create as _engine

    try:
        data = _engine.build(params, out)
    except ValueError as e:
        return _err("create_failed", str(e))
    except Exception as e:
        return _err("create_failed", f"HTML build failed: {e}")
    return ToolResult(ok=True, data=data)
