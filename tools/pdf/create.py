"""
PDF authoring engine for ``pdf.create``.

``pdf.create`` has exactly one job: take a complete HTML document and
render it to PDF. The agent owns the layout — page size, margins,
fonts, palette, running headers, page counters, columns, full-bleed,
bleed marks, whatever it wants. We don't inject any CSS, we don't
override the @page rule, we don't force a print colour scheme. The
agent writes the page, we put it on paper (virtually).

Rendering
---------
- Primary engine: **WeasyPrint**. Full CSS Paged Media support
  (``@page`` size and margins, named pages, ``@top-*``/``@bottom-*``
  margin boxes, ``counter(page)`` / ``counter(pages)``, repeated table
  headers, ``page-break-*`` / ``break-*``, vector text, subset fonts,
  ``@font-face`` with web URLs, hyperlinks, internal anchors).
- Fallback engine: **LibreOffice headless**. Used automatically when
  WeasyPrint's native libs (Pango/Cairo) are missing. LibreOffice has
  much weaker CSS Paged Media support — it ignores ``@page`` margin
  boxes silently — so a document that relies on running headers or
  page counters will render without them on this path. A warning is
  attached to the result.

The agent picks the engine via ``engine`` (``auto`` / ``weasyprint`` /
``libreoffice``). PDF metadata (``title`` / ``author`` / ``subject``)
is set on the document object itself, not injected into the HTML.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

# ---------------------------------------------------------------------------
# Public entry point — called from tools/pdf/impl.py:create
# ---------------------------------------------------------------------------


def build(spec, out_path: Path) -> dict:
    """Render ``spec`` to ``out_path`` (a .pdf path).

    ``spec`` is the validated ``CreateParams`` from
    ``tools/pdf/registry.py``. Returns the result-data dict that
    ``pdf.create`` exposes.
    """
    html_text, base_url = _load_html(spec)

    with tempfile.TemporaryDirectory() as tmpd:
        tmp_html = Path(tmpd) / "source.html"
        tmp_html.write_text(html_text, encoding="utf-8")

        engine_used, warnings = _render_to_pdf(
            tmp_html, out_path, spec, base_url=base_url
        )

    return {
        "output": str(out_path),
        "size_bytes": out_path.stat().st_size,
        "page_count": _count_pages(out_path),
        "engine": engine_used,
        "warnings": warnings,
    }


def render_html_to_pdf(
    html: str,
    out_path: Path,
    *,
    engine: str = "auto",
    timeout_seconds: int = 120,
    title: Optional[str] = None,
    author: Optional[str] = None,
    subject: Optional[str] = None,
) -> Tuple[str, List[str]]:
    """Render a complete HTML document (string or .html file path) to PDF.

    This is the shared engine entry point — ``pdf.create`` calls it via
    ``build()``, and ``pptx.from_html`` calls it directly so the two
    tools agree on how HTML becomes paginated visual output.

    Returns ``(engine_used, warnings)``. Raises ``ValueError`` for bad
    inputs and ``_DependencyMissing`` when no renderer is usable.
    """

    # Reuse the same input-loading and rendering helpers that ``build``
    # uses, by faking the minimal attribute surface of a ``CreateParams``.
    class _Spec:
        pass

    spec = _Spec()
    spec.html = html
    spec.engine = engine
    spec.timeout_seconds = timeout_seconds
    spec.title = title
    spec.author = author
    spec.subject = subject

    html_text, base_url = _load_html(spec)
    with tempfile.TemporaryDirectory() as tmpd:
        tmp_html = Path(tmpd) / "source.html"
        tmp_html.write_text(html_text, encoding="utf-8")
        return _render_to_pdf(tmp_html, out_path, spec, base_url=base_url)


# ---------------------------------------------------------------------------
# HTML resolution — string or file path, no injection
# ---------------------------------------------------------------------------


_HTML_DOC_RE = re.compile(r"<!doctype\s+html|<html[\s>]", re.IGNORECASE)


def _load_html(spec) -> Tuple[str, Optional[str]]:
    """Return ``(html_text, base_url)``.

    ``base_url`` is set when the source came from a file, so WeasyPrint
    can resolve relative URLs (images, stylesheets, fonts) against the
    file's directory. For raw-string input there is no base URL.
    """
    src = (spec.html or "").strip()
    if not src:
        raise ValueError("`html` is required and must not be empty.")

    # Path-shaped strings get treated as files when they exist on disk
    # with an .html / .htm extension. We don't try to be clever about
    # detecting fragments — if it parses as a path and the file is
    # there, we read it; otherwise it's treated as raw HTML.
    looks_like_path = (
        len(src) < 1024
        and "\n" not in src
        and src.lower().endswith((".html", ".htm"))
    )
    if looks_like_path:
        p = Path(src)
        if not p.is_file():
            raise ValueError(f"HTML file not found: {src!r}")
        text = p.read_text(encoding="utf-8")
        if not _HTML_DOC_RE.search(text):
            raise ValueError(
                f"{src!r} does not look like a full HTML document "
                "(no <!doctype html> or <html> tag found)."
            )
        return text, p.resolve().parent.as_uri() + "/"

    # Raw HTML string. Must be a complete document — we are not in the
    # business of wrapping fragments because the agent then can't
    # declare an @page rule, set fonts, etc.
    if not _HTML_DOC_RE.search(src):
        raise ValueError(
            "`html` must be a complete HTML document (start with "
            "`<!doctype html>` and include an `<html>` element). "
            "Add a `<head>` with your `<style>@page { … }</style>` "
            "and any `<link>` / `<meta>` you need — pdf.create does "
            "not wrap fragments."
        )
    return src, None


# ---------------------------------------------------------------------------
# Render: WeasyPrint primary, LibreOffice fallback
# ---------------------------------------------------------------------------


def _render_to_pdf(
    html_path: Path,
    out_path: Path,
    spec,
    base_url: Optional[str],
) -> Tuple[str, List[str]]:
    """Render `html_path` → `out_path`. Returns (engine_used, warnings)."""
    engine = (spec.engine or "auto").lower()
    if engine not in {"auto", "weasyprint", "libreoffice"}:
        raise ValueError(
            f"unknown engine {spec.engine!r}; choose auto/weasyprint/libreoffice"
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    warnings: List[str] = []

    if engine in {"auto", "weasyprint"}:
        try:
            _render_weasyprint(html_path, out_path, spec, base_url)
            return "weasyprint", warnings
        except _DependencyMissing as e:
            if engine == "weasyprint":
                raise
            warnings.append(f"weasyprint unavailable: {e}; falling back to libreoffice")
        except Exception as e:
            if engine == "weasyprint":
                raise
            warnings.append(f"weasyprint failed: {e}; falling back to libreoffice")

    # LibreOffice path
    _render_libreoffice(html_path, out_path, spec.timeout_seconds)
    warnings.append(
        "rendered with libreoffice; CSS @page margin boxes (running headers, "
        "page counters) are ignored on this path."
    )
    return "libreoffice", warnings


class _DependencyMissing(RuntimeError):
    pass


def _render_weasyprint(
    html_path: Path,
    out_path: Path,
    spec,
    base_url: Optional[str],
) -> None:
    _ensure_native_lib_path()
    try:
        from weasyprint import HTML  # type: ignore
    except ImportError as e:
        raise _DependencyMissing(f"weasyprint not installed: {e}") from e
    except OSError as e:
        # Native lib (pango/cairo/gobject) missing — common on
        # bare macOS / minimal Linux images. Tell the caller exactly
        # what to install.
        raise _DependencyMissing(
            f"weasyprint native libs not loadable: {e}. "
            "Install Pango + Cairo (mac: `brew install pango`; "
            "debian: `apt-get install libpango-1.0-0 libpangoft2-1.0-0`)."
        ) from e

    # WeasyPrint resolves relative URLs against `base_url`. For string
    # input we fall back to the temp file's directory, which has no
    # useful neighbours — agents should use absolute URLs in that case.
    effective_base = base_url or html_path.parent.as_uri() + "/"
    html_doc = HTML(filename=str(html_path), base_url=effective_base)

    # Metadata lives on the rendered Document — mutate it before
    # writing. This is the only API that survives across WeasyPrint
    # 60.x → 66.x (write_pdf metadata kwargs were removed in 66).
    document = html_doc.render()
    _apply_pdf_metadata(document, spec)
    document.write_pdf(str(out_path))


def _apply_pdf_metadata(document, spec) -> None:
    """Override the document's ``<head>``-derived metadata with the
    tool-level kwargs, when they're set. Leaves WeasyPrint's defaults
    in place otherwise (which pick up `<title>`, `<meta name=author>`,
    etc. from the HTML).
    """
    meta = getattr(document, "metadata", None)
    if meta is None:
        return
    if spec.title:
        meta.title = str(spec.title)
    if spec.author:
        # WeasyPrint stores authors as a list of strings.
        meta.authors = [str(spec.author)]
    if spec.subject:
        meta.description = str(spec.subject)




# ---------------------------------------------------------------------------
# Native-library discovery
# ---------------------------------------------------------------------------


_NATIVE_LIB_PATHS_PRIMED = False


def _ensure_native_lib_path() -> None:
    """Make sure WeasyPrint can find Pango / Cairo / GObject.

    The problem
    -----------
    WeasyPrint uses ``cffi.dlopen`` which falls through to
    ``ctypes.util.find_library``. On macOS that only searches a few
    system directories, none of which include Homebrew's prefix
    (``/opt/homebrew/lib`` on Apple Silicon, ``/usr/local/lib`` on
    Intel). Setting ``DYLD_FALLBACK_LIBRARY_PATH`` from inside Python
    is too late — dyld read it at process start.

    The fix
    -------
    Locate each required library by absolute path, then monkey-patch
    ``ctypes.util.find_library`` to return that path when WeasyPrint
    asks for the corresponding short name. We also pre-load each lib
    with ``ctypes.CDLL`` (``RTLD_GLOBAL``) so direct ``dlopen`` calls
    inside cffi hit a cached handle.

    The same trick works on Linux distributions that put libs in
    non-standard directories (``/usr/lib/x86_64-linux-gnu`` etc.).
    """
    global _NATIVE_LIB_PATHS_PRIMED
    if _NATIVE_LIB_PATHS_PRIMED:
        return
    _NATIVE_LIB_PATHS_PRIMED = True

    import ctypes
    import ctypes.util
    import sys
    from pathlib import Path as _Path

    if sys.platform == "darwin":
        search_dirs = ["/opt/homebrew/lib", "/usr/local/lib"]
        ext = "dylib"
    elif sys.platform.startswith("linux"):
        search_dirs = [
            "/usr/lib/x86_64-linux-gnu",
            "/usr/lib/aarch64-linux-gnu",
            "/usr/local/lib",
            "/usr/lib",
        ]
        ext = "so"
    else:
        return

    # Mapping from the short names WeasyPrint passes to find_library →
    # the basename glob we should match on disk. Order within each list
    # matters: we keep the first match.
    wanted = {
        "libgobject-2.0-0": ["libgobject-2.0", "gobject-2.0"],
        "gobject-2.0-0":    ["libgobject-2.0", "gobject-2.0"],
        "gobject-2.0":      ["libgobject-2.0", "gobject-2.0"],
        "libpango-1.0-0":   ["libpango-1.0", "pango-1.0"],
        "pango-1.0-0":      ["libpango-1.0", "pango-1.0"],
        "pango-1.0":        ["libpango-1.0", "pango-1.0"],
        "libpangoft2-1.0-0": ["libpangoft2-1.0", "pangoft2-1.0"],
        "pangoft2-1.0-0":    ["libpangoft2-1.0", "pangoft2-1.0"],
        "pangoft2-1.0":      ["libpangoft2-1.0", "pangoft2-1.0"],
        "libharfbuzz-0":    ["libharfbuzz"],
        "harfbuzz":         ["libharfbuzz"],
        "libharfbuzz-subset-0": ["libharfbuzz-subset"],
        "harfbuzz-subset":  ["libharfbuzz-subset"],
        "libfontconfig-1":  ["libfontconfig"],
        "fontconfig-1":     ["libfontconfig"],
        "fontconfig":       ["libfontconfig"],
    }

    def _find_lib_file(basenames):
        for d in search_dirs:
            dpath = _Path(d)
            if not dpath.is_dir():
                continue
            for base in basenames:
                cands = sorted(dpath.glob(f"{base}.{ext}*")) + sorted(
                    dpath.glob(f"{base}-*.{ext}*")
                )
                for c in cands:
                    if c.is_file() or c.is_symlink():
                        return str(c)
        return None

    # Build the alias table and pre-load each lib.
    aliases: dict = {}
    for name, basenames in wanted.items():
        path = _find_lib_file(basenames)
        if path:
            aliases[name] = path

    if not aliases:
        return

    # Pre-load with RTLD_GLOBAL so transitive deps resolve.
    seen_paths = set()
    for p in aliases.values():
        if p in seen_paths:
            continue
        seen_paths.add(p)
        try:
            ctypes.CDLL(p, mode=ctypes.RTLD_GLOBAL)
        except OSError:
            pass

    # Monkey-patch find_library so cffi's later lookups succeed.
    _orig_find = ctypes.util.find_library

    def _patched(name: str):
        if name in aliases:
            return aliases[name]
        return _orig_find(name)

    ctypes.util.find_library = _patched  # type: ignore[assignment]


def _render_libreoffice(html_path: Path, out_path: Path, timeout: int) -> None:
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        raise _DependencyMissing(
            "`soffice` (LibreOffice) not found on PATH. "
            "Install with: `brew install --cask libreoffice` (mac) or "
            "`apt-get install libreoffice` (debian)."
        )

    # macOS Homebrew installs a wrapper that points at the LibreOffice
    # .app bundle. If the user moved / deleted the bundle (or Gatekeeper
    # quarantined it), the wrapper dies with an opaque exit 137. Detect
    # this *before* invoking so we can give an actionable message.
    app_problem = _check_libreoffice_app_bundle(soffice)
    if app_problem:
        raise _DependencyMissing(app_problem)

    with tempfile.TemporaryDirectory() as tmpd:
        out_dir = Path(tmpd)
        cmd = [
            soffice, "--headless",
            "--convert-to", "pdf",
            "--outdir", str(out_dir),
            str(html_path),
        ]
        try:
            proc = subprocess.run(
                cmd, capture_output=True, timeout=max(5, int(timeout))
            )
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(
                f"LibreOffice did not finish within {timeout}s."
            ) from e
        if proc.returncode != 0:
            stderr = proc.stderr.decode("utf-8", "replace").strip()
            stdout = proc.stdout.decode("utf-8", "replace").strip()
            combined = (stderr + "\n" + stdout).strip()
            hint = _interpret_libreoffice_failure(proc.returncode, combined)
            raise RuntimeError(
                f"LibreOffice exited {proc.returncode}. "
                f"{hint}\n--- stderr ---\n{combined[:800] or '(empty)'}"
            )
        produced = out_dir / f"{html_path.stem}.pdf"
        if not produced.is_file():
            cands = [p for p in out_dir.iterdir() if p.suffix.lower() == ".pdf"]
            if not cands:
                raise RuntimeError("LibreOffice produced no PDF.")
            produced = cands[0]
        shutil.copyfile(produced, out_path)


def _check_libreoffice_app_bundle(soffice_path: str) -> Optional[str]:
    """On macOS, the ``soffice`` on PATH is typically either a Homebrew
    shell wrapper that ``exec``s the binary inside LibreOffice.app, or
    a symlink that points directly into the .app bundle. If the .app
    bundle has been moved to the Trash or quarantined by Gatekeeper,
    the launch fails with an opaque exit (127 or 137). Detect both
    states here and return a remediation message; return ``None`` when
    everything looks fine.
    """
    import sys
    if sys.platform != "darwin":
        return None

    app: Optional[Path] = None

    # 1. If `soffice` is a shell wrapper, parse out the absolute .app
    #    path it execs. Works for both Homebrew (`#!/bin/sh; 'X.app/.../soffice' "$@"`)
    #    and the cask Caskroom variant (`*.wrapper.sh`).
    try:
        with open(soffice_path, "rb") as f:
            head = f.read(2)
        if head == b"#!":
            text = Path(soffice_path).read_text(errors="replace")
            m = re.search(r"(/[^\s'\"]+\.app)(?:/Contents/MacOS/\S+)?", text)
            if m:
                app = Path(m.group(1))
    except OSError:
        pass

    # 2. Otherwise resolve the symlink and walk up to find the .app.
    if app is None:
        try:
            target = Path(soffice_path).resolve(strict=False)
            for ancestor in [target, *target.parents]:
                if ancestor.name.endswith(".app"):
                    app = ancestor
                    break
        except OSError:
            return None

    if app is None:
        return None

    if not app.exists():
        return (
            f"LibreOffice wrapper at {soffice_path} points at "
            f"{app}, but that bundle does not exist (was it moved to the "
            "Trash, or never finished installing?). Reinstall with "
            "`brew reinstall --cask libreoffice` and open it once from "
            "/Applications so Gatekeeper records the approval, then retry."
        )

    # Check for Gatekeeper quarantine bit on the .app.
    try:
        proc = subprocess.run(
            ["xattr", "-p", "com.apple.quarantine", str(app)],
            capture_output=True, timeout=5,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return (
                f"LibreOffice at {app} is quarantined by Gatekeeper "
                "(this triggers the 'damaged and should be moved to the "
                "Trash' dialog and an immediate exit 137). Clear it with: "
                f"`xattr -dr com.apple.quarantine {app}`, then retry."
            )
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def _interpret_libreoffice_failure(rc: int, output: str) -> str:
    """Translate a raw soffice failure into a one-line hint."""
    low = output.lower()
    if "damaged" in low or "quarantine" in low:
        return (
            "Gatekeeper rejected the LibreOffice app. Run "
            "`xattr -dr com.apple.quarantine /Applications/LibreOffice.app`."
        )
    if rc == 137 or "killed" in low:
        return (
            "LibreOffice was killed by the OS (Gatekeeper or OOM). "
            "On macOS try opening /Applications/LibreOffice.app once "
            "manually to clear the quarantine bit."
        )
    if "user profile" in low or "lock" in low:
        return "Another LibreOffice instance is holding the user profile; close it and retry."
    return "See stderr below for the underlying cause."


def _count_pages(pdf_path: Path) -> int:
    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError:
        return 0
    try:
        return len(PdfReader(str(pdf_path)).pages)
    except Exception:
        return 0
