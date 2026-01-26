import aiosqlite
import aiohttp

import timezonefinder
import zoneinfo

import json
import datetime

from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

# To be attached to the dispatcher
router = Router()


@router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await message.answer("Hello! This bot can fetch sunset/sunrise quality predictions from " \
        "sunsethue.com for your location. Send a location to begin, no need for an exact one" \
        "as the API's resolution is 0.5x0.5 degrees as of now. You can just send a location at " \
        "any time to update it.")


@router.message(F.location)
async def handle_location(message: Message):
    lat = message.location.latitude
    lon = message.location.longitude
    chat_id = message.from_user.id
    username = message.from_user.username

    # Latitudes not in this range aren't supported by sunsethue
    if not (-55 <= lat <= 70):
        message.answer("Sunsethue only supports latitudes between -55 and 70. Sorry.")
        return


    # Save to database using UPSERT
    async with aiosqlite.connect("users.sqlite") as db:
        await db.execute("""
            INSERT INTO Users (chat_id, username, lat, lon) 
            VALUES (?, ?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                username = excluded.username,
                lat = excluded.lat,
                lon = excluded.lon
        """, (chat_id, username, lat, lon))
        await db.commit()

    await message.answer(f"Saved! Location: {lat}, {lon}. You can now use /sunset and /sunrise. " \
        "Update anytime by dropping another pin.")


@router.message(Command("sunset"))
async def sunset(message: Message):
    # Get the user's latitude/longitude.
    async with aiosqlite.connect("users.sqlite") as db:
        chat_id = message.chat.id
        cursor = await db.execute(f"SELECT lat, lon FROM Users WHERE chat_id = ?", (chat_id, )) 
        coordinates = await cursor.fetchone()
    
    if not coordinates:
        await message.answer("It seems you haven't registered yet. Register using the /start command.")

    # Round to 2 decimal places as the API doesn't offer more precision
    lat = round(coordinates[0], 2)
    lon = round(coordinates[1], 2)

    user_timezone_name = timezonefinder.timezone_at(lat=lat, lng=lon)
    user_datetime = datetime.datetime.now(zoneinfo.ZoneInfo(user_timezone_name))

    utc_datetime = user_datetime.astimezone(zoneinfo.ZoneInfo("UTC"))
    utc_date = utc_datetime.date()
    
    with open("api_key.txt", "r") as f:
        API_KEY = f.read()

    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.sunsethue.com/event?key={API_KEY}&latitude={lat}&longitude={lon}&date={utc_date}&type=sunset") as response:
            await message.answer(str(response.status))
            data = await response.json()
            await message.answer(json.dumps(data, indent=2))

