"""Data update coordinator for Tandoor Recipes."""
from __future__ import annotations

import logging
from datetime import date, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import TandoorApiError, TandoorAuthError, TandoorClient
from .const import DOMAIN, UPDATE_INTERVAL_MINUTES

_LOGGER = logging.getLogger(__name__)


class TandoorData:
    """Container for the data this integration polls."""

    def __init__(self) -> None:
        self.meal_plan: list[dict] = []
        self.shopping_list: list[dict] = []
        self.meal_types: list[dict] = []


class TandoorDataUpdateCoordinator(DataUpdateCoordinator[TandoorData]):
    """Polls Tandoor for today's meal plan and the active shopping list."""

    def __init__(self, hass: HomeAssistant, client: TandoorClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=UPDATE_INTERVAL_MINUTES),
        )
        self.client = client
        self._meal_types_cache: list[dict] | None = None

    async def _async_update_data(self) -> TandoorData:
        data = TandoorData()
        try:
            today = date.today()
            data.meal_plan = await self.client.get_meal_plan(
                today, today + timedelta(days=13)
            )
            data.shopping_list = await self.client.get_shopping_list_entries()
            if self._meal_types_cache is None:
                self._meal_types_cache = await self.client.get_meal_types()
            data.meal_types = self._meal_types_cache
        except TandoorAuthError as err:
            raise UpdateFailed(f"Authentication failed: {err}") from err
        except TandoorApiError as err:
            raise UpdateFailed(f"Error communicating with Tandoor: {err}") from err
        return data
