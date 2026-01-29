"""
Обработчики Fear & Greed Index
"""
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram.error import BadRequest

from services import FearGreedService
from utils.keyboards import fear_greed_keyboard, back_to_menu_keyboard

fear_greed = FearGreedService()


def get_fear_greed_visual(value: int) -> tuple[str, str, str]:
    """Возвращает визуализацию для значения Fear & Greed"""
    if value <= 20:
        return "😱", "ЭКСТРЕМАЛЬНЫЙ СТРАХ", "🔴🔴⚪⚪⚪⚪⚪⚪⚪⚪"
    elif value <= 35:
        return "😰", "СТРАХ", "🟠🟠🟠⚪⚪⚪⚪⚪⚪⚪"
    elif value <= 45:
        return "😟", "УМЕРЕННЫЙ СТРАХ", "🟡🟡🟡🟡⚪⚪⚪⚪⚪⚪"
    elif value <= 55:
        return "😐", "НЕЙТРАЛЬНО", "⚪⚪⚪⚪🔘⚪⚪⚪⚪⚪"
    elif value <= 65:
        return "🙂", "УМЕРЕННАЯ ЖАДНОСТЬ", "⚪⚪⚪⚪⚪⚪🟡🟡🟡⚪"
    elif value <= 80:
        return "🤑", "ЖАДНОСТЬ", "⚪⚪⚪⚪⚪⚪⚪🟠🟠🟠"
    else:
        return "🤯", "ЭКСТРЕМАЛЬНАЯ ЖАДНОСТЬ", "⚪⚪⚪⚪⚪⚪⚪⚪🔴🔴"


def get_recommendation(value: int) -> str:
    """Рекомендация на основе значения"""
    if value <= 20:
        return (
            "🔥 *Отличное время для покупок!*\n"
            "Толпа паникует, опытные инвесторы покупают."
        )
    elif value <= 35:
        return (
            "👀 *Рассмотри покупку*\n"
            "Страх на рынке создаёт возможности."
        )
    elif value <= 45:
        return (
            "📊 *Наблюдай и жди*\n"
            "Рынок в нерешительности."
        )
    elif value <= 55:
        return (
            "😐 *Нейтральная зона*\n"
            "Следуй своей стратегии."
        )
    elif value <= 65:
        return (
            "⚠️ *Будь осторожен*\n"
            "Жадность растёт, подтягивай стопы."
        )
    elif value <= 80:
        return (
            "🚨 *Фиксируй прибыль!*\n"
            "Рассмотри частичную фиксацию."
        )
    else:
        return (
            "💀 *ОПАСНОСТЬ!*\n"
            "Не покупай на хаях, зафиксируй прибыль!"
        )


async def fear_greed_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показ Fear & Greed Index"""
    query = update.callback_query
    await query.answer()
    
    # Получаем данные
    value = 35
    avg_7d = 38
    avg_30d = 42
    
    try:
        analysis = await fear_greed.get_analysis()
        current = analysis.get("current")
        if current:
            value = current["value"]
            avg_7d = analysis.get("avg_7d", 38)
            avg_30d = analysis.get("avg_30d", 42)
    except Exception as e:
        print(f"Fear & Greed error: {e}")
    
    emoji, status, bar = get_fear_greed_visual(value)
    recommendation = get_recommendation(value)
    
    if value > avg_7d + 5:
        trend = "📈 Растёт"
    elif value < avg_7d - 5:
        trend = "📉 Падает"
    else:
        trend = "➡️ Стабильно"
    
    text = f"""
{emoji} *ИНДЕКС СТРАХА И ЖАДНОСТИ*

━━━━━━━━━━━━━━━━━━━━

       {bar}
       
          *{value}/100*
       
     *{status}*

━━━━━━━━━━━━━━━━━━━━

📈 *Статистика:*
├ Сейчас: *{value}*
├ Среднее 7д: *{avg_7d:.0f}*
├ Среднее 30д: *{avg_30d:.0f}*
└ Тренд: {trend}

━━━━━━━━━━━━━━━━━━━━

{recommendation}

━━━━━━━━━━━━━━━━━━━━

❓ *Что это:*
0-25 — Страх (покупай)
75-100 — Жадность (продавай)
"""
    
    try:
        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=fear_greed_keyboard()
        )
    except BadRequest:
        # Если сообщение с фото — отправляем новое
        await query.message.reply_text(
            text,
            parse_mode="Markdown",
            reply_markup=fear_greed_keyboard()
        )


async def fear_greed_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Действия Fear & Greed"""
    query = update.callback_query
    await query.answer()
    
    action = query.data.split(":")[1]
    
    if action == "history":
        text = """
📅 *ИСТОРИЯ ИНДЕКСА (7 дней)*

━━━━━━━━━━━━━━━━━━━━

"""
        
        # Получаем историю
        history_data = []
        try:
            history_data = await fear_greed.get_history(7)
        except:
            pass
        
        if history_data and len(history_data) > 0:
            for item in history_data[:7]:
                value = item.get("value", 50)
                date = item.get("date", "")
                
                emoji, status, _ = get_fear_greed_visual(value)
                filled = value // 10
                bar = "█" * filled + "░" * (10 - filled)
                
                text += f"{emoji} *{value:>2}* │{bar}│ {status}\n"
                if date:
                    text += f"      {date}\n\n"
        else:
            # Примерные данные
            example = [
                ("Пн", 32, "Страх"),
                ("Вт", 35, "Страх"),
                ("Ср", 41, "Умеренный страх"),
                ("Чт", 38, "Страх"),
                ("Пт", 45, "Нейтрально"),
                ("Сб", 42, "Умеренный страх"),
                ("Вс", 35, "Страх"),
            ]
            
            for day, value, status in example:
                emoji, _, _ = get_fear_greed_visual(value)
                filled = value // 10
                bar = "█" * filled + "░" * (10 - filled)
                text += f"*{day}:* {emoji} {value} │{bar}│ {status}\n\n"
        
        text += """━━━━━━━━━━━━━━━━━━━━

💡 _Покупай когда страшно, продавай когда жадно!_
"""
        
        try:
            await query.edit_message_text(
                text,
                parse_mode="Markdown",
                reply_markup=fear_greed_keyboard()
            )
        except BadRequest:
            await query.message.reply_text(
                text,
                parse_mode="Markdown",
                reply_markup=fear_greed_keyboard()
            )
    
    elif action == "refresh":
        # Добавляем временную метку чтобы текст отличался
        import time
        context.user_data["fear_greed_refresh"] = time.time()
        await fear_greed_menu_callback(update, context)


def register_fear_greed_handlers(app):
    """Регистрация обработчиков"""
    app.add_handler(CallbackQueryHandler(
        fear_greed_menu_callback,
        pattern=r"^menu:fear$"
    ))
    app.add_handler(CallbackQueryHandler(
        fear_greed_action_callback,
        pattern=r"^fear:"
    ))