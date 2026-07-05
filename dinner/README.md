# Dinner Data

This folder stores trusted dinner data as one JSON file per dish.

Put dishes in `dishes/`.
Keep the currently agreed weekly plan in `meal-plan.md`.
Keep the simple dinner log in `history.md`.

Suggested rule:

The AI agent may plan meals and format messages, but ingredient facts should come from these JSON files, the agreed weekly sequence should come from `meal-plan.md`, and retrospective questions should use `history.md`.

## Planning Files

- `meal-plan.md`: current agreed plan with concrete calendar dates
- `history.md`: simple append-only dinner log for looking back at what was cooked and when
- `sync_history.py`: append missing planned dinners from `meal-plan.md` into `history.md`

## Sync Rule

After changing `meal-plan.md`, run:

```bash
python3 dinner/sync_history.py
```

This keeps `history.md` in sync without making the log schema complicated.

## Dish File Shape

Use `_template.json` as the starting point for new dishes.

`time_rating` is a 1-5 estimate of time and active dinner effort:

- `1`: very fast
- `2`: normal easy weekday meal
- `3`: more chopping, pan work, or oven time
- `4`: longer cooking or more cleanup
- `5`: project meal

Keep ingredient `id` values stable and boring, for example:

- `spaghetti`
- `ground_beef`
- `canned_tomatoes`
- `yellow_onion`

Avoid vague ingredients like `tomatoes` unless that is really what you mean.

## Optional Knuspr Metadata

Dish files may add an optional `knuspr` object per ingredient to store shopping hints.

Supported patterns:

- `preferred_query`: the preferred Knuspr search phrase for a concrete product choice
- `ask_user`: set to `true` when the ingredient is intentionally ambiguous and the agent must ask before adding anything
- `options`: explicit user-facing alternatives for ambiguous ingredients

Example:

```json
{
  "id": "maultaschen",
  "name": "maultaschen",
  "amount": 12,
  "unit": "piece",
  "knuspr": {
    "preferred_query": "Bürger Gemüsemaultaschen"
  }
}
```
