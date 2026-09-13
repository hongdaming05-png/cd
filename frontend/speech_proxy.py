"""Same-origin upload bridge: browser does not need the backend port."""

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response


def create_speech_proxy(api_url: str) -> APIRouter:
    router = APIRouter()

    @router.post("/api/transcribe")
    async def transcribe(request: Request):
        chunks = []
        size = 0
        async for chunk in request.stream():
            size += len(chunk)
            if size > 21 * 1024 * 1024:
                return JSONResponse({"detail": "錄音太大，請分段說明。"}, status_code=413)
            chunks.append(chunk)
        try:
            async with httpx.AsyncClient(timeout=180) as client:
                result = await client.post(
                    api_url.rstrip("/") + "/api/transcribe",
                    content=b"".join(chunks),
                    headers={"Content-Type": request.headers.get("content-type", "")},
                )
            if "application/json" not in result.headers.get("content-type", ""):
                return JSONResponse({"detail": "語音服務回應異常，請稍後再試。"}, status_code=502)
            return Response(
                result.content, status_code=result.status_code, media_type="application/json"
            )
        except httpx.HTTPError:
            return JSONResponse({"detail": "暫時連不上語音服務，請稍後再試。"}, status_code=503)

    return router
