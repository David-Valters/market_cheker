from aiogram import Bot, Dispatcher
import logging
import asyncio
from handlers import router, AccessControlMiddleware, add_legendary_skins
from config import config
import db
import cheker

logger = logging.getLogger(__name__)

bot = Bot(token=config["TOKEN_BOT"]) # type: ignore

async def main() -> None:
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
    if not config["no_loop"]:      
        await cheker.update_data()
        asyncio.create_task(cheker.loop(bot))
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler("app.log", mode="a", encoding="utf-8"),  # У файл
            logging.StreamHandler()  # У консоль
        ]
    )
    asyncio.run(main())
