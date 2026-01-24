import asyncio
import aiosqlite
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

import handlers

async def main() -> None:
    # Read bot token
    with open("bot_token.txt", "r") as f:
        TOKEN = f.read().strip()


    # Initialize the dispatcher and attach our router to it
    dp = Dispatcher()
    dp.include_routers(handlers.router)

    # Ensure the database exists
    async with aiosqlite.connect("users.sqlite") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS Users (
                chat_id INTEGER PRIMARY KEY,
                username TEXT,
                lat REAL,
                lon REAL
            )
        """)
        await db.commit() 

    # Initialize the bot and start polling
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())