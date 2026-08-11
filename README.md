# Tandoor Recipes for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

A [HACS](https://hacs.xyz/) custom integration that connects Home Assistant to a
[Tandoor Recipes](https://tandoor.dev/) instance (self-hosted or the hosted/cloud
version), so your meal plan and shopping list live inside Home Assistant too.

## What it does

- **Sensors**
  - `sensor.today_s_meals` — how many meals are planned today, with the recipe
    names/meal types as attributes.
  - `sensor.shopping_list_items` — count of open shopping list items.
- **Todo list**
  - A Home Assistant `todo` entity mirroring your Tandoor shopping list — check
    items off, add new ones, or delete them, from HA (Lovelace todo card, voice
    assistants, automations, etc). Changes sync back to Tandoor.
- **Services**
  - `tandoor.search_recipes` — search recipes by name, returns id/name/image/servings.
  - `tandoor.add_meal_plan` — add a recipe (or a freeform note) to the meal plan.
  - `tandoor.add_shopping_list_item` — add an item to the shopping list.

## Requirements

- A Tandoor instance (self-hosted, or the hosted/cloud version) you can reach
  from Home Assistant.
- An API token: in Tandoor, go to **Settings → API** and create an access
  token (Bearer-style token, not the older login-session token).

## Installation

### Via HACS (once added as a custom repository)

1. HACS → Integrations → ⋮ → Custom repositories → add this repo URL,
   category **Integration**.
2. Install "Tandoor Recipes", restart Home Assistant.
3. Settings → Devices & Services → Add Integration → search "Tandoor Recipes".
4. Enter your Tandoor host URL (including the `/space/...` path if your
   instance uses one) and the API token.

### Manual

Copy `custom_components/tandoor` into your Home Assistant `config/custom_components/`
directory, restart HA, then add the integration as above.

## Notes

- Polling interval is 5 minutes (meal plan + shopping list). This isn't
  configurable yet.
- Multiple Tandoor instances can be added as separate config entries; the
  `add_meal_plan` / `add_shopping_list_item` / `search_recipes` services take
  an optional `config_entry_id` to target a specific one (required if more
  than one instance is configured).

## License

MIT
