"""The Tandoor Recipes integration."""
from __future__ import annotations

import logging
from datetime import date

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import TandoorApiError, TandoorAuthError, TandoorClient
from .const import (
    ATTR_AMOUNT,
    ATTR_DATE,
    ATTR_LIMIT,
    ATTR_MEAL_TYPE_ID,
    ATTR_NAME,
    ATTR_NOTE,
    ATTR_QUERY,
    ATTR_RECIPE_ID,
    ATTR_SERVINGS,
    ATTR_UNIT,
    CONF_API_TOKEN,
    CONF_VERIFY_SSL,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
    SERVICE_ADD_MEAL_PLAN,
    SERVICE_ADD_SHOPPING_LIST_ITEM,
    SERVICE_SEARCH_RECIPES,
)
from .coordinator import TandoorDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.TODO]

# Setup is only via the UI config flow; there is no YAML configuration.
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

SEARCH_RECIPES_SCHEMA = vol.Schema(
    {
        vol.Optional("config_entry_id"): cv.string,
        vol.Optional(ATTR_QUERY): cv.string,
        vol.Optional(ATTR_LIMIT, default=10): vol.Coerce(int),
    }
)

ADD_MEAL_PLAN_SCHEMA = vol.Schema(
    {
        vol.Required("config_entry_id"): cv.string,
        vol.Optional(ATTR_RECIPE_ID): vol.Coerce(int),
        vol.Required(ATTR_MEAL_TYPE_ID): vol.Coerce(int),
        vol.Optional(ATTR_DATE): cv.date,
        vol.Optional(ATTR_SERVINGS, default=1): vol.Coerce(float),
        vol.Optional(ATTR_NOTE, default=""): cv.string,
    }
)

ADD_SHOPPING_LIST_ITEM_SCHEMA = vol.Schema(
    {
        vol.Required("config_entry_id"): cv.string,
        vol.Required(ATTR_NAME): cv.string,
        vol.Optional(ATTR_AMOUNT, default=0): vol.Coerce(float),
        vol.Optional(ATTR_UNIT): cv.string,
    }
)


def _get_coordinator(
    hass: HomeAssistant, config_entry_id: str | None = None
) -> TandoorDataUpdateCoordinator:
    entries: dict[str, TandoorDataUpdateCoordinator] = hass.data.get(DOMAIN, {})
    if not entries:
        raise HomeAssistantError("No Tandoor integration is configured")
    if config_entry_id is None:
        if len(entries) > 1:
            raise HomeAssistantError(
                "Multiple Tandoor instances configured; specify config_entry_id"
            )
        return next(iter(entries.values()))
    coordinator = entries.get(config_entry_id)
    if coordinator is None:
        raise HomeAssistantError(f"Unknown Tandoor config entry: {config_entry_id}")
    return coordinator


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register the (config-entry-scoped) services once at integration load."""

    async def handle_search_recipes(call: ServiceCall) -> dict:
        coordinator = _get_coordinator(hass, call.data.get("config_entry_id"))
        results = await coordinator.client.search_recipes(
            query=call.data.get(ATTR_QUERY), limit=call.data.get(ATTR_LIMIT, 10)
        )
        return {
            "recipes": [
                {
                    "id": r["id"],
                    "name": r["name"],
                    "image": r.get("image"),
                    "servings": r.get("servings"),
                }
                for r in results
            ]
        }

    async def handle_add_meal_plan(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass, call.data["config_entry_id"])
        plan_date = call.data.get(ATTR_DATE) or date.today()
        await coordinator.client.add_meal_plan(
            recipe_id=call.data.get(ATTR_RECIPE_ID),
            meal_type_id=call.data[ATTR_MEAL_TYPE_ID],
            plan_date=plan_date,
            servings=call.data.get(ATTR_SERVINGS, 1),
            note=call.data.get(ATTR_NOTE, ""),
        )
        await coordinator.async_request_refresh()

    async def handle_add_shopping_list_item(call: ServiceCall) -> None:
        coordinator = _get_coordinator(hass, call.data["config_entry_id"])
        await coordinator.client.add_shopping_list_item(
            name=call.data[ATTR_NAME],
            amount=call.data.get(ATTR_AMOUNT, 0),
            unit=call.data.get(ATTR_UNIT),
        )
        await coordinator.async_request_refresh()

    hass.services.async_register(
        DOMAIN,
        SERVICE_SEARCH_RECIPES,
        handle_search_recipes,
        schema=SEARCH_RECIPES_SCHEMA,
        supports_response="only",
    )
    hass.services.async_register(
        DOMAIN, SERVICE_ADD_MEAL_PLAN, handle_add_meal_plan, schema=ADD_MEAL_PLAN_SCHEMA
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_ADD_SHOPPING_LIST_ITEM,
        handle_add_shopping_list_item,
        schema=ADD_SHOPPING_LIST_ITEM_SCHEMA,
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tandoor Recipes from a config entry."""
    session = async_get_clientsession(
        hass, verify_ssl=entry.data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)
    )
    client = TandoorClient(
        session,
        entry.data[CONF_HOST],
        entry.data[CONF_API_TOKEN],
        verify_ssl=entry.data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
    )

    try:
        await client.get_current_space()
    except TandoorAuthError as err:
        raise ConfigEntryNotReady(f"Invalid Tandoor API token: {err}") from err
    except TandoorApiError as err:
        raise ConfigEntryNotReady(f"Cannot reach Tandoor at {entry.data[CONF_HOST]}: {err}") from err

    coordinator = TandoorDataUpdateCoordinator(hass, client)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
