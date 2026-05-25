/*
 * In-browser extractor injected into the page by Playwright.
 *
 * The page contains one or more <section class="slide"> elements.
 * Each becomes a slide. For each slide we walk every descendant
 * element (and text nodes), pull computed style + bounding box, and
 * emit a flat list of "atoms" that the Python mapper turns into
 * native PPTX shapes.
 *
 * Coordinate system: each atom's x/y/w/h are in CSS pixels relative
 * to the slide's top-left corner. The Python side converts to EMU
 * using the @page size (also reported per slide).
 *
 * Atom types
 * ----------
 *   { type: 'box', x, y, w, h, fill?, gradient?, border?, radius,
 *     shadow?, opacity, rotation, z }
 *   { type: 'text', x, y, w, h, lines: [{x,y,w,h,text,
 *       font, size, weight, italic, color, align, decoration}],
 *     z }
 *   { type: 'image', x, y, w, h, src, opacity, z }
 *   { type: 'table', x, y, w, h, rows: [[{text, font, size, weight,
 *       color, fill, align}, ...]], z }
 *
 * The mapper paints atoms in array order, so we sort by z-index
 * before returning.
 */

(function () {
  const px = (v) => parseFloat(v) || 0;

  // -------------------------------------------------------------------
  // Colour + gradient parsing (just enough to be useful; Python does
  // the rest)
  // -------------------------------------------------------------------

  // "rgb(15, 23, 42)" or "rgba(15, 23, 42, 0.5)" → {r,g,b,a}
  function parseColor(str) {
    if (!str) return null;
    const m = str.match(
      /rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)(?:\s*,\s*([\d.]+))?\s*\)/i
    );
    if (!m) return null;
    return {
      r: +m[1],
      g: +m[2],
      b: +m[3],
      a: m[4] === undefined ? 1 : +m[4],
    };
  }

  function isTransparent(c) {
    return !c || c.a === 0;
  }

  // "linear-gradient(135deg, rgb(...) 0%, rgb(...) 100%)"
  // We only support linear-gradient with explicit rgb stops for now;
  // anything else returns null and the Python side falls back to
  // solid fill (or skips the fill entirely).
  function parseLinearGradient(bgImage) {
    if (!bgImage || !bgImage.startsWith("linear-gradient")) return null;
    // Strip "linear-gradient(" and trailing ")"
    const inner = bgImage.slice("linear-gradient(".length, -1);
    // Split top-level by commas, respecting nested parens (rgb(..)).
    const parts = [];
    let depth = 0;
    let cur = "";
    for (const ch of inner) {
      if (ch === "(") depth++;
      else if (ch === ")") depth--;
      if (ch === "," && depth === 0) {
        parts.push(cur.trim());
        cur = "";
      } else {
        cur += ch;
      }
    }
    if (cur.trim()) parts.push(cur.trim());

    let angle = 180; // CSS default for linear-gradient is "to bottom"
    let stopParts = parts;
    if (parts[0].endsWith("deg")) {
      angle = parseFloat(parts[0]);
      stopParts = parts.slice(1);
    } else if (parts[0].startsWith("to ")) {
      // Convert "to top" etc. to degrees (rough).
      const dir = parts[0].slice(3).trim();
      const map = {
        top: 0,
        right: 90,
        bottom: 180,
        left: 270,
        "top right": 45,
        "bottom right": 135,
        "bottom left": 225,
        "top left": 315,
      };
      angle = map[dir] !== undefined ? map[dir] : 180;
      stopParts = parts.slice(1);
    }

    const stops = [];
    for (const sp of stopParts) {
      const m = sp.match(/(rgba?\([^)]+\))(?:\s+([\d.]+)%)?/i);
      if (!m) continue;
      const c = parseColor(m[1]);
      if (!c) continue;
      stops.push({
        color: c,
        offset: m[2] !== undefined ? +m[2] / 100 : null,
      });
    }
    if (stops.length < 2) return null;

    // Fill in missing offsets evenly between fixed ones.
    if (stops[0].offset === null) stops[0].offset = 0;
    if (stops[stops.length - 1].offset === null)
      stops[stops.length - 1].offset = 1;
    for (let i = 1; i < stops.length - 1; i++) {
      if (stops[i].offset === null) {
        stops[i].offset = i / (stops.length - 1);
      }
    }
    return { angle, stops };
  }

  // -------------------------------------------------------------------
  // Helpers
  // -------------------------------------------------------------------

  function isVisible(el, cs) {
    if (cs.display === "none" || cs.visibility === "hidden") return false;
    if (px(cs.opacity) === 0) return false;
    return true;
  }

  function rectInside(rect, slideRect) {
    // Skip elements completely outside the slide (covers `overflow:
    // hidden` content too — we still emit them so the slide stays
    // faithful, but trim to the slide bounds).
    return {
      x: rect.left - slideRect.left,
      y: rect.top - slideRect.top,
      w: rect.width,
      h: rect.height,
    };
  }

  function zOf(cs) {
    const z = parseInt(cs.zIndex, 10);
    return isNaN(z) ? 0 : z;
  }

  function getRotation(transform) {
    if (!transform || transform === "none") return 0;
    const m = transform.match(/matrix\(([^)]+)\)/);
    if (!m) return 0;
    const v = m[1].split(",").map(parseFloat);
    return Math.round(Math.atan2(v[1], v[0]) * (180 / Math.PI));
  }

  // First non-transparent ancestor background colour. Used so text
  // boxes can pick a sensible fallback if the user opens the PPTX in
  // dark mode etc.
  function ancestorBg(el) {
    let cur = el.parentElement;
    while (cur) {
      const cs = getComputedStyle(cur);
      const c = parseColor(cs.backgroundColor);
      if (c && c.a > 0) return c;
      cur = cur.parentElement;
    }
    return { r: 255, g: 255, b: 255, a: 1 };
  }

  // Inline / formatting tags whose text is already captured by the
  // surrounding block's ``inlineRuns`` walk. We must NEVER emit a
  // separate text atom for these — doing so duplicates every styled
  // span on top of its containing paragraph.
  const INLINE_TAGS = new Set([
    "A", "ABBR", "B", "BDI", "BDO", "BR", "CITE", "CODE", "DATA",
    "DFN", "EM", "I", "KBD", "MARK", "Q", "RUBY", "S", "SAMP",
    "SMALL", "SPAN", "STRONG", "SUB", "SUP", "TIME", "U", "VAR",
    "WBR", "FONT",
  ]);

  // Tags that own a dedicated atom type (table / image / svg) and
  // must not be considered text leaves.
  const NON_TEXT_TAGS = new Set([
    "TABLE", "THEAD", "TBODY", "TFOOT", "TR", "TD", "TH",
    "COLGROUP", "COL", "CAPTION",
    "IMG", "SVG", "PICTURE", "SOURCE", "VIDEO", "AUDIO", "CANVAS",
  ]);

  // Decide whether an element is a "leaf text container": a block-
  // level element whose only meaningful content is text + inline
  // formatting AND no descendant will be its own text leaf. We emit
  // one PPTX text box per such element. The deepest block wins so
  // bigger ancestors never re-paint the same text on top of a child.
  function isTextLeaf(el) {
    if (NON_TEXT_TAGS.has(el.tagName)) return false;
    // Inline tags are captured by their parent block's run walk.
    if (INLINE_TAGS.has(el.tagName)) return false;
    // Must have visible text of its own.
    if ((el.textContent || "").trim().length === 0) return false;

    // If any descendant is itself a candidate block-with-text, let
    // that descendant be the leaf — not us. Otherwise the ancestor
    // and the descendant would both paint the same text.
    for (const desc of el.querySelectorAll("*")) {
      if (INLINE_TAGS.has(desc.tagName)) continue;
      if (NON_TEXT_TAGS.has(desc.tagName)) continue;
      if ((desc.textContent || "").trim().length === 0) continue;
      return false;
    }
    return true;
  }

  // Walk inline runs inside a text-leaf element and return an array
  // of styled runs in document order. Each run inherits its parent
  // element's computed style (which is where colour/weight/italic
  // overrides live).
  function inlineRuns(el) {
    const runs = [];
    function walk(node, styleSrc) {
      if (node.nodeType === Node.TEXT_NODE) {
        const text = node.textContent;
        if (!text) return;
        const cs = getComputedStyle(styleSrc);
        runs.push({
          text: text,
          font: cs.fontFamily.split(",")[0].replace(/['"]/g, "").trim(),
          size: px(cs.fontSize) * 0.75, // px → pt
          weight: parseInt(cs.fontWeight, 10) || 400,
          italic: cs.fontStyle === "italic",
          color: parseColor(cs.color) || { r: 0, g: 0, b: 0, a: 1 },
          decoration: cs.textDecorationLine || "none",
        });
      } else if (node.nodeType === Node.ELEMENT_NODE) {
        if (node.tagName === "BR") {
          runs.push({ text: "\n", brk: true });
          return;
        }
        for (const child of node.childNodes) walk(child, node);
      }
    }
    walk(el, el);
    return runs;
  }

  // -------------------------------------------------------------------
  // Main per-slide extractor
  // -------------------------------------------------------------------

  function extractSlide(slideEl) {
    const slideRect = slideEl.getBoundingClientRect();
    const slideCs = getComputedStyle(slideEl);
    const atoms = [];

    // Emit the slide background first (always at z=-1 so anything
    // else paints on top).
    const slideBg = parseColor(slideCs.backgroundColor);
    const slideGrad = parseLinearGradient(slideCs.backgroundImage);
    if (slideGrad || (slideBg && !isTransparent(slideBg))) {
      atoms.push({
        type: "box",
        x: 0,
        y: 0,
        w: slideRect.width,
        h: slideRect.height,
        fill: slideBg && !isTransparent(slideBg) ? slideBg : null,
        gradient: slideGrad,
        radius: 0,
        opacity: 1,
        rotation: 0,
        z: -1,
      });
    }

    // Then walk every descendant.
    const all = slideEl.querySelectorAll("*");
    for (const el of all) {
      const cs = getComputedStyle(el);
      if (!isVisible(el, cs)) continue;
      const rect = el.getBoundingClientRect();
      if (rect.width === 0 || rect.height === 0) continue;
      const r = rectInside(rect, slideRect);
      const z = zOf(cs);

      // Skip the slide root itself (already emitted as background).
      if (el === slideEl) continue;

      const tag = el.tagName;

      // ---- Images ----
      if (tag === "IMG") {
        atoms.push({
          type: "image",
          x: r.x,
          y: r.y,
          w: r.w,
          h: r.h,
          src: el.src,
          opacity: px(cs.opacity),
          z,
        });
        continue;
      }

      // ---- Tables ----
      if (tag === "TABLE") {
        const rows = [];
        for (const tr of el.rows) {
          const row = [];
          for (const cell of tr.cells) {
            const ccs = getComputedStyle(cell);
            const fill = parseColor(ccs.backgroundColor);
            row.push({
              text: (cell.textContent || "").trim(),
              font: ccs.fontFamily.split(",")[0].replace(/['"]/g, "").trim(),
              size: px(ccs.fontSize) * 0.75,
              weight: parseInt(ccs.fontWeight, 10) || 400,
              italic: ccs.fontStyle === "italic",
              color: parseColor(ccs.color) || { r: 0, g: 0, b: 0, a: 1 },
              fill: fill && !isTransparent(fill) ? fill : null,
              align: ccs.textAlign,
              header: cell.tagName === "TH",
            });
          }
          rows.push(row);
        }
        atoms.push({
          type: "table",
          x: r.x,
          y: r.y,
          w: r.w,
          h: r.h,
          rows,
          z,
        });
        // Skip descendants — table cells are already serialised.
        continue;
      }

      // ---- SVG ----
      if (tag === "SVG" || tag === "svg") {
        // For MVP, snapshot the SVG outerHTML; mapper will rasterise
        // via Playwright element.screenshot() in a follow-up pass.
        atoms.push({
          type: "svg",
          x: r.x,
          y: r.y,
          w: r.w,
          h: r.h,
          markup: el.outerHTML,
          opacity: px(cs.opacity),
          z,
        });
        continue;
      }

      // ---- Background / border box ----
      const bg = parseColor(cs.backgroundColor);
      const grad = parseLinearGradient(cs.backgroundImage);
      const borderColor = parseColor(cs.borderTopColor);
      const borderW = px(cs.borderTopWidth);
      const radius = px(cs.borderTopLeftRadius);
      const hasFill = grad || (bg && !isTransparent(bg));
      const hasBorder =
        borderW > 0 && borderColor && !isTransparent(borderColor);
      if (hasFill || hasBorder) {
        atoms.push({
          type: "box",
          x: r.x,
          y: r.y,
          w: r.w,
          h: r.h,
          fill: bg && !isTransparent(bg) ? bg : null,
          gradient: grad,
          border: hasBorder ? { color: borderColor, width: borderW } : null,
          radius,
          opacity: px(cs.opacity),
          rotation: getRotation(cs.transform),
          z,
        });
      }

      // ---- Text leaf ----
      if (isTextLeaf(el)) {
        const runs = inlineRuns(el);
        if (runs.length === 0) continue;
        const padTop = px(cs.paddingTop);
        const padLeft = px(cs.paddingLeft);
        const padRight = px(cs.paddingRight);
        const padBottom = px(cs.paddingBottom);
        atoms.push({
          type: "text",
          x: r.x + padLeft,
          y: r.y + padTop,
          w: r.w - padLeft - padRight,
          h: r.h - padTop - padBottom,
          align: cs.textAlign,
          lineHeight: px(cs.lineHeight),
          runs,
          z,
        });
      }
    }

    // Stable sort by z, then by document order (already preserved by
    // the array). Lower z paints first.
    atoms.sort((a, b) => (a.z || 0) - (b.z || 0));

    return {
      width: slideRect.width,
      height: slideRect.height,
      atoms,
    };
  }

  // -------------------------------------------------------------------
  // Entry point exposed to Playwright
  // -------------------------------------------------------------------

  window.__extractDeck = function () {
    const slides = document.querySelectorAll("section.slide, .slide");
    const out = [];
    for (const s of slides) out.push(extractSlide(s));
    return out;
  };
})();
