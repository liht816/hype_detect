"""
Анализ монеты (CoinGecko) + поддержка ввода в формате BTCUSDT.
Индекс перегрева считается по CoinGecko.
"""
from __future__ import annotations

from telegram import (
    Update, InputFile, InputMediaPhoto,
    InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import ContextTypes, MessageHandler, CallbackQueryHandler, filters
from telegram.error import BadRequest

from services import CoinGeckoService
from core.hype_calculator import HypeCalculator
from utils.keyboards import analyze_result_keyboard, prediction_keyboard, back_to_menu_keyboard
from utils.charts import create_hype_chart

from database.connection import async_session
from database.repositories import UserRepository, WatchlistRepository, AnalysisRepository, AlertRepository
from config import FREE_ANALYSES_PER_DAY, is_admin, SUPPORT_USERNAME


coingecko = CoinGeckoService()
heat_calc = HypeCalculator()


# ---------- helpers ----------

def _chg(val: float) -> str:
    if val > 0:
        return f"🟢 +{val:.2f}%"
    if val < 0:
        return f"🔴 {val:.2f}%"
    return f"⚪ {val:.2f}%"


def _buf_size(buf) -> int:
    try:
        buf.seek(0, 2)
        size = buf.tell()
        buf.seek(0)
        return size
    except Exception:
        return 0


def _as_input_file(buf, filename: str = "chart.png") -> InputFile | None:
    """
    Делает InputFile только если буфер реально не пустой.
    И обязательно ставит seek(0), иначе Telegram может прочитать 0 байт.
    """
    if buf is None:
        return None
    try:
        # проверяем размер
        buf.seek(0, 2)
        size = buf.tell()
        if size <= 0:
            return None
        buf.seek(0)
        return InputFile(buf, filename=filename)
    except Exception:
        return None


def _normalize_input_to_coingecko_query(text: str) -> str:
    """
    Принимаем:
      - BTC / btc / bitcoin
      - BTCUSDT / btcusdt
      - BTC/USDT / btc-usdt / btc usdt
    Приводим к запросу для CoinGecko:
      BTCUSDT -> btc
    """
    s = (text or "").strip().lower()
    s = s.replace("/", "").replace("-", "").replace(" ", "")
    if s.startswith("$"):
        s = s[1:]
    if s.endswith("usdt") and len(s) > 4:
        s = s[:-4]
    return s


def _alert_threshold_kb(coin_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("5%", callback_data=f"alert:set:{coin_id}:5"),
            InlineKeyboardButton("10%", callback_data=f"alert:set:{coin_id}:10"),
        ],
        [
            InlineKeyboardButton("20%", callback_data=f"alert:set:{coin_id}:20"),
            InlineKeyboardButton("30%", callback_data=f"alert:set:{coin_id}:30"),
        ],
        [
            InlineKeyboardButton("🏠 Главное меню", callback_data="menu:main"),
        ],
    ])


# ---------- handlers ----------

async def analyze_coin_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if not text or text.startswith("/"):
        return

    # админ ввод (если есть)
    try:
        from handlers.admin import admin_text_handler
        if await admin_text_handler(update, context):
            return
    except Exception:
        pass

    # redflag ввод (если есть)
    try:
        from handlers.redflag import handle_redflag_text
        if await handle_redflag_text(update, context):
            return
    except Exception:
        pass

    # алерт ввод (если есть alerts.py)
    try:
        from handlers.alerts import handle_alert_coin_text
        if await handle_alert_coin_text(update, context):
            return
    except Exception:
        pass

    if context.user_data.get("awaiting_compare_input"):
        return
    if context.user_data.get("awaiting_watchlist_add"):
        return
    if context.user_data.get("awaiting_portfolio_add"):
        return

    query = _normalize_input_to_coingecko_query(text)
    if len(query) < 2:
        return

    await _perform_analysis(update, context, query)


async def analyze_refresh_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    # отвечаем максимально рано, чтобы не словить "Query is too old"
    try:
        await q.answer("🔄 Обновляю...")
    except BadRequest:
        # Query could be too old — игнорируем
        pass

    parts = q.data.split(":")
    if len(parts) < 3:
        return
    coin_id = parts[2]

    try:
        await q.message.delete()
    except Exception:
        pass

    await _perform_analysis(update, context, coin_id, is_callback=True, query_is_coin_id=True)


async def alert_setup_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    callback_data: alert:setup:<coin_id>
    """
    q = update.callback_query
    try:
        await q.answer()
    except BadRequest:
        pass

    parts = q.data.split(":")
    if len(parts) < 3:
        return

    coin_id = parts[2]

    await q.message.reply_text(
        f"🔔 *Алерт для* `{coin_id}`\n\nВыбери порог изменения цены:",
        parse_mode="Markdown",
        reply_markup=_alert_threshold_kb(coin_id)
    )


async def alert_set_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    callback_data: alert:set:<coin_id>:<pct>
    """
    q = update.callback_query
    try:
        await q.answer()
    except BadRequest:
        pass

    parts = q.data.split(":")
    if len(parts) < 4:
        return

    coin_id = parts[2]
    pct = int(parts[3])

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
            condition={"threshold_percent": pct, "source": "coingecko"}
        )

    await q.message.reply_text(
        f"✅ Алерт создан для *{coin_id}*\n"
        f"Уведомлю при изменении цены примерно на *{pct}%*.",
        parse_mode="Markdown",
        reply_markup=back_to_menu_keyboard()
    )


async def _perform_analysis(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    query: str,
    is_callback: bool = False,
    query_is_coin_id: bool = False
):
    if is_callback:
        message = update.callback_query.message
        user = update.callback_query.from_user
    else:
        message = update.message
        user = update.effective_user

    async with async_session() as session:
        user_repo = UserRepository(session)
        analysis_repo = AnalysisRepository(session)
        watchlist_repo = WatchlistRepository(session)

        db_user = await user_repo.get_or_create(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name
        )

        # лимит (админ — безлимит)
        if not is_admin(user.id):
            personal_limit = getattr(db_user, "daily_analysis_limit", None)
            if personal_limit is None:
                personal_limit = FREE_ANALYSES_PER_DAY

            if personal_limit != -1:
                today_count = await analysis_repo.get_today_count(db_user)
                if today_count >= personal_limit:
                    await message.reply_text(
                        f"⚠️ *Лимит анализов исчерпан*\n\n"
                        f"Лимит на сегодня: *{personal_limit}*\n"
                        f"Сделано сегодня: *{today_count}*\n\n"
                        f"💎 Хочешь безлимит/повышенный лимит — напиши: {SUPPORT_USERNAME}",
                        parse_mode="Markdown",
                        reply_markup=back_to_menu_keyboard()
                    )
                    return

        status_msg = await message.reply_text(f"🔍 Ищу *{query}*...", parse_mode="Markdown")

        # 1) определяем coin_id
        if query_is_coin_id:
            coin_id = query
        else:
            coin = await coingecko.search_coin(query)
            if not coin:
                await status_msg.edit_text(
                    f"😕 Не нашёл монету по запросу *{query}*.\n\n"
                    "Попробуй:\n"
                    "• `btc` / `bitcoin`\n"
                    "• `eth` / `ethereum`\n"
                    "• или `BTCUSDT` (будет воспринято как `BTC`)",
                    parse_mode="Markdown",
                    reply_markup=back_to_menu_keyboard()
                )
                return
            coin_id = coin["id"]

        await status_msg.edit_text("📊 Загружаю данные CoinGecko...", parse_mode="Markdown")

        coin_data = await coingecko.get_coin_data(coin_id)
        if not coin_data:
            await status_msg.edit_text(
                "😕 CoinGecko не вернул данные. Попробуй позже.",
                reply_markup=back_to_menu_keyboard()
            )
            return

        name = coin_data.get("name", coin_id)
        symbol = (coin_data.get("symbol") or coin_id).upper()

        market = coin_data.get("market_data", {})
        current_price = float(market.get("current_price", {}).get("usd", 0) or 0)
        price_change_24h = float(market.get("price_change_percentage_24h", 0) or 0)
        price_change_7d = float(market.get("price_change_percentage_7d", 0) or 0)
        price_change_30d = float(market.get("price_change_percentage_30d", 0) or 0)
        market_cap = float(market.get("market_cap", {}).get("usd", 0) or 0)
        volume_24h = float(market.get("total_volume", {}).get("usd", 0) or 0)
        market_cap_rank = coin_data.get("market_cap_rank")

        analysis = heat_calc.calculate(
            price_change_24h=price_change_24h,
            price_change_7d=price_change_7d,
            market_cap=market_cap,
            volume_24h=volume_24h,
            market_cap_rank=market_cap_rank
        )

        # график
        price_history = await coingecko.get_price_history(coin_id, days=7)
        chart_buf = create_hype_chart(
            price_history=price_history or [],
            mentions_by_day={},
            coin_symbol=symbol,
            hype_score=analysis.score
        )

        photo = _as_input_file(chart_buf, "chart.png")

        caption = _format_result(
            name=name,
            symbol=symbol,
            coin_id=coin_id,
            heat_score=analysis.score,
            price=current_price,
            chg_24h=price_change_24h,
            chg_7d=price_change_7d,
            chg_30d=price_change_30d,
            market_cap_rank=market_cap_rank,
            market_cap=market_cap,
            volume_24h=volume_24h,
            reasons=analysis.reasons,
            recommendation=analysis.recommendation
        )

        in_watchlist = await watchlist_repo.exists(db_user, coin_id)

        # сохраняем историю
        await analysis_repo.save(
            user=db_user,
            coin_id=coin_id,
            coin_symbol=symbol,
            coin_name=name,
            hype_score=analysis.score,
            price=current_price,
            market_cap_rank=market_cap_rank,
            reddit_mentions=0,
            sentiment_score=0.5
        )
        await user_repo.increment_analyses(db_user)

        context.user_data["last_analysis"] = {
            "coin_id": coin_id,
            "coin_symbol": symbol,
            "coin_name": name,
            "price": current_price,
            "heat_score": analysis.score,
        }

        await status_msg.delete()

        if photo is None:
            # fallback: без картинки
            await message.reply_text(
                caption,
                parse_mode="Markdown",
                reply_markup=analyze_result_keyboard(coin_id, in_watchlist)
            )
        else:
            await message.reply_photo(
                photo=photo,
                caption=caption,
                parse_mode="Markdown",
                reply_markup=analyze_result_keyboard(coin_id, in_watchlist)
            )


def _format_result(
    name: str,
    symbol: str,
    coin_id: str,
    heat_score: int,
    price: float,
    chg_24h: float,
    chg_7d: float,
    chg_30d: float,
    market_cap_rank: int | None,
    market_cap: float,
    volume_24h: float,
    reasons: list[str],
    recommendation: str
) -> str:
    if heat_score >= 80:
        bar = "🔴🔴🔴🔴🔴"; status = "КРИТИЧЕСКИЙ"
    elif heat_score >= 60:
        bar = "🔴🔴🔴🔴⚪"; status = "ВЫСОКИЙ"
    elif heat_score >= 40:
        bar = "🟠🟠🟠⚪⚪"; status = "ПОВЫШЕННЫЙ"
    elif heat_score >= 20:
        bar = "🟡🟡⚪⚪⚪"; status = "УМЕРЕННЫЙ"
    else:
        bar = "🟢⚪⚪⚪⚪"; status = "НИЗКИЙ"

    reasons_text = "\n".join("• " + r for r in reasons) if reasons else "• Нет сильных рыночных аномалий"

    def price_str(p: float) -> str:
        if p >= 1:
            return f"${p:,.4f}"
        if p >= 0.01:
            return f"${p:.6f}"
        return f"${p:.10f}"

    def fmt_big(num: float) -> str:
        if num >= 1e12: return f"${num/1e12:.2f}T"
        if num >= 1e9:  return f"${num/1e9:.2f}B"
        if num >= 1e6:  return f"${num/1e6:.2f}M"
        if num >= 1e3:  return f"${num/1e3:.2f}K"
        return f"${num:.2f}"

    return f"""
🦎 *CoinGecko* — *{name}* ({symbol})
ID: `{coin_id}`

🔥 *ИНДЕКС ПЕРЕГРЕВА: {heat_score}/100*
{bar} — *{status}*

━━━━━━━━━━━━━━━━━━━━

💰 *Цена:* {price_str(price)}
📈 *24ч:* {_chg(chg_24h)}
📊 *7д:* {_chg(chg_7d)}
📅 *30д:* {_chg(chg_30d)}

🏆 *Ранг:* #{market_cap_rank or "N/A"}
💎 *Капитализация:* {fmt_big(market_cap)}
📊 *Объём 24ч:* {fmt_big(volume_24h)}

━━━━━━━━━━━━━━━━━━━━

🔍 *Сигналы:*
{reasons_text}

━━━━━━━━━━━━━━━━━━━━

💡 *Вердикт:*
_{recommendation}_
""".strip()


async def chart_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    try:
        await q.answer("📊 Загружаю график...")
    except BadRequest:
        pass

    parts = q.data.split(":")
    if len(parts) < 3:
        return

    period = parts[1]
    coin_id = parts[2]
    days = 7 if period == "7d" else 30

    price_history = await coingecko.get_price_history(coin_id, days=days)
    if not price_history:
        await q.message.reply_text("❌ Нет данных для графика.")
        return

    last = context.user_data.get("last_analysis", {})
    score = last.get("heat_score", 50)
    symbol = (last.get("coin_symbol") or coin_id).upper()

    chart_buf = create_hype_chart(price_history, {}, symbol, score)
    photo = _as_input_file(chart_buf, "chart.png")
    if photo is None:
        await q.message.reply_text("❌ График не удалось построить (пустой файл).")
        return

    # edit_media иногда падает, поэтому fallback на новое сообщение
    try:
        await q.message.edit_media(
            media=InputMediaPhoto(
                media=photo,
                caption=f"📊 *{symbol}* — {days} дней\n🔥 Индекс перегрева: *{score}/100*",
                parse_mode="Markdown"
            ),
            reply_markup=q.message.reply_markup
        )
    except BadRequest:
        await q.message.reply_photo(
            photo=photo,
            caption=f"📊 *{symbol}* — {days} дней\n🔥 Индекс перегрева: *{score}/100*",
            parse_mode="Markdown"
        )


async def prediction_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    try:
        await q.answer()
    except BadRequest:
        pass

    parts = q.data.split(":")
    action = parts[1]
    coin_id = parts[2] if len(parts) > 2 else None

    if action == "make":
        await q.message.reply_text(
            "🎯 *Ваш прогноз на 24 часа?*",
            parse_mode="Markdown",
            reply_markup=prediction_keyboard(coin_id)
        )
    elif action in ["pump", "dump", "stable"]:
        last = context.user_data.get("last_analysis", {})
        txt = {"pump": "РОСТ", "dump": "ПАДЕНИЕ", "stable": "СТАБИЛЬНО"}
        await q.message.reply_text(
            f"✅ Прогноз принят: *{txt[action]}* для *{(last.get('coin_symbol') or '').upper()}*",
            parse_mode="Markdown",
            reply_markup=back_to_menu_keyboard()
        )


def register_analyze_handlers(app):
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, analyze_coin_text))
    app.add_handler(CallbackQueryHandler(analyze_refresh_callback, pattern=r"^analyze:refresh:"))
    app.add_handler(CallbackQueryHandler(chart_callback, pattern=r"^chart:"))
    app.add_handler(CallbackQueryHandler(prediction_callback, pattern=r"^predict:"))

    # новый алерт flow
    app.add_handler(CallbackQueryHandler(alert_setup_callback, pattern=r"^alert:setup:"))
    app.add_handler(CallbackQueryHandler(alert_set_callback, pattern=r"^alert:set:"))