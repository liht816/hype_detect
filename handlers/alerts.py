from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram.error import BadRequest

from utils.keyboards import alerts_home_keyboard, alert_threshold_keyboard, back_to_menu_keyboard
from database.connection import async_session
from database.repositories import UserRepository, AlertRepository
from services.mexc import MexcService

mexc = MexcService()

async def _safe_edit_or_send(q, text: str, reply_markup=None):
    try:
        await q.edit_message_text(text=text, parse_mode="Markdown", reply_markup=reply_markup)
    except BadRequest as e:
        if "Message is not modified" in str(e):
            return
        await q.message.reply_text(text=text, parse_mode="Markdown", reply_markup=reply_markup)

async def alerts_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await _safe_edit_or_send(
        q,
        "🔔 *Алерты*\n\nВыбери действие:",
        reply_markup=alerts_home_keyboard()
    )

async def alert_setup_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    coin_id = q.data.split(":")[2]
    await q.message.reply_text(
        f"🔔 *Алерт для* `{coin_id}`\n\nВыбери порог изменения цены:",
        parse_mode="Markdown",
        reply_markup=alert_threshold_keyboard(coin_id)
    )

async def alert_set_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    _, _, coin_id, pct = q.data.split(":")
    pct = int(pct)

    async with async_session() as session:
        user_repo = UserRepository(session)
        alert_repo = AlertRepository(session)
        db_user = await user_repo.get_or_create(
            telegram_id=q.from_user.id,
            username=q.from_user.username,
            first_name=q.from_user.first_name
        )
        await alert_repo.create(
            user=db_user,
            alert_type="price_change",
            coin_id=coin_id,
            coin_symbol=None,
            condition={"threshold_percent": pct, "market": context.user_data.get("market_mode", "spot")}
        )

    await q.message.reply_text(
        f"✅ Алерт создан для *{coin_id}*\nУведомлю при изменении цены на *{pct}%*.",
        parse_mode="Markdown",
        reply_markup=alerts_home_keyboard()
    )

async def alert_list_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    async with async_session() as session:
        user_repo = UserRepository(session)
        alert_repo = AlertRepository(session)
        db_user = await user_repo.get_or_create(
            telegram_id=q.from_user.id,
            username=q.from_user.username,
            first_name=q.from_user.first_name
        )
        alerts = await alert_repo.get_active_by_user(db_user)

    if not alerts:
        await _safe_edit_or_send(q, "📋 *Мои алерты*\n\nПока пусто.", reply_markup=alerts_home_keyboard())
        return

    text = "📋 *Мои алерты*\n\n"
    for a in alerts[:30]:
        pct = (a.condition or {}).get("threshold_percent", "?")
        mkt = (a.condition or {}).get("market", "spot")
        text += f"• `{a.coin_id}` — {pct}% ({mkt})  id={a.id}\n"

    await _safe_edit_or_send(q, text, reply_markup=alerts_home_keyboard())

async def alert_new_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["awaiting_alert_coin"] = True
    await _safe_edit_or_send(
        q,
        "➕ *Создать алерт*\n\nНапиши монету (например `BTCUSDT` или `btc`).",
        reply_markup=back_to_menu_keyboard()
    )

async def handle_alert_coin_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not context.user_data.get("awaiting_alert_coin"):
        return False
    context.user_data["awaiting_alert_coin"] = False

    query = (update.message.text or "").strip()
    symbol = await mexc.resolve_symbol(query, market=context.user_data.get("market_mode", "spot"))
    if not symbol:
        await update.message.reply_text("😕 Не нашёл символ на MEXC. Пример: BTCUSDT")
        return True

    await update.message.reply_text(
        f"🔔 *Алерт для* `{symbol}`\n\nВыбери порог:",
        parse_mode="Markdown",
        reply_markup=alert_threshold_keyboard(symbol)
    )
    return True

def register_alerts_handlers(app):
    app.add_handler(CallbackQueryHandler(alerts_menu_callback, pattern=r"^menu:alerts$"))
    app.add_handler(CallbackQueryHandler(alert_new_callback, pattern=r"^alert:new$"))
    app.add_handler(CallbackQueryHandler(alert_list_callback, pattern=r"^alert:list$"))
    app.add_handler(CallbackQueryHandler(alert_setup_callback, pattern=r"^alert:setup:"))
    app.add_handler(CallbackQueryHandler(alert_set_callback, pattern=r"^alert:set:"))