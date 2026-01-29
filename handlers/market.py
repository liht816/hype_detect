from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from services.mexc import MexcService

mexc = MexcService()

def market_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📈 Спот", callback_data="market:set:spot"),
         InlineKeyboardButton("⚡ Фьючерсы", callback_data="market:set:futures")],
        [InlineKeyboardButton("📊 Вместе", callback_data="market:set:both")],
        [InlineKeyboardButton("🔥 Топ роста", callback_data="market:top:gainers"),
         InlineKeyboardButton("📉 Топ падения", callback_data="market:top:losers")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="menu:main")],
    ])

async def market_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if "market_mode" not in context.user_data:
        context.user_data["market_mode"] = "spot"
    await q.edit_message_text(
        f"📊 *Рынок MEXC*\n\nТекущий режим: *{context.user_data['market_mode']}*\nВыбери действие:",
        parse_mode="Markdown",
        reply_markup=market_keyboard()
    )

async def market_set(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    mode = q.data.split(":")[2]
    context.user_data["market_mode"] = mode
    await q.edit_message_text(
        f"✅ Режим рынка установлен: *{mode}*\n\nТеперь смотри топы или анализируй пары (например BTCUSDT).",
        parse_mode="Markdown",
        reply_markup=market_keyboard()
    )

async def market_top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer("Сканирую MEXC...")
    kind = q.data.split(":")[2]
    mode = context.user_data.get("market_mode", "spot")

    if mode in ("spot", "both"):
        tickers = await mexc.spot_tickers_24h()
        usdt = [t for t in tickers if str(t.get("symbol","")).endswith("USDT")]
        usdt.sort(key=lambda x: float(x.get("priceChangePercent", 0)), reverse=True)
        if kind == "losers":
            usdt = list(reversed(usdt))
        top = usdt[:10]
        lines = []
        for t in top:
            sym = t["symbol"]
            chg = float(t.get("priceChangePercent", 0))
            vol = float(t.get("quoteVolume", 0))
            lines.append(f"• `{sym}`  {chg:+.2f}%  vol={vol:,.0f}")
        text = "📊 *MEXC SPOT топ*\n\n" + "\n".join(lines)
    else:
        # Futures: если API не отдаёт — будет пусто
        ft = await mexc.futures_tickers() or []
        if not ft:
            text = "⚡ *MEXC Futures*\n\nНе удалось получить данные фьючерсов (API может отличаться)."
        else:
            # предполагаем поле riseFallRate (доля), иначе fallback
            def pct(x):
                if "riseFallRate" in x:
                    return float(x["riseFallRate"]) * 100
                return float(x.get("priceChangePercent", 0))
            ft.sort(key=pct, reverse=True)
            if kind == "losers":
                ft = list(reversed(ft))
            top = ft[:10]
            lines = [f"• `{t.get('symbol')}`  {pct(t):+.2f}%" for t in top]
            text = "⚡ *MEXC FUTURES топ*\n\n" + "\n".join(lines)

    await q.edit_message_text(text, parse_mode="Markdown", reply_markup=market_keyboard())

def register_market_handlers(app):
    app.add_handler(CallbackQueryHandler(market_menu, pattern=r"^menu:market$"))
    app.add_handler(CallbackQueryHandler(market_set, pattern=r"^market:set:"))
    app.add_handler(CallbackQueryHandler(market_top, pattern=r"^market:top:"))