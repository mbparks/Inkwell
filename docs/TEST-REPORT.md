# INKWELL v1.0.1 — verification report

Recorded: 2026-09-23. Chromium 144.0.7559.96.

**33/33 focused input tests, 66/66 existing UI/rendering/export tests, and 11/11 offline-cache logic checks passed.** No uncaught JavaScript errors occurred in the updated app's browser checks.

## Before and after

The focused input suite was executed against the unmodified v1.0.0 HTML and then against v1.0.1. It passed 11/33 cases on v1.0.0 and 33/33 on v1.0.1. Before/after machine-readable records are in `tests/input-baseline-v1.0.0.json` and `tests/input-results.json`.

The old release lost ink in controlled native Chromium cases involving released pointer capture, touch cancellation, and a second finger arriving after a written finger stroke. Those same sequences retain the ink in this release. This reproduces concrete failure paths, not the precise circumstances on the reporting user's physical device.

## Scope and limitations

The real application runs in a headless Chromium renderer via `page.set_content`: the managed container blocks URL navigation. Canvas drawing, image encoders, SVG paths and masks, and browser-rendered screenshots are real. Storage is a memory adapter. Download delivery is intercepted to inspect actual generated file blobs, and the print dialog is substituted. These tests do not prove durable IndexedDB/localStorage, deployment behavior, native service-worker registration, OS downloads, share sheets, or printing.

The input suite uses synthetic PointerEvents for exceptional event sequences plus five groups of browser-native mouse/touch checks. It includes 100 separate no-frame mouse strokes, 40 native mouse strokes, 25 native touch strokes, native mouse capture release, native touch cancellation, and a native second-finger transition. Browser-native touch here means Chromium event injection, not a physical touchscreen. Pen pressure is simulated, not measured on hardware.

The separate service-worker test uses in-memory Cache/Fetch adapters. It verifies installation asset lists, deletion of the previous v1.0.0 cache for the same directory only, offline fallbacks, network refresh, and scope/method boundaries. It does not establish actual offline installation or cache durability.

**Not tested:** physical iPhone/iPad or Android hardware, physical mice/styluses and hardware palm rejection, Safari, Firefox, native persistent storage, native service-worker updates/offline reload, and OS save/share/print dialogs.

## Reproduce

```sh
python -m pip install playwright pillow
python -m playwright install chromium
python tests/test_inkwell.py --sandbox --browser /path/to/chromium
python tests/test_input_regressions.py --browser /path/to/chromium
node tests/test_service_worker.mjs
```

For a normal environment that permits local HTTP navigation, omit `--sandbox` from the UI/export suite. The targeted input suite intentionally uses `set_content` and a memory storage adapter; its aim is input lifetime and rendering.

To compare an older HTML:

```sh
python tests/test_input_regressions.py --app /path/to/INKWELL-v1.0.0.html --browser /path/to/chromium --output /tmp/input-baseline.json
```

The previous release is expected to fail the newly added reliability checks. That command exits nonzero when a check fails.

## Focused input checks

1. PASS — A tap paints a visible dot without a move or animation frame
2. PASS — 100 rapid mouse strokes all commit independently before animation frames
3. PASS — Mouse cancellation retains captured ink without invented cancel coordinates
4. PASS — Touch cancellation retains captured ink
5. PASS — Pen cancellation retains captured ink
6. PASS — Lost capture with no buttons preserves ink once; later up cannot duplicate it
7. PASS — Lost capture while drawing continues through window move/up listeners
8. PASS — Failed pointer capture still receives movement and release outside the stage
9. PASS — A new down after a missed up saves the old stroke and starts a separate one
10. PASS — Mouse hover after a missed release ends ink without a long connecting line
11. PASS — Pen hover after a missed release does not draw phantom ink
12. PASS — A fresh primary touch recovers stale contacts instead of starting a false pinch
13. PASS — A second finger does not erase an already-written first-finger stroke
14. PASS — Immediate two-finger navigation discards only its provisional starting dot
15. PASS — Finishing a pinch allows the next one-finger stroke
16. PASS — Palm contacts during pen ink cannot put subsequent drawing into gesture lock
17. PASS — A coalesced-event API error falls back to the dispatched move
18. PASS — An unavailable coalesced-event API still draws
19. PASS — Empty coalesced samples fall back to the dispatched move
20. PASS — Coalesced movement samples preserve a curved path
21. PASS — Subpixel final movement is retained rather than dropping the endpoint
22. PASS — Blur preserves unfinished ink and clears input ownership
23. PASS — Pagehide preserves ink and permits a fresh primary touch
24. PASS — Escape still intentionally discards the unfinished stroke
25. PASS — Undo and redo retain their behavior for an interrupted stroke
26. PASS — Eraser interruption preserves the completed part of the erase
27. PASS — A stale hand-tool pan does not hijack a new pen stroke
28. PASS — An interrupted shape keeps its known geometry rather than disappearing
29. PASS — 40 native mouse strokes without dropped marks
30. PASS — 25 native touch strokes without dropped marks
31. PASS — Native mouse capture loss keeps one continuous stroke
32. PASS — Native touch cancellation retains the written stroke
33. PASS — Native second-finger contact does not erase existing finger ink

## Existing UI/rendering/export checks

1. PASS — Initial workspace is blank, not seeded with demo data
2. PASS — Visible version and integration API are present
3. PASS — Easy mode hides advanced shape tools
4. PASS — Mouse handwriting records a continuous vector stroke
5. PASS — Mouse handwriting paints visible canvas pixels
6. PASS — Live stroke preview is visible before pointer-up
7. PASS — Escape cancels the unfinished mark
8. PASS — Undo removes a committed stroke
9. PASS — Undo preserves the viewport for same-sized sheets
10. PASS — Redo restores a committed stroke
11. PASS — Successful autosave changes the state to saved
12. PASS — Autosave serialization restores in a fresh document (storage adapter)
13. PASS — Advanced mode reveals shape and text controls
14. PASS — Rectangle tool commits editable shape geometry
15. PASS — Typed annotation is placed through its form
16. PASS — SVG escapes text rather than executing markup
17. PASS — Paper guide setting updates the project
18. PASS — Dark theme does not alter artwork colors
19. PASS — High-contrast theme activates
20. PASS — Unsupported schema is rejected without changing the workspace
21. PASS — Import validation rejects bad.paper.width abuse
22. PASS — Import validation rejects bad.paper.color abuse
23. PASS — Import validation rejects bad.marks[0].points[0][0] abuse
24. PASS — Import validation rejects bad.marks[0].points[0][2] abuse
25. PASS — Import validation rejects bad.marks[0].type abuse
26. PASS — All malformed-import checks preserve the current drawing
27. PASS — Eraser removes earlier ink to true transparency
28. PASS — Ink drawn after erasing remains visible
29. PASS — PNG output is a genuine decodable PNG file at the selected size
30. PASS — PNG preserves later ink inside an erased region
31. PASS — PNG preserves transparent background and erasing
32. PASS — JPEG output is a genuine decodable JPEG file at the selected size
33. PASS — JPEG preserves later ink inside an erased region
34. PASS — JPEG flattens against the paper color, not black
35. PASS — WEBP output is a genuine decodable WEBP file at the selected size
36. PASS — WEBP preserves later ink inside an erased region
37. PASS — WEBP preserves transparent background and erasing
38. PASS — BMP output is a genuine decodable BMP file at the selected size
39. PASS — BMP preserves later ink inside an erased region
40. PASS — BMP flattens against the paper color, not black
41. PASS — SVG contains vector paths and eraser masks, not a embedded screenshot
42. PASS — Browser-rendered SVG reproduces erasure ordering and transparency
43. PASS — Crop-to-ink uses actual remaining alpha pixels, not the eraser bounding box
44. PASS — 2× export renders to exactly double the pixel dimensions
45. PASS — Print / PDF action prepares a decodable artwork image
46. PASS — Editable JSON download retains strokes, paper, and schema
47. PASS — Opening over an existing drawing requests replacement confirmation
48. PASS — JSON file input completes a validated project import
49. PASS — Malformed JSON reports an error without replacing the drawing
50. PASS — New phone workspace uses portrait paper
51. PASS — Phone viewport has no horizontal page overflow
52. PASS — Native touch event sequence draws a finger stroke
53. PASS — Immediate two-finger navigation cancels its provisional starting dot
54. PASS — Pinch gesture changes canvas zoom
55. PASS — Mobile settings open as a usable side panel
56. PASS — Pen-only mode turns finger input into navigation, not ink
57. PASS — Export dialog fits a phone viewport
58. PASS — Pen-pressure PointerEvents produce varying brush widths
59. PASS — Blocked storage never falsely reports a successful autosave
60. PASS — Clear ink requires confirmation
61. PASS — Clear ink removes all marks
62. PASS — Undo restores the drawing after Clear ink
63. PASS — Fresh Start resets the workspace and undo history
64. PASS — Fresh Start resets mode and theme preferences
65. PASS — Small 320-pixel phone layout avoids horizontal page overflow
66. PASS — No uncaught JavaScript errors across the tested workflows

## Offline-cache logic checks

1. PASS — Install precaches all four deployed assets and requests activation
2. PASS — Offline shell cache contains the expected four URLs
3. PASS — Activation claims clients and removes the old same-scope cache
4. PASS — Activation preserves caches belonging to another deployment
5. PASS — Offline root navigation returns the cached app shell
6. PASS — Uncached offline navigation falls back to index.html
7. PASS — External requests are not intercepted
8. PASS — POST requests are not intercepted or cached
9. PASS — Requests outside the app folder are not intercepted
10. PASS — Online navigation prefers the network response
11. PASS — Updated navigation responses are retained for the next offline visit

## Real-device acceptance

At the deployed site, confirm the version reads v1.0.1. Write many short letters and dots, lift and resume, move outside the paper and return, and repeat with a finger. Try a two-finger gesture both before writing and after drawing a line. Confirm that the completed part of the line stays and that the next stroke starts normally. Test a pen with incidental palm contact where available.

Save a JSON backup before testing reload/offline behavior. Confirm restoration, import/export, and all intended image formats on the actual devices and browsers. Do not clear site data as a version-update procedure. If a browser-cancelled contact was unwanted, Undo removes its preserved partial mark. The app cannot recover input that the browser or hardware never reports.
