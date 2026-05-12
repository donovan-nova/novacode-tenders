from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import httpx
import os

router_proxy = APIRouter()

@router_proxy.post("/api/proxy/claude")
async def claude_proxy(request: Request):
    try:
        body = await request.json()
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            return JSONResponse({"error": "ANTHROPIC_API_KEY not set"}, status_code=500)
        async with httpx.AsyncClient(timeout=180) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                json=body,
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
            )
            data = resp.json()
            return JSONResponse(content=data, status_code=resp.status_code)
    except Exception as e:
        import traceback
        return JSONResponse({"error": str(e), "trace": traceback.format_exc()}, status_code=500)
