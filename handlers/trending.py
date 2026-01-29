"""
Обработчики трендовых монет
"""
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler

from services import CoinGeckoService
from utils.keyboards import trending_keyboard, back_to_menu_keyboard

coingecko = CoinGeckoService()


async def trending_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню трендов"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "🔥 *Загружаю тренды...*",
        parse_mode="Markdown"
    )
    
    trending = await coingecko.get_trending()
    
    if not trending:
        await query.edit_message_text(
            "😕 Не удалось получить тренды. Попробуй позже.",
            reply_markup=back_to_menu_keyboard()
        )
        return
    
    text = """🔥 *Трендовые монеты (CoinGecko)*

❓ *Что это значит?*
Это монеты, которые сейчас чаще всего ищут на CoinGecko за последние 24 часа.

⚠️ *Важно понимать:*
• Тренды ≠ рекомендация к покупке
• Часто тут появляются монеты ПОСЛЕ пампа
• Высокий интерес может означать P&D схему
• Чем ниже ранг (#) — тем рискованнее

━━━━━━━━━━━━━━━━━━━━

"""
    
    for i, coin in enumerate(trending[:10], 1):
        item = coin.get("item", {})
        name = item.get("name", "?")
        symbol = item.get("symbol", "?").upper()
        rank = item.get("market_cap_rank", "N/A")
        
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")
        
        # Добавляем предупреждение для низких рангов
        if rank and isinstance(rank, int):
            if rank > 500:
                warning = " ⚠️ _высокий риск_"
            elif rank > 200:
                warning = " 👀 _осторожно_"
            elif rank > 100:
                warning = ""
            else:
                warning = " ✅"
        else:
            warning = " ❓"
        
        text += f"{medal} *{name}* ({symbol})\n"
        text += f"    Ранг: #{rank}{warning}\n\n"
    
    text += """━━━━━━━━━━━━━━━━━━━━

💡 *Как использовать:*
1. Напиши название монеты для полного анализа
2. Проверь хайп-скор
3. Посмотри Red Flags

🎯 _Правило: если все говорят про монету — возможно, уже поздно!_"""
    
    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=trending_keyboard()
    )


async def trending_source_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Переключение источников трендов"""
    query = update.callback_query
    await query.answer("🔄 Обновляю...")
    
    source = query.data.split(":")[1]
    
    if source in ["coingecko", "refresh"]:
        await trending_menu_callback(update, context)
    
    elif source == "reddit":
        await query.edit_message_text(
            """💬 *Тренды Reddit*

❓ *Что это?*
Монеты, которые чаще всего упоминаются в крипто-сабреддитах.

⚠️ *Внимание:*
Для работы этой функции нужен Reddit API.
Сейчас показаны примерные данные.

━━━━━━━━━━━━━━━━━━━━

*Топ обсуждаемых:*

1. 🔥 *BTC* — Bitcoin
   _Всегда в топе обсуждений_

2. 🔥 *ETH* — Ethereum
   _Второй по популярности_

3. 🔥 *SOL* — Solana
   _Активное комьюнити_

4. 👀 *PEPE* — Pepe
   _Мем-коин, осторожно!_

5. 👀 *DOGE* — Dogecoin
   _Классический мем-коин_

━━━━━━━━━━━━━━━━━━━━

💡 _Для реальных данных настрой Reddit API в .env_""",
            parse_mode="Markdown",
            reply_markup=trending_keyboard()
        )
    
    elif source == "twitter":
        await query.edit_message_text(
            """🐦 *Тренды Twitter/X*

❓ *Что это?*
Монеты с наибольшим количеством упоминаний в крипто-Twitter.

⚠️ *Важно:*
• Twitter API теперь платный ($100/мес)
• Много ботов и накруток
• Инфлюенсеры часто шиллят за деньги

━━━━━━━━━━━━━━━━━━━━

*Примерные тренды:*

1. 🔥 *$BTC* — ~50,000 твитов/день
2. 🔥 *$ETH* — ~35,000 твитов/день
3. 🔥 *$SOL* — ~20,000 твитов/день
4. 👀 *$PEPE* — ~15,000 твитов/день
5. 👀 *$WIF* — ~10,000 твитов/день

━━━━━━━━━━━━━━━━━━━━

⚠️ *Правило:*
_Если монету шиллят все инфлюенсеры сразу — это 🚩 Red Flag!_""",
            parse_mode="Markdown",
            reply_markup=trending_keyboard()
        )
    
    elif source == "hype":
        await query.edit_message_text(
            """📊 *Топ по хайп-скору*

❓ *Что это?*
Монеты с самым высоким хайп-скором — признаками искусственного ажиотажа.

⚠️ *ВНИМАНИЕ:*
Высокий хайп = высокий риск P&D!

━━━━━━━━━━━━━━━━━━━━

*Как читать:*

🟢 0-20 — Органический рост, безопасно
🟡 20-40 — Умеренный интерес
🟠 40-60 — Повышенное внимание
🔴 60-80 — Явный хайп, ОСТОРОЖНО!
💀 80-100 — DANGER ZONE, не входить!

━━━━━━━━━━━━━━━━━━━━

*Пример опасных монет:*

💀 *SCAMCOIN* — 92/100
   _Все признаки P&D_

🔴 *HYPEMEME* — 78/100
   _Агрессивный шиллинг_

🔴 *MOON100X* — 71/100
   _Подозрительное название_

━━━━━━━━━━━━━━━━━━━━

💡 *Совет:*
_Проанализируй интересующую монету — напиши её название!_""",
            parse_mode="Markdown",
            reply_markup=trending_keyboard()
        )


def register_trending_handlers(app):
    """Регистрация обработчиков"""
    app.add_handler(CallbackQueryHandler(
        trending_menu_callback,
        pattern=r"^menu:trending$"
    ))
    app.add_handler(CallbackQueryHandler(
        trending_source_callback,
        pattern=r"^trending:"
    ))