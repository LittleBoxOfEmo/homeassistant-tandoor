"""Sensor platform for Tandoor Recipes."""
from __future__ import annotations

from datetime import date, datetime

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import TandoorDataUpdateCoordinator
from .entity import tandoor_device_info


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: TandoorDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            TandoorTodayMealsSensor(coordinator, entry),
            TandoorNextMealSensor(coordinator, entry),
            TandoorUpcomingMealsSensor(coordinator, entry),
            TandoorShoppingListCountSensor(coordinator, entry),
        ]
    )


def _parse_date(value: str) -> date:
    return datetime.fromisoformat(value).date()


def _meal_summary(m: dict) -> dict:
    return {
        "title": m.get("title") or m.get("recipe_name"),
        "recipe_name": m.get("recipe_name"),
        "recipe_id": (m.get("recipe") or {}).get("id"),
        "meal_type": m.get("meal_type_name"),
        "servings": m.get("servings"),
        "date": _parse_date(m["from_date"]).isoformat(),
    }


def _sort_key(m: dict) -> tuple:
    meal_type = m.get("meal_type") or {}
    return (_parse_date(m["from_date"]), meal_type.get("order", 0))


class TandoorTodayMealsSensor(CoordinatorEntity[TandoorDataUpdateCoordinator], SensorEntity):
    """Shows the number of meals planned for today, with the meal list as an attribute."""

    _attr_has_entity_name = True
    _attr_name = "Today's meals"
    _attr_icon = "mdi:silverware-fork-knife"

    def __init__(self, coordinator: TandoorDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_today_meals"
        self._attr_device_info = tandoor_device_info(entry)

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
        return {"meals": [_meal_summary(m) for m in self._todays_entries()]}


class TandoorNextMealSensor(CoordinatorEntity[TandoorDataUpdateCoordinator], SensorEntity):
    """The next upcoming planned meal (today or later), by date/meal-type order."""

    _attr_has_entity_name = True
    _attr_name = "Next meal"
    _attr_icon = "mdi:silverware-variant"

    def __init__(self, coordinator: TandoorDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_next_meal"
        self._attr_device_info = tandoor_device_info(entry)

    def _next_entry(self) -> dict | None:
        today = date.today()
        upcoming = sorted(
            (m for m in self.coordinator.data.meal_plan if _parse_date(m["from_date"]) >= today),
            key=_sort_key,
        )
        return upcoming[0] if upcoming else None

    @property
    def native_value(self) -> str | None:
        entry = self._next_entry()
        if entry is None:
            return None
        return entry.get("title") or entry.get("recipe_name") or "Untitled"

    @property
    def extra_state_attributes(self) -> dict:
        entry = self._next_entry()
        return _meal_summary(entry) if entry else {}


class TandoorUpcomingMealsSensor(CoordinatorEntity[TandoorDataUpdateCoordinator], SensorEntity):
    """Number of meals planned from today through the coordinator's polling window."""

    _attr_has_entity_name = True
    _attr_name = "Upcoming meals"
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator: TandoorDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_upcoming_meals"
        self._attr_device_info = tandoor_device_info(entry)

    def _upcoming_entries(self) -> list[dict]:
        today = date.today()
        return sorted(
            (m for m in self.coordinator.data.meal_plan if _parse_date(m["from_date"]) >= today),
            key=_sort_key,
        )

    @property
    def native_value(self) -> int:
        return len(self._upcoming_entries())

    @property
    def extra_state_attributes(self) -> dict:
        return {"meals": [_meal_summary(m) for m in self._upcoming_entries()]}


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
        self._attr_device_info = tandoor_device_info(entry)

    @property
    def native_value(self) -> int:
        return len(self.coordinator.data.shopping_list)
