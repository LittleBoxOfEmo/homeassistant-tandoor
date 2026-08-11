"""Shared entity helpers for Tandoor Recipes."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN


def tandoor_device_info(entry: ConfigEntry) -> DeviceInfo:
    """Build the DeviceInfo shared by all entities of a Tandoor config entry."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name="Tandoor Recipes",
        manufacturer="Tandoor",
        configuration_url=entry.data.get("host"),
    )
