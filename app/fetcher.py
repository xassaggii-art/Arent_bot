import logging
from typing import Any

import aiohttp

from app.config import settings

logger = logging.getLogger(__name__)


class FetchError(Exception):
    pass


async def fetch_html_via_flaresolverr(
    url: str,
    *,
    cookies: list[dict[str, Any]] | None = None,
) -> str:
    payload: dict[str, Any] = {
        "cmd": "request.get",
        "url": url,
        "maxTimeout": settings.flaresolverr_max_timeout_ms,
    }
    if cookies:
        payload["cookies"] = cookies

    endpoint = settings.flaresolverr_url.rstrip("/") + "/v1"

    timeout = aiohttp.ClientTimeout(total=settings.flaresolverr_max_timeout_ms / 1000 + 30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(endpoint, json=payload) as resp:
            body = await resp.json(content_type=None)

    if body.get("status") != "ok":
        message = body.get("message") or "FlareSolverr error"
        raise FetchError(message)

    solution = body.get("solution") or {}
    html = solution.get("response")
    if not html or not isinstance(html, str):
        raise FetchError("FlareSolverr returned empty HTML")

    if "Just a moment" in html and "challenges.cloudflare.com" in html:
        raise FetchError("Cloudflare challenge not solved")

    return html
