"""Calendar platform for Tandoor Recipes - exposes the meal plan as a calendar."""
from __future__ import annotations

from datetime import date, datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import TandoorDataUpdateCoordinator
from .entity import tandoor_device_info


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: TandoorDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([TandoorMealPlanCalendar(coordinator, entry)])


def _to_calendar_event(m: dict) -> CalendarEvent:
    from_date = datetime.fromisoformat(m["from_date"])
    meal_type = m.get("meal_type") or {}
    meal_time = meal_type.get("time")
    title = m.get("title") or m.get("recipe_name") or meal_type.get("name") or "Meal"
    summary = f"{meal_type['name']}: {title}" if meal_type.get("name") else title
    description = "\n".join(
        filter(
            None,
            [
                m.get("recipe_name"),
                f"Servings: {m['servings']}" if m.get("servings") else None,
                m.get("note"),
            ],
        )
    )

    if meal_time:
        hour, minute, *_ = (int(p) for p in meal_time.split(":"))
        start = dt_util.as_local(from_date).replace(
            hour=hour, minute=minute, second=0, microsecond=0
        )
        end = start + timedelta(hours=1)
    else:
        start = from_date.date()
        end = start + timedelta(days=1)

    return CalendarEvent(
        start=start,
        end=end,
        summary=summary,
        description=description or None,
        uid=str(m["id"]),
    )


def _end_as_local_datetime(end: date | datetime) -> datetime:
    """Normalize a CalendarEvent.end (date or datetime) to an aware local datetime."""
    if isinstance(end, datetime):
        return end if end.tzinfo else dt_util.as_local(end)
    return dt_util.as_local(datetime.combine(end, datetime.min.time()))


def _start_as_local_datetime(start: date | datetime) -> datetime:
    if isinstance(start, datetime):
        return start if start.tzinfo else dt_util.as_local(start)
    return dt_util.as_local(datetime.combine(start, datetime.min.time()))


class TandoorMealPlanCalendar(
    CoordinatorEntity[TandoorDataUpdateCoordinator], CalendarEntity
):
    """Calendar entity backed by the Tandoor meal plan."""

    _attr_has_entity_name = True
    _attr_name = "Meal plan"
    _attr_icon = "mdi:calendar-heart"

    def __init__(self, coordinator: TandoorDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_meal_plan_calendar"
        self._attr_device_info = tandoor_device_info(entry)

    @property
    def event(self) -> CalendarEvent | None:
        """The currently ongoing or next upcoming meal-plan event."""
        now = dt_util.now()
        events = sorted(
            (_to_calendar_event(m) for m in self.coordinator.data.meal_plan),
            key=lambda e: _start_as_local_datetime(e.start),
        )
        for event in events:
            if _end_as_local_datetime(event.end) >= now:
                return event
        return None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Fetch events directly from Tandoor for the requested range.

        Not served from the coordinator's cached window, since the calendar
        UI can page to arbitrary past/future date ranges outside it.
        """
        entries = await self.coordinator.client.get_meal_plan(
            start_date.date(), end_date.date()
        )
        return [_to_calendar_event(m) for m in entries]
