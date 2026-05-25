"""Playwright driver that turns an HTML document into a per-slide
JSON atom list, using the in-page extractor at ``extract.js``.

The HTML is expected to contain one or more ``<section class="slide">``
(or any element with class ``slide``) — one per slide. The browser
viewport is sized to the slide's CSS pixel dimensions so layout
matches the rendered design exactly; for multi-slide docs we use the
first slide's size as the viewport (the extractor reports each slide's
actual size in CSS pixels, which the mapper uses directly).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple


# Module-level so callers can mention the install command in errors.
_PLAYWRIGHT_INSTALL_HINT = (
    "Install with:\n"
    "  pip install playwright\n"
    "  python -m playwright install chromium"
)


class ExtractorError(Exception):
    """Raised when the Playwright pipeline can't complete. ``code``
    maps to a ToolResult error code."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def extract(html: str, *, base_url: str | None = None,
            timeout_seconds: int = 60) -> List[Dict[str, Any]]:
    """Render ``html`` in headless Chromium and return one dict per
    slide. Each dict has ``width`` / ``height`` (CSS pixels) and an
    ``atoms`` list (see ``extract.js`` for the schema).

    ``base_url`` lets relative URLs (images, web fonts) resolve when
    the HTML was loaded from disk; pass e.g.
    ``"file:///path/to/source/"`` (with trailing slash).
    """
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except ImportError:
        raise ExtractorError(
            "dependency_missing",
            "Playwright is not installed. " + _PLAYWRIGHT_INSTALL_HINT,
        )

    extract_js = (Path(__file__).parent / "extract.js").read_text(
        encoding="utf-8"
    )

    try:
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(headless=True)
            except Exception as e:
                # Most common reason: `playwright install chromium`
                # was never run on this machine.
                raise ExtractorError(
                    "dependency_missing",
                    "Could not launch headless Chromium: "
                    f"{e}\n{_PLAYWRIGHT_INSTALL_HINT}",
                )

            try:
                context = browser.new_context(
                    # Big viewport so wide slides aren't horizontally
                    # clipped before the extractor measures them. The
                    # extractor reads each slide's own rect anyway.
                    viewport={"width": 2400, "height": 1400},
                    device_scale_factor=1,
                )
                page = context.new_page()
                page.set_default_timeout(timeout_seconds * 1000)

                page.set_content(
                    html,
                    wait_until="networkidle",
                    timeout=timeout_seconds * 1000,
                )

                # Wait for web fonts so font metrics are stable.
                page.evaluate("document.fonts && document.fonts.ready")

                # Inject the extractor and call it.
                page.add_script_tag(content=extract_js)
                slides = page.evaluate("window.__extractDeck()")

                if not isinstance(slides, list) or not slides:
                    raise ExtractorError(
                        "invalid_input",
                        "No slides found — the HTML must contain at "
                        'least one element with class "slide".',
                    )

                # SVG screenshot pass: re-grab each SVG element by
                # index so the mapper can embed a PNG fallback while
                # waiting for the vector-EMF pipeline.
                _screenshot_svgs(page, slides)

                return slides
            finally:
                browser.close()
    except ExtractorError:
        raise
    except Exception as e:
        raise ExtractorError("render_failed", f"Browser extraction failed: {e}")


def _screenshot_svgs(page, slides: List[Dict[str, Any]]) -> None:
    """Walk every slide for ``type='svg'`` atoms and replace the raw
    SVG markup with a base64 PNG screenshot of that element. We index
    SVGs in document order so the slide/index match up with what was
    visible to the extractor.
    """
    import base64

    # Map all SVGs in the document so we can locate them by global
    # index. ``querySelectorAll('svg')`` returns them in document
    # order which is the same order our extractor visited them.
    svg_count = page.evaluate("document.querySelectorAll('svg').length")
    if svg_count == 0:
        return

    handles = page.query_selector_all("svg")
    global_idx = 0
    for slide in slides:
        for atom in slide["atoms"]:
            if atom.get("type") != "svg":
                continue
            if global_idx >= len(handles):
                break
            try:
                png = handles[global_idx].screenshot(omit_background=True)
                atom["png_b64"] = base64.b64encode(png).decode("ascii")
            except Exception:
                # Best-effort; mapper will skip the atom on failure.
                atom["png_b64"] = None
            atom.pop("markup", None)
            global_idx += 1


def resolve_html_input(html_or_path: str) -> Tuple[str, str | None]:
    """Mirror of ``pdf.create``'s convention: if ``html_or_path`` is a
    short single-line string ending in ``.html``/``.htm`` *and* the
    file exists, treat it as a path and return ``(contents, base_url)``.
    Otherwise return ``(html_or_path, None)``.
    """
    s = (html_or_path or "").strip()
    if (
        len(s) <= 1024
        and "\n" not in s
        and s.lower().endswith((".html", ".htm"))
    ):
        p = Path(s)
        if p.is_file():
            return (
                p.read_text(encoding="utf-8"),
                p.resolve().parent.as_uri() + "/",
            )
    return html_or_path, None
