import asyncio
import logging
import os
import sys

import aiohttp
from aiogram import BaseMiddleware, Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, TelegramObject
from dotenv import load_dotenv

import handlers
from database import Base, async_session, engine


async def setup_bot_commands(bot: Bot):
    commands = [
        BotCommand(
            command="start", description="Display welcome message, ask to send location"
        ),
        BotCommand(command="sunset", description="Sunset forecast"),
        BotCommand(command="sunrise", description="Sunrise forecast"),
        BotCommand(command="help", description="Display help message"),
    ]

    await bot.set_my_commands(commands)


class DatabaseMiddleware(BaseMiddleware):
    def __init__(self, http_session: aiohttp.ClientSession):
        super().__init__()
        self.http_session = http_session

    async def __call__(self, handler, event: TelegramObject, data: dict):
        async with async_session() as db_session:
            data["db"] = db_session
            data["session"] = self.http_session
            return await handler(event, data)


async def main() -> None:
    load_dotenv()

    BOT_TOKEN = os.getenv("BOT_TOKEN")
    API_KEY = os.getenv("API_KEY")
    if not BOT_TOKEN or not API_KEY:
        logging.error(
            "Couldn't get the required environment variables. Please set BOT_TOKEN and API_KEY in the .env file."
        )
        return

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with aiohttp.ClientSession() as http_session:
        dp = Dispatcher(API_KEY=API_KEY)
        dp.include_routers(handlers.router)
        dp.update.outer_middleware.register(DatabaseMiddleware(http_session))

        bot = Bot(
            token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )

        dp.startup.register(setup_bot_commands)
        await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
