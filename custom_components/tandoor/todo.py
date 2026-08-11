"""Todo platform for Tandoor Recipes - mirrors the Tandoor shopping list."""
from __future__ import annotations

import logging

from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import TandoorDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: TandoorDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([TandoorShoppingListEntity(coordinator, entry)])


def _food_name(entry_data: dict) -> str:
    food = entry_data.get("food") or {}
    return food.get("name", "Unknown item")


def _to_todo_item(entry_data: dict) -> TodoItem:
    amount = entry_data.get("amount") or 0
    unit = (entry_data.get("unit") or {}).get("name")
    name = _food_name(entry_data)
    if amount:
        summary = f"{amount:g} {unit} {name}".strip() if unit else f"{amount:g} {name}"
    else:
        summary = name
    return TodoItem(
        summary=summary,
        uid=str(entry_data["id"]),
        status=(
            TodoItemStatus.COMPLETED
            if entry_data.get("checked")
            else TodoItemStatus.NEEDS_ACTION
        ),
    )


class TandoorShoppingListEntity(
    CoordinatorEntity[TandoorDataUpdateCoordinator], TodoListEntity
):
    """A HA todo list backed by the Tandoor shopping list."""

    _attr_has_entity_name = True
    _attr_name = "Shopping list"
    _attr_icon = "mdi:cart-outline"
    _attr_supported_features = (
        TodoListEntityFeature.CREATE_TODO_ITEM
        | TodoListEntityFeature.UPDATE_TODO_ITEM
        | TodoListEntityFeature.DELETE_TODO_ITEM
    )

    def __init__(self, coordinator: TandoorDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_shopping_list"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Tandoor Recipes",
            manufacturer="Tandoor",
            configuration_url=entry.data.get("host"),
        )

    @property
    def todo_items(self) -> list[TodoItem]:
        return [
            _to_todo_item(e)
            for e in self.coordinator.data.shopping_list
            if not e.get("checked")
        ]

    async def async_create_todo_item(self, item: TodoItem) -> None:
        await self.coordinator.client.add_shopping_list_item(name=item.summary)
        await self.coordinator.async_request_refresh()

    async def async_update_todo_item(self, item: TodoItem) -> None:
        checked = item.status == TodoItemStatus.COMPLETED
        await self.coordinator.client.set_shopping_list_item_checked(
            int(item.uid), checked
        )
        await self.coordinator.async_request_refresh()

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        for uid in uids:
            await self.coordinator.client.delete_shopping_list_item(int(uid))
        await self.coordinator.async_request_refresh()
