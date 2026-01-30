import aiosqlite
import aiohttp

import timezonefinder
import zoneinfo

import json
import datetime

from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from format_forecast import format_forecast

# To be attached to the dispatcher
router = Router()


@router.message(CommandStart())
async def start(message: Message):
    await message.answer("Hello! This bot can fetch sunset/sunrise quality predictions from " \
        "sunsethue.com for your location, for up to 2 days into the future (accuracy not guaranteed). " \
        "Send a location to begin, no need for an exact one as the API's resolution is 0.5x0.5 degrees as " \
        "of now. You can just send a location at any time to update it.")
    
@router.message(Command("help"))
async def help(message: Message):
    await message.answer("This bot can fetch sunset or sunrise quality predictions for your location from sunsethue.com. " \
        "Just drop a location to start. Probably don't use your exact one, the API operates in 0.5x0.5deg squares (~55km) " \
        "anyway. \n\n/start - Display welcome message\n/sunrise and /sunset - send a message with buttons to select the date " \
        "(today, tomorrow, the date after tomorrow), then send a formatted forecast.\n/help - Display this message")


@router.message(F.location)
async def handle_location(message: Message):
    lat = message.location.latitude
    lon = message.location.longitude
    chat_id = message.from_user.id
    username = message.from_user.username

    # Latitudes not in this range aren't supported by sunsethue
    if not (-55 <= lat <= 70):
        await message.answer("Sunsethue only supports latitudes between -55 and 70. Sorry.")
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

class ForecastRequest(CallbackData, prefix="forecast"):
    type: str
    date: str
    lat: float
    lon: float
    timezone_name: str

@router.message(Command("sunset", "sunrise"))
async def sunset_sunrise(message: Message, bot: Bot):
    await bot.send_chat_action(message.chat.id, "typing")

    # Get the user's latitude/longitude.
    async with aiosqlite.connect("users.sqlite") as db:
        chat_id = message.chat.id
        cursor = await db.execute(f"SELECT lat, lon FROM Users WHERE chat_id = {chat_id}") 
        coordinates = await cursor.fetchone()
    
    if not coordinates:
        await message.answer("It seems you haven't registered yet. Register using the /start command.")

    # Round to 2 decimal places as the API has 0.5x0.5 degree precision anyway
    lat = round(coordinates[0], 2)
    lon = round(coordinates[1], 2)

    # Get the forecast type based on the command
    type = message.text[1:]

    # Get the local datetime based on coordinates.
    timezone_name = timezonefinder.timezone_at(lat=lat, lng=lon)
    user_datetime = datetime.datetime.now(zoneinfo.ZoneInfo(timezone_name))

    # To get the options, we shift the local datetime by 0, 1, 2 days into the future.
    kb_builder = InlineKeyboardBuilder()
    for i in range(3):
        shifted_datetime = user_datetime + datetime.timedelta(days=i)
        # debug
        print("Shifted datetime:", str(shifted_datetime.date()))
        kb_builder.add(
            InlineKeyboardButton(
                text=shifted_datetime.strftime("%a %d.%m"),
                callback_data=ForecastRequest(type=type, 
                                              date=str(shifted_datetime.date()),
                                              lat=lat,
                                              lon=lon,
                                              timezone_name=timezone_name
                                              ).pack()
            )
        )

    await message.answer(f"Select {type} time:", reply_markup=kb_builder.as_markup())
        
@router.callback_query(ForecastRequest.filter())
async def forecast(callback_query: CallbackQuery, callback_data: ForecastRequest, bot: Bot):
    await bot.send_chat_action(chat_id=callback_query.message.chat.id, action="typing")
    await callback_query.message.edit_reply_markup(None)
    await callback_query.message.edit_text("Fetching...")

    with open("api_key.txt", "r") as f:
        API_KEY = f.read()
    
    lat = callback_data.lat
    lon = callback_data.lon
    date = callback_data.date
    type = callback_data.type
    timezone_name = callback_data.timezone_name

    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(10)) as session:
            async with session.get(f"https://api.sunsethue.com/event?key={API_KEY}&latitude={lat}&longitude={lon}&date={date}&type={type}") as response:
                if response.status != 200:
                    callback_query.answer()
                    callback_query.message.answer(f"Couldn't fetch. API returned {response.status}")
                    callback_query.message.delete()
                    return None
                    
                response_json = await response.text()

    except aiohttp.ConnectionTimeoutError:
        callback_query.answer()
        callback_query.message.answer(f"API timed out.")
        callback_query.message.delete()
        return None

    # TODO: Format data instead of this

    print(json.dumps(response_json, indent=2))
    await callback_query.answer()
    await callback_query.message.answer(format_forecast(response_json, timezone_name))
    await callback_query.message.delete()
