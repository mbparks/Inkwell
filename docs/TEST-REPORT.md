# INKWELL v1.0.0 — test report

**Recorded: 2026-09-22.**

**Browser engine:** Chromium 144.0.7559.96. **Result:** 66 UI/rendering/export checks and 11 offline-shell logic checks passed. No uncaught JavaScript errors were observed in the UI run.

## What was actually exercised

The application HTML and JavaScript were executed in Chromium. Tests drove mouse input, injected Chromium touch sequences, injected pen-pressure PointerEvents, used the real Canvas renderer and native image codecs, generated actual PNG/JPEG/WebP/BMP/SVG data, decoded raster files with Pillow, and rasterized generated SVG back in the browser to verify alpha and eraser ordering. Screenshots in this package are browser renders of the app, not concept art.

## Important limits of this run

The container browser blocks navigation through its managed configuration. The test therefore used `page.set_content` to render the local application, not a successful navigation to a public or localhost deployment. A memory-backed localStorage adapter allowed the real autosave serialization and restoration code to be checked across fresh documents. Download links were intercepted so their real generated Blob contents could be examined; operating-system file-save delivery was not exercised. The print test checked that an artwork image was prepared, not that a physical print or OS PDF dialog completed.

A separate test executed the actual service-worker source using in-memory Cache/Fetch adapters. It checked installation asset lists, namespace-safe cache cleanup, offline shell fallback, network refresh, and scope/method boundaries. It does not prove browser service-worker registration or durable offline caching.

The desktop and phone screenshots use the test storage adapter; a displayed Saved status demonstrates the application state after an adapter write, not a claim that native browser persistence was verified in this environment.

**Not verified:** physical iPhone/iPad Safari, physical Android Chrome, actual stylus hardware, hardware palm rejection, native IndexedDB/localStorage durability, native service-worker installation/update/offline reload, and native OS download/share/print dialogs.

## Reproduce

```sh
python -m pip install playwright pillow
python -m playwright install chromium
python tests/test_inkwell.py
node tests/test_service_worker.mjs
```

For the restricted-environment mode used for this report:

```sh
python tests/test_inkwell.py --sandbox --browser /usr/bin/chromium
```

## UI, rendering, and export checks

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

53. PASS — Two-finger navigation cancels the unfinished finger mark

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


## Offline-shell logic checks

1. PASS Install precaches all four deployed assets and requests activation

2. PASS Offline shell cache contains the expected four URLs

3. PASS Activation claims clients and removes the old same-scope cache

4. PASS Activation preserves caches belonging to another deployment

5. PASS Offline root navigation returns the cached app shell

6. PASS Uncached offline navigation falls back to index.html

7. PASS External requests are not intercepted

8. PASS POST requests are not intercepted or cached

9. PASS Requests outside the app folder are not intercepted

10. PASS Online navigation prefers the network response

11. PASS Updated navigation responses are retained for the next offline visit


## Real-device acceptance checklist

On the intended HTTPS deployment, verify the following before relying on browser storage or offline use for important work:


1. Draw with a physical mouse or finger; move to another area of the page and resume drawing. Check that scrolling does not interrupt ink.

2. Make two-finger pan/pinch gestures, and verify that they do not commit an accidental first-finger mark.

3. Wait for Saved, reload the page, and confirm that the project restores. Export and reopen a JSON backup as well.

4. Wait for Offline website cache ready, disable the network, reload, and draw/export again. Repeat after a deployed version update.

5. Save every supported image type. Open it in an independent viewer and check alpha, dimensions, crop, and erasing. On Safari, test the persistent save link and available share sheet.

6. Check pen pressure and pen-only mode on supported hardware. Do not interpret pen-only mode as guaranteed palm rejection.

7. Test Print / PDF, portrait and landscape orientation, and a low-memory device at larger export scales.

8. Confirm that a blocked storage permission or full quota leaves a visible Not saved warning while JSON export remains available.
