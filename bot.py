import asyncio
import aiosqlite
import logging
import sys
import aiohttp

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

import handlers

async def setup_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Display welcome message, ask to send location"),
        BotCommand(command="sunset", description="Sunset forecast"),
        BotCommand(command="sunrise", description="Sunrise forecast"),
        BotCommand(command="help", description="Display help message")
    ]

    await bot.set_my_commands(commands)


async def main() -> None:
    # Read bot token
    with open("bot_token.txt", "r") as f:
        BOT_TOKEN = f.read().strip()
    
    # Read API key
    with open("api_key.txt", "r") as f:
        API_KEY = f.read()

    # Ensure the database exists
    async with aiosqlite.connect("users.sqlite") as db:
        async with aiohttp.ClientSession() as session:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS Users (
                    chat_id INTEGER PRIMARY KEY,
                    username TEXT,
                    lat REAL NOT NULL CHECK (lat >= -55.0 AND lat <= 70.0),
                    lon REAL NOT NULL CHECK (lon >= -180.0 AND lon <= 180.0)
                )
            """)
            await db.commit()

            # Database and aiohttp connection middleware. We will pass it to all handlers
            async def dependencies_middleware(handler, event, data):
                data["db"] = db
                data["session"] = session
                return await handler(event, data)
            
            # Initialize the dispatcher and attach our router to it. We only pass the API key 
            # into the dispatcher as we don't need the bot token after we initialize the bot
            dp = Dispatcher(API_KEY=API_KEY)
            dp.include_routers(handlers.router)

            # Register middleware
            dp.update.outer_middleware.register(dependencies_middleware)

            # Initialize the bot and start polling
            bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

            dp.startup.register(setup_bot_commands)
            await dp.start_polling(bot, skip_updates=True, on_startup=setup_bot_commands)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
