"""HTML → editable PPTX engine.

Pipeline
--------
1. ``extractor`` opens the HTML in a headless Chromium (Playwright),
   injects ``extract.js`` into the page, and returns one JSON blob per
   ``<section class="slide">`` describing every visible atom (text run,
   box, image, table cell) with absolute coordinates and computed
   styles.
2. ``mapper`` turns those JSON atoms into native ``python-pptx`` shapes
   (text boxes, rounded rectangles, pictures, tables), preserving
   editability.
3. ``build`` orchestrates the two and writes the .pptx.

This is the *editable* counterpart to ``pptx.from_html``, which renders
each slide to a single full-bleed picture. Use that one when you want
pixel-perfect fidelity; use this one when the user will edit the deck.
"""
