"""FastAPI backend uchun async HTTP klient (X-API-Key bilan)."""

from typing import Any
from uuid import UUID

import httpx


class OmborApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str, details: Any = None) -> None:
        super().__init__(f"[{status_code} {code}] {message}")
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


class OmborApiClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        timeout: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._http = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"X-API-Key": api_key, "Accept": "application/json"},
            timeout=timeout,
            transport=transport,
        )

    async def __aenter__(self) -> "OmborApiClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._http.aclose()

    async def request(
        self, method: str, path: str, *, params: dict[str, Any] | None = None, json: Any = None
    ) -> Any:
        clean_params = {k: v for k, v in (params or {}).items() if v is not None}
        response = await self._http.request(method, path, params=clean_params, json=json)
        if response.status_code == 204:
            return None
        if response.is_error:
            raise self._to_error(response)
        return response.json()

    async def get(self, path: str, **params: Any) -> Any:
        return await self.request("GET", path, params=params)

    async def post(self, path: str, body: Any) -> Any:
        return await self.request("POST", path, json=body)

    # ------------------------------------------------------- AI buyruqlar navbati
    async def claim_command(self, worker_id: str) -> dict[str, Any] | None:
        return await self.post("/ai/commands/claim", {"worker_id": worker_id})

    async def update_command(self, command_id: UUID | str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.request("PATCH", f"/ai/commands/{command_id}", json=payload)

    @staticmethod
    def _to_error(response: httpx.Response) -> OmborApiError:
        try:
            error = response.json().get("error", {})
        except ValueError:
            error = {}
        return OmborApiError(
            response.status_code,
            error.get("code", "http_error"),
            error.get("message", response.text[:300] or response.reason_phrase),
            error.get("details"),
        )
