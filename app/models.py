from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Source(str, Enum):
    LIST_AM = "list_am"
    FACEBOOK = "facebook"


class FeedKey(str, Enum):
    RENT_LONG = "rent_long"
    RENT_DAILY = "rent_daily"
    SALE = "sale"
    ALL_REALESTATE = "all_realestate"
    FB_MARKETPLACE_RENT = "fb_marketplace_rent"
    FB_MARKETPLACE_SALE = "fb_marketplace_sale"


@dataclass(frozen=True)
class Listing:
    source: Source
    feed_key: FeedKey
    listing_id: str
    title: str
    url: str
    price_text: str | None = None
    location_text: str | None = None
    posted_at_text: str | None = None
    image_url: str | None = None

    @property
    def dedupe_key(self) -> str:
        return f"{self.source.value}:{self.listing_id}"


FEED_LABELS: dict[FeedKey, str] = {
    FeedKey.RENT_LONG: "List.am — долгосрочная аренда квартир (Гюмри)",
    FeedKey.RENT_DAILY: "List.am — посуточная аренда (Гюмри)",
    FeedKey.SALE: "List.am — продажа квартир (Гюмри)",
    FeedKey.ALL_REALESTATE: "List.am — вся недвижимость (Гюмри)",
    FeedKey.FB_MARKETPLACE_RENT: "Facebook Marketplace — аренда (Гюмри)",
    FeedKey.FB_MARKETPLACE_SALE: "Facebook Marketplace — продажа (Гюмри)",
}

LIST_AM_FEED_URLS: dict[FeedKey, str] = {
    FeedKey.RENT_LONG: "https://www.list.am/en/category/56?q=gyumri&srt=3",
    FeedKey.RENT_DAILY: "https://www.list.am/en/category/166?q=gyumri&srt=3",
    FeedKey.SALE: "https://www.list.am/en/category/60?q=gyumri&srt=3",
    FeedKey.ALL_REALESTATE: "https://www.list.am/en/category/54?q=gyumri&srt=3",
}

FACEBOOK_FEED_URLS: dict[FeedKey, str] = {
    FeedKey.FB_MARKETPLACE_RENT: (
        "https://www.facebook.com/marketplace/gyumri/search/?query=apartment%20rent"
    ),
    FeedKey.FB_MARKETPLACE_SALE: (
        "https://www.facebook.com/marketplace/gyumri/search/?query=apartment%20sale"
    ),
}

GYUMRI_KEYWORDS = (
    "gyumri",
    "giumri",
    "գյումրի",
    "гюмри",
)
