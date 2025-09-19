from aiogram import Bot, Dispatcher
import logging
import asyncio
from handlers import router, AccessControlMiddleware, add_legendary_skins
from config import config
import db
import cheker
import os
from datetime import datetime

# logger = logging.getLogger(__name__)

bot = Bot(token=config["TOKEN_BOT"])  # type: ignore


async def main() -> None:
    logger.info("\n\nStarting system...")
    dp = Dispatcher()
    dp.include_router(router)
    dp.message.middleware(AccessControlMiddleware())
    dp.inline_query.middleware(AccessControlMiddleware())
    dp.callback_query.middleware(AccessControlMiddleware())
    if db.init_db():
        logger.warning("Database is not initialized, adding legendary skins...")
        await add_legendary_skins()
        logger.info("[+] Database initialized successfully.")
    db.run_migrations()
    await cheker.update_data()
    if not "no_loop" in config:
        asyncio.create_task(cheker.loop(bot))
    else:
        logger.warning("no_loop is set to True, skipping the loop task.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    os.makedirs("logs", exist_ok=True)
    log_filename = datetime.now().strftime("logs/log_%Y-%m-%d.log")
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    file_handler = logging.FileHandler(log_filename, mode="a", encoding="utf-8")
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    # Root logger → тільки INFO (для бібліотек)
    logging.basicConfig(level=logging.INFO, handlers=[file_handler, stream_handler])

    # Твій логер → DEBUG
    logger = logging.getLogger("myapp")  # назва твого пакета/модуля
    logger.setLevel(logging.DEBUG)
    asyncio.run(main())
