import logging
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.fetcher import fetch_html_via_flaresolverr
from app.models import GYUMRI_KEYWORDS, FeedKey, Listing, Source

logger = logging.getLogger(__name__)

_MARKETPLACE_ITEM_RE = re.compile(r"/marketplace/item/(\d+)")


def _parse_facebook_cookies(raw: str | None) -> list[dict[str, str]] | None:
    if not raw:
        return None
    cookies: list[dict[str, str]] = []
    for part in raw.split(";"):
        part = part.strip()
        if not part or "=" not in part:
            continue
        name, value = part.split("=", 1)
        cookies.append({"name": name.strip(), "value": value.strip(), "domain": ".facebook.com"})
    return cookies or None


def parse_facebook_marketplace_html(html: str, *, feed_key: FeedKey, page_url: str) -> list[Listing]:
    soup = BeautifulSoup(html, "lxml")
    listings: list[Listing] = []
    seen: set[str] = set()

    for anchor in soup.find_all("a", href=True):
        href = anchor["href"]
        match = _MARKETPLACE_ITEM_RE.search(href)
        if not match:
            continue

        listing_id = match.group(1)
        if listing_id in seen:
            continue

        title = anchor.get("aria-label") or anchor.get_text(" ", strip=True)
        if not title or len(title) < 5:
            continue

        blob = f"{title} {href}".lower()
        if not any(k in blob for k in GYUMRI_KEYWORDS):
            # Marketplace URL is already Gyumri-scoped; keep items without explicit keyword too.
            pass

        full_url = urljoin(page_url, href.split("?", 1)[0])
        seen.add(listing_id)
        listings.append(
            Listing(
                source=Source.FACEBOOK,
                feed_key=feed_key,
                listing_id=listing_id,
                title=title[:500],
                url=full_url,
            )
        )

    return listings


async def scrape_facebook(url: str, feed_key: FeedKey, *, cookie_header: str | None) -> list[Listing]:
    cookies = _parse_facebook_cookies(cookie_header)
    html = await fetch_html_via_flaresolverr(url, cookies=cookies)
    if "login" in html.lower() and 'id="loginform"' in html.lower():
        logger.warning("Facebook returned login page — set FACEBOOK_COOKIE in .env")
        return []

    items = parse_facebook_marketplace_html(html, feed_key=feed_key, page_url=url)
    logger.info("Facebook %s: parsed %s listings", feed_key.value, len(items))
    return items
