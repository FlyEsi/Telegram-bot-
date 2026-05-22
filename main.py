import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from app.database.core import init_db, close_db
from app.services.redis_service import redis_manager
from app.config import settings
from app.handlers import user_handlers

# Настроить логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Главная функция бота"""
    
    logger.info("=" * 50)
    logger.info("🤖 Запуск Telegram бота...")
    logger.info("=" * 50)
    
    # Инициализировать БД
    await init_db()
    
    # Подключиться к Redis
    await redis_manager.connect()
    
    # Создать бота и диспетчер
    bot = Bot(
        token=settings.BOT_TOKEN,
        default={"parse_mode": ParseMode.HTML}
    )
    dp = Dispatcher()
    
    # Подключить обработчики
    dp.include_router(user_handlers.user_router)
    
    try:
        logger.info("✅ Бот начинает опрашивать сервер...")
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("⏹️ Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"❌ Ошибка в боте: {e}")
    finally:
        await bot.session.close()
        await close_db()
        await redis_manager.disconnect()
        logger.info("✅ Бот корректно завершил работу")


if __name__ == "__main__":
    asyncio.run(main())
