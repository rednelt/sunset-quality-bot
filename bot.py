import asyncio
import aiosqlite
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

import handlers

async def setup_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Display welcome message, ask to send location"),
        BotCommand(command="help", description="Get help"),
        BotCommand(command="sunset", description="Return the forecast for the next sunset"),
        BotCommand(command="sunrise", description="Return the forecast for the next sunrise")
    ]

    await bot.set_my_commands(commands)


async def main() -> None:
    # Read bot token
    with open("bot_token.txt", "r") as f:
        BOT_TOKEN = f.read().strip()

    # Initialize the dispatcher and attach our router to it
    dp = Dispatcher()
    dp.include_routers(handlers.router)

    # Ensure the database exists
    async with aiosqlite.connect("users.sqlite") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS Users (
                chat_id INTEGER PRIMARY KEY,
                username TEXT,
                lat REAL NOT NULL CHECK (lat >= -55.0 AND lat <= 70.0),
                lon REAL NOT NULL CHECK (lon >= -180.0 AND lon <= 180.0)
            )
        """)
        await db.commit() 

    # Initialize the bot and start polling
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))


    dp.startup.register(setup_bot_commands)
    await dp.start_polling(bot, skip_updates=True, on_startup=setup_bot_commands)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
