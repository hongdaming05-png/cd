"""Only HTTP crosses the frontend/backend boundary."""

import httpx


class APIError(Exception):
    def __init__(self, message: str, status: int = 0):
        super().__init__(message)
        self.status = status


class APIClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    async def request(self, method: str, path: str, body: dict | None = None):
        try:
            async with httpx.AsyncClient(timeout=135) as client:
                response = await client.request(method, self.base_url + path, json=body)
        except httpx.HTTPError as exc:
            raise APIError("暫時連不上教學服務，進度會保留。請稍後按「重新連線」。") from exc
        if response.is_error:
            try:
                detail = response.json().get("detail")
            except ValueError:
                detail = None
            message = detail if isinstance(detail, str) else "暫時無法完成，請稍後再試。"
            raise APIError(message, response.status_code)
        return response.json()
