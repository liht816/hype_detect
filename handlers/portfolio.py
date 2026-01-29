"""
Обработчики портфолио
"""
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler

from utils.keyboards import portfolio_keyboard, back_to_menu_keyboard


async def portfolio_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню портфолио"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "💼 *Твоё портфолио*\n\n"
        "Отслеживай свои позиции!\n\n"
        "📊 _Портфолио пока пусто_\n\n"
        "Добавь свою первую позицию!",
        parse_mode="Markdown",
        reply_markup=portfolio_keyboard(has_items=False)
    )


async def portfolio_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Действия портфолио"""
    query = update.callback_query
    await query.answer()
    
    action = query.data.split(":")[1]
    
    if action == "add":
        await query.edit_message_text(
            "➕ *Добавить позицию*\n\n"
            "Напиши данные в формате:\n"
            "`монета количество цена`\n\n"
            "Пример:\n"
            "`btc 0.5 45000`",
            parse_mode="Markdown",
            reply_markup=back_to_menu_keyboard()
        )
        context.user_data["awaiting_portfolio_add"] = True
    
    elif action == "stats":
        await query.answer("📊 Статистика пока недоступна", show_alert=True)
    
    elif action == "refresh":
        await portfolio_menu_callback(update, context)


def register_portfolio_handlers(app):
    """Регистрация обработчиков"""
    app.add_handler(CallbackQueryHandler(
        portfolio_menu_callback,
        pattern=r"^menu:portfolio$"
    ))
    app.add_handler(CallbackQueryHandler(
        portfolio_action_callback,
        pattern=r"^portfolio:"
    ))