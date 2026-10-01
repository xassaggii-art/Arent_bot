from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.config import settings
from app.models import FACEBOOK_FEED_URLS, FEED_LABELS, LIST_AM_FEED_URLS, FeedKey
from app.storage import Database

router = Router()

LIST_AM_FEEDS = list(LIST_AM_FEED_URLS.keys())
FB_FEEDS = list(FACEBOOK_FEED_URLS.keys())


def _main_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="⚙️ Настроить подписки", callback_data="subs:edit")],
        [InlineKeyboardButton(text="✅ List.am — все категории", callback_data="subs:preset:list_am_all")],
        [InlineKeyboardButton(text="📋 Мои подписки", callback_data="subs:list")],
        [InlineKeyboardButton(text="⏸ Пауза / ▶️ Возобновить", callback_data="subs:toggle_pause")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _feeds_keyboard(db_feeds: set[FeedKey]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for key in LIST_AM_FEEDS:
        mark = "✅" if key in db_feeds else "⬜️"
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{mark} {FEED_LABELS[key]}",
                    callback_data=f"feed:toggle:{key.value}",
                )
            ]
        )
    if settings.facebook_enabled:
        for key in FB_FEEDS:
            mark = "✅" if key in db_feeds else "⬜️"
            rows.append(
                [
                    InlineKeyboardButton(
                        text=f"{mark} {FEED_LABELS[key]}",
                        callback_data=f"feed:toggle:{key.value}",
                    )
                ]
            )
    rows.append([InlineKeyboardButton(text="« Назад", callback_data="menu:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.message(CommandStart())
async def cmd_start(message: Message, db: Database) -> None:
    await db.ensure_subscriber(message.chat.id)
    text = (
        "Привет! Я присылаю новые объявления о <b>продаже и аренде квартир в Гюмри</b> "
        "с List.am."
        + "\n\nВыберите категории в «Настроить подписки». "
        "Первый проход по источникам запоминает текущие объявления — уведомления пойдут только о <b>новых</b>."
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⚙️ Настроить подписки", callback_data="subs:edit")],
            [InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help")],
        ]
    )
    await message.answer(text, parse_mode="HTML", reply_markup=kb)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(_help_text(), parse_mode="HTML")


@router.callback_query(F.data == "help")
async def cb_help(callback: CallbackQuery) -> None:
    await callback.message.edit_text(_help_text(), parse_mode="HTML", reply_markup=_main_keyboard())
    await callback.answer()


@router.callback_query(F.data == "menu:main")
async def cb_main(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "Главное меню. Настройте подписки или поставьте уведомления на паузу.",
        reply_markup=_main_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "subs:edit")
async def cb_edit_subs(callback: CallbackQuery, db: Database) -> None:
    enabled = set(await db.list_enabled_feeds(callback.message.chat.id))
    await callback.message.edit_text(
        "Отметьте категории, по которым нужны уведомления:",
        reply_markup=_feeds_keyboard(enabled),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("feed:toggle:"))
async def cb_toggle_feed(callback: CallbackQuery, db: Database) -> None:
    raw = callback.data.removeprefix("feed:toggle:")
    feed_key = FeedKey(raw)
    chat_id = callback.message.chat.id
    enabled_now = await db.is_feed_enabled(chat_id, feed_key)
    await db.set_feed(chat_id, feed_key, enabled=not enabled_now)
    enabled = set(await db.list_enabled_feeds(chat_id))
    await callback.message.edit_reply_markup(reply_markup=_feeds_keyboard(enabled))
    await callback.answer("Сохранено")


@router.callback_query(F.data == "subs:list")
async def cb_list_subs(callback: CallbackQuery, db: Database) -> None:
    feeds = await db.list_enabled_feeds(callback.message.chat.id)
    if not feeds:
        body = "Подписок пока нет. Нажмите «Настроить подписки»."
    else:
        body = "Активные подписки:\n" + "\n".join(f"• {FEED_LABELS[f]}" for f in feeds)
    paused = not await db.is_subscriber_enabled(callback.message.chat.id)
    if paused:
        body += "\n\n⏸ Уведомления на паузе."
    await callback.message.edit_text(body, reply_markup=_main_keyboard())
    await callback.answer()


@router.callback_query(F.data == "subs:preset:list_am_all")
async def cb_preset_list_am_all(callback: CallbackQuery, db: Database) -> None:
    chat_id = callback.message.chat.id
    for key in LIST_AM_FEEDS:
        await db.set_feed(chat_id, key, enabled=True)
    await callback.answer("Подключены все категории List.am для Гюмри", show_alert=True)
    enabled = set(await db.list_enabled_feeds(chat_id))
    await callback.message.edit_reply_markup(reply_markup=_feeds_keyboard(enabled))


@router.callback_query(F.data == "subs:toggle_pause")
async def cb_toggle_pause(callback: CallbackQuery, db: Database) -> None:
    chat_id = callback.message.chat.id
    enabled = await db.is_subscriber_enabled(chat_id)
    await db.set_subscriber_enabled(chat_id, not enabled)
    state = "возобновлены" if enabled else "на паузе"
    await callback.answer(f"Уведомления {state}", show_alert=True)


def _help_text() -> str:
    fb = (
        "\n• Facebook — экспериментально, часто нужны cookies в FACEBOOK_COOKIE."
        if settings.facebook_enabled
        else "\n• Facebook можно включить через FACEBOOK_ENABLED=true в .env."
    )
    return (
        "<b>Как это работает</b>\n"
        "Бот каждые несколько минут проверяет List.am (через FlareSolverr) "
        "и шлёт только новые объявления по выбранным категориям.\n\n"
        "<b>Команды</b>\n"
        "/start — меню\n"
        "/help — эта справка\n\n"
        "<b>Источники</b>\n"
        "• List.am — аренда (долгая/посуточная), продажа, вся недвижимость по запросу Gyumri"
        f"{fb}\n\n"
        "Похоже на @BrokerBotAM_bot: подписки по типам сделки и мгновенные алерты."
    )
