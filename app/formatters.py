from app.models import FEED_LABELS, Listing


def format_listing_message(item: Listing) -> str:
    feed_label = FEED_LABELS.get(item.feed_key, item.feed_key.value)
    lines = [
        f"🏠 <b>{_escape(item.title)}</b>",
        f"📍 {feed_label}",
    ]
    if item.price_text:
        lines.append(f"💰 {_escape(item.price_text)}")
    if item.location_text:
        lines.append(f"🗺 {_escape(item.location_text)}")
    if item.posted_at_text:
        lines.append(f"🕒 {_escape(item.posted_at_text)}")
    lines.append(f'<a href="{item.url}">Открыть объявление</a>')
    return "\n".join(lines)


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
