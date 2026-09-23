# Changelog

## 1.0.0 — 2026-09-22

First packaged release of INKWELL, a Green Shoe Garage Field Instrument.

### Drawing

- Unified mouse, touch, and pen input with pointer capture and live previews.
- Pen, variable-width brush, translucent highlighter, and true-alpha eraser.
- Color palette, custom hex colors, stroke widths, smoothing, opacity, and pressure/speed dynamics.
- Two-finger pan/pinch, Move tool, space-drag, wheel zoom, and Fit.
- Lines, arrows, boxes, ovals, filled shapes, and typed annotations in Advanced mode.
- Keyboard shortcuts, undo/redo, cancel-stroke behavior, and viewport-preserving undo.

### Paper and export

- Landscape, portrait, square, signature-strip, A4-ratio, and custom paper sizes.
- Plain, ruled, grid, and dot paper; custom color and transparent paper.
- PNG, JPEG, capability-detected WebP, vector SVG, and 24-bit BMP.
- Transparent output, visible-ink crop, padding, 1×–4× export, codec/size checks, and export preview.
- Browser Print / PDF preparation and feature-detected file sharing.

### Local-first workflow

- Inline single-file application with optional scoped service-worker shell.
- Autosave indicator, local storage fallback, blocked-storage warnings, and multi-tab warning.
- Validated editable JSON import/export and drag-and-drop JSON opening.
- Clear ink, undoable workspace replacements, and confirmed Fresh Start.
- Editable sample; no initial seed artwork.
- Responsive portrait phone layout, collapsible settings, and light/dark/high-contrast themes.
- README, JSON documentation, examples, browser screenshots, and reproducible regression tests.

### Release verification

- 66 UI, rendering, interaction, and file-content checks passed in Chromium using sandbox storage/download adapters.
- 11 scoped offline-cache logic checks passed using in-memory adapters.
- Native persistence, native offline installation, physical devices, and OS dialogs remain outside this test run. See `docs/TEST-REPORT.md`.
