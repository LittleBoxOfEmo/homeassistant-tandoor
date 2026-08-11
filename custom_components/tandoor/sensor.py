"""Sensor platform for Tandoor Recipes."""
from __future__ import annotations

from datetime import date, datetime

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import TandoorDataUpdateCoordinator


def _device_info(entry: ConfigEntry) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name="Tandoor Recipes",
        manufacturer="Tandoor",
        configuration_url=entry.data.get("host"),
    )


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: TandoorDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            TandoorTodayMealsSensor(coordinator, entry),
            TandoorShoppingListCountSensor(coordinator, entry),
        ]
    )


def _parse_date(value: str) -> date:
    return datetime.fromisoformat(value).date()


class TandoorTodayMealsSensor(CoordinatorEntity[TandoorDataUpdateCoordinator], SensorEntity):
    """Shows the number of meals planned for today, with the meal list as an attribute."""

    _attr_has_entity_name = True
    _attr_name = "Today's meals"
    _attr_icon = "mdi:silverware-fork-knife"

    def __init__(self, coordinator: TandoorDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_today_meals"
        self._attr_device_info = _device_info(entry)

    def _todays_entries(self) -> list[dict]:
        today = date.today()
        return [
            m
            for m in self.coordinator.data.meal_plan
            if _parse_date(m["from_date"]) == today
        ]

    @property
    def native_value(self) -> int:
        return len(self._todays_entries())

    @property
    def extra_state_attributes(self) -> dict:
        meals = []
        for m in self._todays_entries():
            meals.append(
                {
                    "title": m.get("title") or m.get("recipe_name"),
                    "recipe_name": m.get("recipe_name"),
                    "meal_type": m.get("meal_type_name"),
                    "servings": m.get("servings"),
                }
            )
        return {"meals": meals}


class TandoorShoppingListCountSensor(
    CoordinatorEntity[TandoorDataUpdateCoordinator], SensorEntity
):
    """Number of open (unchecked) shopping list items."""

    _attr_has_entity_name = True
    _attr_name = "Shopping list items"
    _attr_icon = "mdi:cart-outline"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: TandoorDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_shopping_list_count"
        self._attr_device_info = _device_info(entry)

    @property
    def native_value(self) -> int:
        return len(self.coordinator.data.shopping_list)
