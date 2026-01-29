"""
Обработчики стартового меню
"""
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from telegram.error import BadRequest

from utils.keyboards import main_menu_keyboard, back_to_menu_keyboard
from database.connection import async_session
from database.repositories import UserRepository


WELCOME_TEXT = """
🔥 *Добро пожаловать в Детектор Хайпа!*

Я помогу тебе отличить органический рост криптовалюты от искусственного пампа.

*Как пользоваться:*
Просто напиши название монеты (например: `bitcoin` или `btc`) или используй кнопки меню ниже 👇

⚠️ _Это не финансовый совет!_
"""


async def _safe_edit_or_send(query, text: str, reply_markup=None):
    """
    Безопасно пытается отредактировать сообщение.
    Если сообщение было фото/без текста — отправит новое сообщение.
    """
    try:
        await query.edit_message_text(
            text=text,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    except BadRequest as e:
        msg = str(e)
        # Частые причины:
        # - "There is no text in the message to edit" (это фото-сообщение)
        # - "Message is not modified"
        if "Message is not modified" in msg:
            return
        await query.message.reply_text(
            text=text,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    user = update.effective_user

    async with async_session() as session:
        user_repo = UserRepository(session)
        await user_repo.get_or_create(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name
        )

    await update.message.reply_text(
        WELCOME_TEXT,
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(user_id=user.id)
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    help_text = """
📚 *Справка*

*Индекс перегрева рынка (0-100):*
🟢 0-20 — спокойно  
🟡 20-40 — умеренно  
🟠 40-60 — повышенная активность  
🔴 60-80 — перегрето  
💀 80-100 — критически перегрето

*Команды:*
/start — Главное меню
"""
    await update.message.reply_text(
        help_text,
        parse_mode="Markdown",
        reply_markup=back_to_menu_keyboard()
    )


async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Возврат в главное меню"""
    query = update.callback_query
    await query.answer()

    await _safe_edit_or_send(
        query,
        WELCOME_TEXT,
        reply_markup=main_menu_keyboard(user_id=query.from_user.id)
    )


async def analyze_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню анализа"""
    query = update.callback_query
    await query.answer()

    await _safe_edit_or_send(
        query,
        "🔍 *Анализ монеты*\n\n"
        "Напиши название или тикер монеты:\n\n"
        "Примеры:\n"
        "• `bitcoin` или `btc`\n"
        "• `ethereum` или `eth`\n"
        "• `solana` или `sol`",
        reply_markup=back_to_menu_keyboard()
    )


def register_start_handlers(app):
    """Регистрация обработчиков"""
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(main_menu_callback, pattern=r"^menu:main$"))
    app.add_handler(CallbackQueryHandler(analyze_menu_callback, pattern=r"^menu:analyze$"))