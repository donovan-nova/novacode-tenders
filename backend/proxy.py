
from fastapi import APIRouter, Request
import httpx
import os

router_proxy = APIRouter()

@router_proxy.post("/api/proxy/claude")
async def claude_proxy(request: Request):
    body = await request.json()
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            json=body,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
        )
    return resp.json()
