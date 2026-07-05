# Dinner History

This file is the append-only log for what the family actually planned or ate.

Use it to answer questions like:

- What have we not had in a while?
- When did we last eat X?
- Which dishes repeat too often?

Rules:

- Append new rows instead of rewriting old ones.
- Prefer real dates in `YYYY-MM-DD`.
- `source` should point to the dish JSON when possible.
- `status` can be `planned`, `cooked`, `skipped`, or `changed`.

| Date | Day | Dish | Status | Source | Notes |
| --- | --- | --- | --- | --- | --- |
| 2026-07-06 | Monday | Halloumi Wraps | planned | `halloumi-wraps.json` | Imported from current meal plan |
| 2026-07-07 | Tuesday | Maultaschen | planned | `maultaschen-pan-with-egg.json` | Imported from current meal plan |
| 2026-07-08 | Wednesday | Pasta with Tomato Sauce | planned | `pasta-with-tomato-sauce.json` | Imported from current meal plan |
