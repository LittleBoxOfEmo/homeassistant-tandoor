"""Thin async client for the Tandoor Recipes REST API.

Only wraps the handful of endpoints this integration actually uses
(space/current, recipe, meal-plan, shopping-list-entry). Not a full
client for the whole Tandoor API surface.
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)


class TandoorApiError(Exception):
    """Raised for any non-2xx response from the Tandoor API."""

    def __init__(self, status: int, message: str) -> None:
        self.status = status
        super().__init__(f"Tandoor API error {status}: {message}")


class TandoorAuthError(TandoorApiError):
    """Raised on 401/403 responses."""


class TandoorClient:
    """Minimal async wrapper around the Tandoor REST API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        api_token: str,
        verify_ssl: bool = True,
    ) -> None:
        self._session = session
        self._base_url = host.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {api_token}",
            "Accept": "application/json",
        }
        self._verify_ssl = verify_ssl

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> Any:
        url = f"{self._base_url}/{path.strip('/')}/"
        clean_params = None
        if params:
            clean_params = {k: v for k, v in params.items() if v is not None}

        try:
            async with self._session.request(
                method,
                url,
                headers=self._headers,
                params=clean_params,
                json=json,
                ssl=self._verify_ssl,
            ) as resp:
                text = await resp.text()
                if resp.status in (401, 403):
                    raise TandoorAuthError(resp.status, text)
                if resp.status >= 400:
                    raise TandoorApiError(resp.status, text)
                if resp.status == 204 or not text:
                    return None
                return await resp.json(content_type=None)
        except aiohttp.ClientError as err:
            raise TandoorApiError(0, str(err)) from err

    # -- connectivity / auth check -------------------------------------------------

    async def get_current_space(self) -> dict[str, Any]:
        return await self._request("GET", "/api/space/current")

    # -- recipes ---------------------------------------------------------------

    async def search_recipes(self, query: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
        params = {"query": query, "page_size": limit}
        data = await self._request("GET", "/api/recipe", params=params)
        return data.get("results", []) if data else []

    async def get_recipe(self, recipe_id: int) -> dict[str, Any]:
        return await self._request("GET", f"/api/recipe/{recipe_id}")

    # -- meal plan ---------------------------------------------------------------

    async def get_meal_plan(
        self, from_date: date, to_date: date
    ) -> list[dict[str, Any]]:
        params = {
            "from_date": from_date.isoformat(),
            "to_date": to_date.isoformat(),
            "page_size": 200,
        }
        data = await self._request("GET", "/api/meal-plan", params=params)
        return data.get("results", []) if data else []

    async def add_meal_plan(
        self,
        recipe_id: int | None,
        meal_type_id: int,
        plan_date: date,
        servings: float = 1,
        note: str = "",
        title: str = "",
    ) -> dict[str, Any]:
        start = datetime.combine(plan_date, datetime.min.time()).isoformat()
        body: dict[str, Any] = {
            "title": title,
            "recipe": recipe_id,
            "servings": servings,
            "note": note,
            "from_date": start,
            "to_date": start,
            "meal_type": meal_type_id,
        }
        return await self._request("POST", "/api/meal-plan", json=body)

    async def get_meal_types(self) -> list[dict[str, Any]]:
        data = await self._request("GET", "/api/meal-type", params={"page_size": 100})
        return data.get("results", []) if data else []

    # -- shopping list -------------------------------------------------------------

    async def get_shopping_list_entries(self) -> list[dict[str, Any]]:
        data = await self._request(
            "GET", "/api/shopping-list-entry", params={"page_size": 200}
        )
        return data.get("results", []) if data else []

    async def add_shopping_list_item(
        self, name: str, amount: float = 0, unit: str | None = None
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "food": {"name": name},
            "amount": amount,
        }
        if unit:
            body["unit"] = {"name": unit}
        return await self._request("POST", "/api/shopping-list-entry", json=body)

    async def set_shopping_list_item_checked(
        self, entry_id: int, checked: bool
    ) -> dict[str, Any]:
        return await self._request(
            "PATCH",
            f"/api/shopping-list-entry/{entry_id}",
            json={"checked": checked},
        )

    async def delete_shopping_list_item(self, entry_id: int) -> None:
        await self._request("DELETE", f"/api/shopping-list-entry/{entry_id}")
