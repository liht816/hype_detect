"""
🔥 Детектор Хайпа — Главный файл бота
"""
import logging
from telegram import Update
from telegram.ext import Application, ContextTypes
from keep_alive import keep_alive  # <--- Добавить импорт

from config import BOT_TOKEN
from database.connection import init_db
from handlers import register_all_handlers
from jobs import start_scheduler, stop_scheduler

# ====== ЛОГИРОВАНИЕ ======
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


async def post_init(application: Application):
    """Инициализация после запуска"""
    logger.info("🔧 Initializing database...")
    await init_db()
    
    logger.info("⏰ Starting scheduler...")
    await start_scheduler(application.bot)
    
    logger.info("✅ Bot initialized successfully!")


async def post_shutdown(application: Application):
    """Очистка при выключении"""
    logger.info("🛑 Shutting down scheduler...")
    await stop_scheduler()
    
    logger.info("👋 Bot shutdown complete")

from telegram.error import BadRequest

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    err = context.error
    if isinstance(err, BadRequest):
        msg = str(err)
        if "Query is too old" in msg:
            return
        if "Message is not modified" in msg:
            return
        if "There is no text in the message to edit" in msg:
            return
    logger.error(f"Error: {err}")


def main():
    """Запуск бота"""
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN not found in environment!")
        return
    
    logger.info("🚀 Starting Hype Detector Bot...")
    
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )
    
    register_all_handlers(application)
    application.add_error_handler(error_handler)
    
    logger.info("🔥 Bot is running!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
    keep_alive()
