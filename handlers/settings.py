"""
Обработчики настроек
"""
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler

from utils.keyboards import settings_keyboard, back_to_menu_keyboard
from database.connection import async_session
from database.repositories import UserRepository


async def settings_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню настроек"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    
    async with async_session() as session:
        user_repo = UserRepository(session)
        db_user = await user_repo.get_by_telegram_id(user.id)
        
        if not db_user:
            db_user = await user_repo.get_or_create(
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name
            )
    
    notif = "🔔 Вкл" if db_user.notifications_enabled else "🔕 Выкл"
    
    text = f"""
⚙️ *Настройки*

📬 *Уведомления:* {notif}
📊 *Порог хайпа:* {db_user.alert_threshold}+
🌍 *Язык:* Русский

👤 *Аккаунт:*
ID: `{db_user.telegram_id}`
С нами с: {db_user.created_at.strftime('%d.%m.%Y')}
"""
    
    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=settings_keyboard(db_user)
    )


async def settings_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Действия настроек"""
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split(":")
    action = parts[1]
    
    user = query.from_user
    
    async with async_session() as session:
        user_repo = UserRepository(session)
        db_user = await user_repo.get_by_telegram_id(user.id)
        
        if not db_user:
            db_user = await user_repo.get_or_create(
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name
            )
        
        if action == "toggle_notifications":
            db_user.notifications_enabled = not db_user.notifications_enabled
            await session.commit()
            
            status = "включены 🔔" if db_user.notifications_enabled else "выключены 🔕"
            await query.answer(f"Уведомления {status}", show_alert=True)
            
            await settings_menu_callback(update, context)
        
        elif action == "threshold":
            if len(parts) > 2:
                threshold = int(parts[2])
                db_user.alert_threshold = threshold
                await session.commit()
                
                await query.answer(f"Порог: {threshold}+", show_alert=True)
                await settings_menu_callback(update, context)
            else:
                await query.edit_message_text(
                    "📊 *Порог хайпа для алертов*\n\n"
                    "Выбери минимальный хайп-скор:\n\n"
                    "• *40+* — много уведомлений\n"
                    "• *60+* — средне\n"
                    "• *80+* — только критичные",
                    parse_mode="Markdown",
                    reply_markup=back_to_menu_keyboard()
                )
        
        elif action == "language":
            await query.answer("Пока только русский 🇷🇺", show_alert=True)
        
        elif action == "quiet_hours":
            await query.answer("Тихие часы: 23:00 - 08:00", show_alert=True)
        
        elif action == "delete_data":
            await query.edit_message_text(
                "🗑️ *Удаление данных*\n\n"
                "Это удалит все твои данные:\n"
                "• История анализов\n"
                "• Watchlist\n"
                "• Алерты\n"
                "• Достижения\n\n"
                "⚠️ _Функция временно отключена_",
                parse_mode="Markdown",
                reply_markup=back_to_menu_keyboard()
            )


def register_settings_handlers(app):
    """Регистрация обработчиков"""
    app.add_handler(CallbackQueryHandler(
        settings_menu_callback,
        pattern=r"^menu:settings$"
    ))
    app.add_handler(CallbackQueryHandler(
        settings_action_callback,
        pattern=r"^settings:"
    ))