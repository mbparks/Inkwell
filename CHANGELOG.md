# Changelog

## 1.0.1 — 2026-09-23

Input-reliability patch following reports of occasional missed ink strokes.

- Preserve captured ink on browser pointer cancellation instead of deleting the unfinished mark. Interrupted erasing and shapes also retain their completed portion.
- Use one capture-phase window route for movement and release, so capture failures and leaving the drawing area do not silently lose the event stream.
- Continue through an unexpected capture loss while the contact is down; finish at the last known point when it is no longer down. Normal release cannot duplicate a mark.
- Recover a stale pointer on a fresh down and a stale primary touch on a new primary contact. A missed release cannot silently block or merge the next stroke.
- Treat mouse/pen hover after a missed release as an end, not an ink point. Clear pointer and gesture ownership on blur, page hide, tool changes, dialogs, and explicit cancellation.
- Keep an already-written finger stroke when a second finger begins navigation. Only an immediate stationary first contact is discarded as the provisional navigation dot.
- Ignore new touch contacts during an active pen stroke; fall back safely when coalesced-event access is absent, empty, or throws.
- Preserve small final movements and flush the last known raw point before committing so smoothing does not cut off the end of the stroke.
- Update application and offline-cache versions. Keep schema 1, storage keys, image formats, and the existing layout.
- Include GNU GPL v3 licensing and reproducible before/after input tests.

Verification: 33 focused input cases passed, including native Chromium mouse capture loss, native touch cancellation, repeated mouse/touch strokes, and a second-finger transition. The same input suite passes 11/33 cases against v1.0.0. All 66 existing UI/rendering/export checks and 11 service-worker logic checks also passed. Storage/file delivery use adapters; physical hardware and Safari were not tested. See `docs/TEST-REPORT.md`.

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
