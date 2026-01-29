"""
Обработчики Red Flags
"""
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler

from services import CoinGeckoService
from core import RedFlagsDetector
from utils.keyboards import redflag_keyboard, back_to_menu_keyboard

coingecko = CoinGeckoService()
detector = RedFlagsDetector()


async def redflag_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню Red Flags"""
    query = update.callback_query
    await query.answer()
    
    # Сбрасываем флаг
    context.user_data["awaiting_redflag_input"] = False
    
    await query.edit_message_text(
        "🚨 *Red Flags Детектор*\n\n"
        "Проверь монету на признаки скама!\n\n"
        "*Что проверяется:*\n"
        "• 📛 Подозрительное название\n"
        "• 📊 Рыночные аномалии\n"
        "• 👥 Социальные сигналы\n"
        "• 👨‍💻 Активность разработки\n"
        "• 📜 Контракт и аудит\n\n"
        "_Выбери действие:_",
        parse_mode="Markdown",
        reply_markup=redflag_keyboard()
    )


async def redflag_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Действия Red Flags"""
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split(":")
    action = parts[1]
    
    if action == "search":
        context.user_data["awaiting_redflag_input"] = True
        
        await query.edit_message_text(
            "🔍 *Проверка на скам*\n\n"
            "Напиши название или тикер монеты:\n\n"
            "Примеры:\n"
            "• `bitcoin` или `btc`\n"
            "• `ethereum` или `eth`\n"
            "• `pepe`",
            parse_mode="Markdown",
            reply_markup=back_to_menu_keyboard()
        )
    
    elif action == "check" and len(parts) > 2:
        coin_id = parts[2]
        await perform_redflag_check(query.message, context, coin_id)
    
    elif action == "info":
        await query.edit_message_text(
            "📚 *Что такое Red Flags?*\n\n"
            "*Red Flags* — тревожные признаки скама.\n\n"
            "*💀 Критические:*\n"
            "• Неверифицированный контракт\n"
            "• Анонимная команда + хайп\n"
            "• Honeypot (нельзя продать)\n\n"
            "*🔴 Высокий риск:*\n"
            "• Нет сайта или GitHub\n"
            "• Микро-капитализация (<$100k)\n"
            "• Экстремальный хайп без причины\n\n"
            "*🟠 Средний риск:*\n"
            "• Мало подписчиков\n"
            "• Подозрительное название\n"
            "• Нет активности разработки\n\n"
            "_Всегда проверяй перед инвестицией!_",
            parse_mode="Markdown",
            reply_markup=redflag_keyboard()
        )


async def perform_redflag_check(message, context, query_text: str):
    """Выполнение проверки на Red Flags"""
    
    status_msg = await message.reply_text(
        f"🔍 Ищу *{query_text}*...",
        parse_mode="Markdown"
    )
    
    # Ищем монету
    coin = await coingecko.search_coin(query_text)
    
    if not coin:
        await status_msg.edit_text(
            f"😕 Монета *{query_text}* не найдена.\n\n"
            "Попробуй:\n"
            "• Полное название (bitcoin)\n"
            "• Тикер (btc, eth)",
            parse_mode="Markdown",
            reply_markup=redflag_keyboard()
        )
        return
    
    coin_id = coin["id"]
    coin_name = coin["name"]
    coin_symbol = coin["symbol"]
    
    await status_msg.edit_text(
        f"🚨 Проверяю *{coin_name}* на Red Flags...",
        parse_mode="Markdown"
    )
    
    # Получаем данные
    coin_data = await coingecko.get_coin_data(coin_id)
    
    if not coin_data:
        await status_msg.edit_text(
            "😕 Не удалось получить данные. Попробуй позже.",
            reply_markup=redflag_keyboard()
        )
        return
    
    # Извлекаем метрики
    market_data = coin_data.get("market_data", {})
    market_cap = market_data.get("market_cap", {}).get("usd", 0)
    market_cap_rank = coin_data.get("market_cap_rank")
    volume = market_data.get("total_volume", {}).get("usd", 0)
    price_change_24h = market_data.get("price_change_percentage_24h") or 0
    price_change_7d = market_data.get("price_change_percentage_7d") or 0
    
    # Социальные данные
    community = coin_data.get("community_data", {})
    twitter_followers = community.get("twitter_followers") or 0
    reddit_subscribers = community.get("reddit_subscribers") or 0
    
    # Ссылки
    links = coin_data.get("links", {})
    homepage = links.get("homepage", [])
    website = homepage[0] if homepage and homepage[0] else None
    repos = links.get("repos_url", {})
    github_repos = repos.get("github", [])
    github_url = github_repos[0] if github_repos else None
    
    # Supply
    total_supply = market_data.get("total_supply")
    circulating_supply = market_data.get("circulating_supply")
    
    # Выполняем анализ
    result = detector.analyze(
        coin_id=coin_id,
        coin_symbol=coin_symbol,
        coin_name=coin_name,
        market_cap=market_cap,
        market_cap_rank=market_cap_rank,
        volume_24h=volume,
        price_change_24h=price_change_24h,
        price_change_7d=price_change_7d,
        website_url=website,
        github_url=github_url,
        twitter_followers=twitter_followers,
        reddit_subscribers=reddit_subscribers,
        total_supply=total_supply,
        circulating_supply=circulating_supply,
    )
    
    # Форматируем ответ
    risk_emoji = {
        "critical": "🚨🚨🚨",
        "high": "🚨",
        "medium": "⚠️",
        "low": "✅"
    }
    
    emoji = risk_emoji.get(result.risk_level, "❓")
    
    text = f"""
{emoji} *Red Flag анализ: {coin_name}* ({coin_symbol.upper()})

📊 *Risk Score: {result.risk_score}/100*
⚠️ Уровень: *{result.risk_level.upper()}*

"""
    
    # Red Flags
    if result.red_flags:
        text += "🚩 *Обнаружены Red Flags:*\n"
        for rf in result.red_flags[:5]:
            severity_icon = {
                1: "🟡",  # LOW
                2: "🟠",  # MEDIUM
                3: "🔴",  # HIGH
                4: "💀",  # CRITICAL
            }
            icon = severity_icon.get(rf.severity.value, "⚪")
            text += f"{icon} {rf.name}\n"
        text += "\n"
    else:
        text += "✅ *Red Flags не обнаружены*\n\n"
    
    # Green Flags
    if result.green_flags:
        text += "✅ *Позитивные сигналы:*\n"
        for gf in result.green_flags[:3]:
            text += f"• {gf}\n"
        text += "\n"
    
    # Рекомендация
    text += f"💡 *Вердикт:*\n{result.recommendation}"
    
    await status_msg.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=redflag_keyboard()
    )


async def handle_redflag_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстового ввода для Red Flags"""
    if not context.user_data.get("awaiting_redflag_input"):
        return False
    
    context.user_data["awaiting_redflag_input"] = False
    
    query_text = update.message.text.strip().lower()
    await perform_redflag_check(update.message, context, query_text)
    
    return True


def register_redflag_handlers(app):
    """Регистрация обработчиков"""
    app.add_handler(CallbackQueryHandler(
        redflag_menu_callback,
        pattern=r"^menu:redflag$"
    ))
    app.add_handler(CallbackQueryHandler(
        redflag_action_callback,
        pattern=r"^redflag:"
    ))