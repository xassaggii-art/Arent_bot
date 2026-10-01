import logging
import re
from urllib.parse import urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup

from app.fetcher import fetch_html_via_flaresolverr
from app.models import FeedKey, Listing, Source

logger = logging.getLogger(__name__)

_ITEM_ID_RE = re.compile(r"/item/(\d+)")


def parse_list_am_html(html: str, *, feed_key: FeedKey, page_url: str) -> list[Listing]:
    soup = BeautifulSoup(html, "lxml")
    listings: list[Listing] = []
    seen: set[str] = set()

    for anchor in soup.select('a.fav-item-info-container[href*="/item/"]'):
        href = anchor.get("href")
        if not href:
            continue

        full_url = _normalize_item_url(href, page_url)
        match = _ITEM_ID_RE.search(href)
        listing_id = match.group(1) if match else full_url
        if listing_id in seen:
            continue

        title_el = anchor.select_one(".dltitle .pt")
        title = title_el.get_text(strip=True) if title_el else ""
        if not title:
            continue

        price_el = anchor.select_one(".ad-info-line-wrapper .p")
        price_text = price_el.get_text(strip=True) if price_el else None

        location_text = _extract_location(anchor)

        date_el = anchor.select_one(".d")
        posted_at_text = date_el.get_text(strip=True) if date_el else None

        image_url = _extract_image(anchor, page_url)

        seen.add(listing_id)
        listings.append(
            Listing(
                source=Source.LIST_AM,
                feed_key=feed_key,
                listing_id=listing_id,
                title=title,
                url=full_url,
                price_text=price_text,
                location_text=location_text,
                posted_at_text=posted_at_text,
                image_url=image_url,
            )
        )

    return listings


async def scrape_list_am(url: str, feed_key: FeedKey) -> list[Listing]:
    html = await fetch_html_via_flaresolverr(url)
    items = parse_list_am_html(html, feed_key=feed_key, page_url=url)
    logger.info("List.am %s: parsed %s listings", feed_key.value, len(items))
    return items


def _normalize_item_url(href: str, base: str) -> str:
    joined = urljoin(base, href)
    parsed = urlparse(joined)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


def _extract_image(anchor, base: str) -> str | None:
    img = anchor.find("img")
    if not img:
        return None
    src = img.get("data-original") or img.get("src") or img.get("data-src")
    if not src:
        return None
    if src.startswith("//"):
        return f"https:{src}"
    return urljoin(base, src)


def _extract_location(anchor) -> str | None:
    for at in anchor.select(".at"):
        text = at.get_text(strip=True)
        if not text:
            continue
        if text.startswith("Подходит для") or text.startswith("Suitable for"):
            continue
        if "," in text and ("г." in text or "km" in text.lower()):
            continue
        if len(text) < 80:
            return text
    return None
