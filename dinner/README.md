# Dinner Data

This folder stores trusted dinner data as one JSON file per dish.

Put dishes in `dishes/`.

Suggested rule:

The AI agent may plan meals and format messages, but ingredient facts should come from these JSON files.

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
