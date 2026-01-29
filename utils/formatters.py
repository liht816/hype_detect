"""
Форматирование текста и сообщений
"""
from datetime import datetime
from typing import Optional
from config import ACHIEVEMENTS


def format_price(price: float) -> str:
    """Форматирование цены"""
    if price >= 1:
        return f"${price:,.2f}"
    elif price >= 0.01:
        return f"${price:.4f}"
    else:
        return f"${price:.8f}"


def format_change(change: float) -> str:
    """Форматирование изменения с эмодзи"""
    if change > 0:
        return f"🟢 +{change:.2f}%"
    elif change < 0:
        return f"🔴 {change:.2f}%"
    else:
        return f"⚪ {change:.2f}%"


def format_large_number(num: float) -> str:
    """Форматирование больших чисел"""
    if num >= 1_000_000_000:
        return f"${num / 1_000_000_000:.2f}B"
    elif num >= 1_000_000:
        return f"${num / 1_000_000:.2f}M"
    elif num >= 1_000:
        return f"${num / 1_000:.2f}K"
    else:
        return f"${num:.2f}"


def format_hype_score(score: int) -> str:
    """Форматирование хайп-скора с визуализацией"""
    if score >= 80:
        emoji = "💀"
        bar = "🔴" * 5
        status = "DANGER"
    elif score >= 60:
        emoji = "🔴"
        bar = "🔴" * 4 + "⚪"
        status = "EXTREME"
    elif score >= 40:
        emoji = "🟠"
        bar = "🟠" * 3 + "⚪" * 2
        status = "HIGH"
    elif score >= 20:
        emoji = "🟡"
        bar = "🟡" * 2 + "⚪" * 3
        status = "MODERATE"
    else:
        emoji = "🟢"
        bar = "🟢" + "⚪" * 4
        status = "ORGANIC"
    
    return f"{emoji} {bar} {score}/100 ({status})"


def format_hype_level(score: int) -> tuple[str, str]:
    """Возвращает название и описание уровня хайпа"""
    levels = {
        (0, 20): ("🟢 Органический рост", "Нет признаков искусственного хайпа"),
        (20, 40): ("🟡 Умеренный хайп", "Интерес растёт, но в пределах нормы"),
        (40, 60): ("🟠 Высокий хайп", "Повышенное внимание, будь осторожен"),
        (60, 80): ("🔴 Экстремальный", "Явные признаки пампа, высокий риск"),
        (80, 101): ("💀 DANGER ZONE", "Возможная P&D схема, не входить!"),
    }
    
    for (low, high), (name, desc) in levels.items():
        if low <= score < high:
            return name, desc
    
    return "❓ Неизвестно", "Недостаточно данных"


def format_analysis_result(
    coin_name: str,
    coin_symbol: str,
    hype_score: int,
    price: float,
    price_change_24h: float,
    price_change_7d: float,
    market_cap_rank: Optional[int],
    mention_velocity: float,
    sentiment_ratio: float,
    reasons: list[str],
    recommendation: str
) -> str:
    """Форматирование полного результата анализа"""
    
    level_name, level_desc = format_hype_level(hype_score)
    
    text = f"""
*{coin_name}* ({coin_symbol.upper()})

{format_hype_score(hype_score)}
_{level_desc}_

━━━━━━━━━━━━━━━━━━━━

💰 *Цена:* {format_price(price)}
📈 *24ч:* {format_change(price_change_24h)}
📊 *7д:* {format_change(price_change_7d)}
🏆 *Ранг:* #{market_cap_rank or 'N/A'}

━━━━━━━━━━━━━━━━━━━━

📱 *Социальные сигналы (7д):*
├ 💬 Reddit: {reddit_mentions} упоминаний
├ 🐦 Twitter: {twitter_mentions} упоминаний
├ 📈 Рост активности: {mention_velocity:+.0f}%
└ 😊 Позитив: {sentiment_ratio*100:.0f}%

━━━━━━━━━━━━━━━━━━━━

🔍 *Почему такой скор:*
{chr(10).join('• ' + r for r in reasons)}

━━━━━━━━━━━━━━━━━━━━

💡 *Вердикт:*
{recommendation}
"""
    return text


def format_watchlist_item(item, current_price: float = None, current_hype: int = None) -> str:
    """Форматирование элемента watchlist"""
    text = f"*{item.coin_symbol.upper()}* — {item.coin_name}\n"
    
    if current_price and item.added_price:
        change = ((current_price - item.added_price) / item.added_price) * 100
        text += f"Цена: {format_price(current_price)} ({format_change(change)} с добавления)\n"
    
    if current_hype is not None:
        text += f"Хайп: {format_hype_score(current_hype)}\n"
        if item.added_hype_score:
            hype_change = current_hype - item.added_hype_score
            text += f"Изменение хайпа: {hype_change:+d}\n"
    
    added_date = item.added_at.strftime("%d.%m.%Y")
    text += f"Добавлено: {added_date}"
    
    return text


def format_alert(alert) -> str:
    """Форматирование алерта"""
    type_names = {
        "hype_spike": "📊 Скачок хайпа",
        "price_change": "💰 Изменение цены",
        "whale_move": "🐋 Движение кита",
        "trending": "🔥 Вход в тренды",
    }
    
    status = "🟢 Активен" if alert.is_active else "🔴 Неактивен"
    type_name = type_names.get(alert.alert_type, alert.alert_type)
    coin = alert.coin_symbol.upper() if alert.coin_symbol else "Все монеты"
    
    text = f"""
*{type_name}*
Монета: {coin}
Статус: {status}
Сработал: {alert.triggered_count} раз
"""
    
    if alert.condition:
        text += f"Условие: {alert.condition}\n"
    
    if alert.last_triggered:
        text += f"Последний раз: {alert.last_triggered.strftime('%d.%m %H:%M')}"
    
    return text


def format_whale_transaction(tx: dict) -> str:
    """Форматирование транзакции кита"""
    amount = format_large_number(tx.get("amount_usd", 0))
    symbol = tx.get("symbol", "???").upper()
    tx_type = "📥 Покупка" if tx.get("type") == "buy" else "📤 Продажа"
    
    return f"{tx_type} {amount} {symbol}"


def format_fear_greed(value: int, classification: str) -> str:
    """Форматирование индекса страха и жадности"""
    emoji_map = {
        "Extreme Fear": "😱",
        "Fear": "😰",
        "Neutral": "😐",
        "Greed": "🤑",
        "Extreme Greed": "🤯",
    }
    emoji = emoji_map.get(classification, "❓")
    
    # Визуальная шкала
    position = value // 10
    bar = "⬜" * position + "🔘" + "⬜" * (10 - position - 1)
    
    return f"""
{emoji} *{classification}*

{bar}
*{value}/100*

😱 Страх ←───────→ Жадность 🤑
"""


def format_profile(user, achievements: list) -> str:
    """Форматирование профиля пользователя"""
    level_names = {
        1: "🥉 Новичок",
        2: "🥈 Любитель",
        3: "🥇 Трейдер",
        4: "💎 Эксперт",
        5: "👑 Мастер",
        6: "🔮 Гуру",
        7: "⭐ Легенда",
        8: "🌟 Титан",
        9: "💫 Бог трейдинга",
        10: "🏆 Топ-1",
    }
    
    level_name = level_names.get(user.level, f"Уровень {user.level}")
    
    text = f"""
👤 *Твой профиль*

{level_name}
⭐ Очки: {user.points}
📊 Анализов: {user.analyses_count}
🔥 Streak: {user.streak_days} дней

━━━━━━━━━━━━━━━━━━━━

🏆 *Достижения ({len(achievements)}/{len(ACHIEVEMENTS)}):*
"""
    
    for ach_id in achievements:
        if ach_id in ACHIEVEMENTS:
            text += f"• {ACHIEVEMENTS[ach_id]['name']}\n"
    
    if not achievements:
        text += "_Пока нет достижений_\n"
    
    return text


def format_leaderboard(users: list) -> str:
    """Форматирование лидерборда"""
    medals = ["🥇", "🥈", "🥉"]
    
    text = "🏆 *Топ трейдеров*\n\n"
    
    for i, user in enumerate(users):
        medal = medals[i] if i < 3 else f"{i+1}."
        name = user.username or user.first_name or f"User{user.telegram_id}"
        text += f"{medal} *{name}* — {user.points} очков\n"
    
    return text


def format_portfolio_summary(items: list, prices: dict) -> str:
    """Форматирование сводки портфолио"""
    total_invested = 0
    total_current = 0
    
    text = "💼 *Твой портфолио*\n\n"
    
    for item in items:
        invested = item.amount * item.buy_price
        current_price = prices.get(item.coin_id, item.buy_price)
        current_value = item.amount * current_price
        pnl = current_value - invested
        pnl_percent = (pnl / invested * 100) if invested > 0 else 0
        
        total_invested += invested
        total_current += current_value
        
        emoji = "🟢" if pnl >= 0 else "🔴"
        text += f"{emoji} *{item.coin_symbol.upper()}*\n"
        text += f"   {item.amount:.4f} × {format_price(current_price)}\n"
        text += f"   P&L: {format_change(pnl_percent)}\n\n"
    
    total_pnl = total_current - total_invested
    total_pnl_percent = (total_pnl / total_invested * 100) if total_invested > 0 else 0
    
    text += "━━━━━━━━━━━━━━━━━━━━\n"
    text += f"💰 *Вложено:* {format_large_number(total_invested)}\n"
    text += f"📊 *Текущая стоимость:* {format_large_number(total_current)}\n"
    text += f"📈 *Общий P&L:* {format_change(total_pnl_percent)}\n"
    
    return text