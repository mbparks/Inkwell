# INKWELL project format — schema 1

An editable project is a JSON object with `app: "INKWELL"` and `schema: 1`.

```json
{
  "app": "INKWELL",
  "schema": 1,
  "version": "1.0.0",
  "id": "application-generated-identifier",
  "title": "My sketch",
  "created": "2026-09-22T00:00:00.000Z",
  "paper": {
    "width": 1600,
    "height": 1000,
    "color": "#fffdf7",
    "pattern": "blank",
    "spacing": 40,
    "transparent": false
  },
  "marks": [
    {
      "id": "application-generated-mark-identifier",
      "type": "stroke",
      "tool": "pen",
      "color": "#243d36",
      "width": 4,
      "opacity": 1,
      "points": [[100, 200, 0.8], [150, 220, 0.75]]
    }
  ]
}
```

## Coordinates and ordering

All coordinates are in logical paper pixels, with `(0, 0)` at the top-left. Each point is `[x, y, pressureFactor]`; pressure factors range from 0 to 1. Brush width is `width × (0.25 + 0.75 × pressureFactor)`. Constant-width pens and highlighters retain point pressure values but do not use them to set width.

Marks are rendered in array order. An `eraser` stroke removes ink from earlier marks. It does not erase the paper or guides and does not erase marks appearing later in the array. SVG exports reproduce this ordering with luminance masks.

Freehand coordinates and pressure are normalized to two decimal places on import. Stroke identifiers are regenerated on import; they are not stable external object identifiers. New project instances receive new identifiers on import as well. Geometry and other supported editable content are retained. Additional unknown properties are discarded, not executed.

## Mark types

`stroke` requires `tool` (`pen`, `brush`, `highlighter`, or `eraser`), `width`, `color`, `opacity`, and `points`.

`line`, `arrow`, `rect`, and `ellipse` require `x1`, `y1`, `x2`, `y2`, `width`, `color`, `opacity`, and a boolean `fill`. Fill affects rectangles and ellipses; lines and arrows remain lines.

`text` requires `x`, `y`, `text`, `fontSize`, `fontFamily` (`sans`, `serif`, or `mono`), `color`, and `opacity`. Text uses a top-aligned origin, with multiline spacing of 1.25 times the font size. Text is escaped for SVG output.

## Validation

Accepted paper patterns are `blank`, `lined`, `grid`, and `dots`. Colors must be six-digit hexadecimal colors. All numeric coordinates must be finite and inside the validation envelope. Paper, mark, point, text, opacity, width, and file-size limits are enforced before state replacement. Unknown schemas are rejected rather than guessed or silently downgraded.

Exports contain the current application version and an additional `exported` timestamp. JSON is compact by default. Undo history, zoom/pan, and workspace theme are not part of an editable project.

## Integration surface

The page exposes a small `window.Inkwell` object:

```js
await Inkwell.ready;
const original = Inkwell.getProject(); // independent JSON-compatible copy
const validated = Inkwell.validateProject(original); // throws on invalid data
Inkwell.loadProject(validated); // undoable replacement; programmatic, no dialog
const status = Inkwell.getStatus();
const example = Inkwell.getSample();
const svg = Inkwell.toSVG(); // current export-panel settings
```

The UI file importer supplies confirmation before replacing non-empty work. The programmatic `loadProject` method intentionally omits that UI confirmation; callers must obtain any required user consent. The API does not upload or fetch project content.
