"""
Обработчики сравнения
"""
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler

from utils.keyboards import compare_keyboard, back_to_menu_keyboard


async def compare_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню сравнения"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "⚖️ *Сравнение монет*\n\n"
        "Сравни несколько монет по хайпу!\n\n"
        "Сколько монет сравнить?",
        parse_mode="Markdown",
        reply_markup=compare_keyboard()
    )


async def compare_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Действия сравнения"""
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split(":")
    action = parts[1]
    
    if action == "count":
        count = parts[2] if len(parts) > 2 else "2"
        
        context.user_data["compare_count"] = int(count)
        context.user_data["compare_coins"] = []
        
        await query.edit_message_text(
            f"⚖️ *Сравнение {count} монет*\n\n"
            f"Напиши название первой монеты:",
            parse_mode="Markdown",
            reply_markup=back_to_menu_keyboard()
        )


def register_compare_handlers(app):
    """Регистрация обработчиков"""
    app.add_handler(CallbackQueryHandler(
        compare_menu_callback,
        pattern=r"^menu:compare$"
    ))
    app.add_handler(CallbackQueryHandler(
        compare_action_callback,
        pattern=r"^compare:"
    ))