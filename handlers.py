import datetime
import json
import zoneinfo

import aiohttp
import aiosqlite
import timezonefinder
from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.filters.callback_data import CallbackData
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from format_forecast import format_forecast

# To be attached to the dispatcher
router = Router()


@router.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "Hello! This bot can fetch sunset/sunrise quality predictions from sunsethue.com for your location, "
        "for up to 3 days into the future. Send a location to begin."
    )


@router.message(Command("help"))
async def help(message: Message):
    await message.answer(
        "This bot can fetch sunset or sunrise quality predictions for your location from sunsethue.com. "
        "Just drop a location to start. Probably don't use your exact one, the API operates in 0.5x0.5deg squares (~55km) "
        "anyway. The accuracy <i>will</i> deteoriate the further into the future you look, keep that in mind."
        "\n\n/start - Display welcome message\n/sunrise and /sunset - send a message with buttons to select the date "
        "(today, tomorrow, the day after tomorrow), then send a formatted forecast.\n/help - Display this message"
    )


@router.message(F.location)
async def location(message: Message, db: aiosqlite.Connection):
    lat = message.location.latitude
    lon = message.location.longitude
    chat_id = message.from_user.id
    username = message.from_user.username

    # Latitudes not in this range aren't supported by sunsethue
    if not (-55 <= lat <= 70):
        await message.answer(
            "Sunsethue only supports latitudes between -55 and 70. Sorry."
        )
        return

    timezone = timezonefinder.timezone_at(lat=lat, lng=lon)

    # Save to database using UPSERT
    await db.execute(
        """
            INSERT INTO Users (chat_id, username, lat, lon, timezone)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
            username = excluded.username,
            lat = excluded.lat,
            lon = excluded.lon,
            timezone = excluded.timezone
        """,
        (chat_id, username, lat, lon, timezone),
    )
    await db.commit()

    await message.answer(
        f"Saved! Location: {lat}, {lon}. Determined timezone {timezone}: You can now use /sunset and /sunrise. "
        "Update anytime by dropping another pin."
    )


class ForecastRequest(CallbackData, prefix="forecast"):
    type: str
    date: str
    lat: float
    lon: float
    timezone: str


@router.message(Command("sunset", "sunrise"))
async def sunset_sunrise(message: Message, bot: Bot, db: aiosqlite.Connection):
    await bot.send_chat_action(message.chat.id, "typing")

    # Get the user's latitude/longitude.
    chat_id = message.chat.id
    cursor = await db.execute(
        "SELECT lat, lon FROM Users WHERE chat_id = ?", (chat_id,)
    )
    coordinates = await cursor.fetchone()

    if not coordinates:
        await message.answer(
            "It seems you haven't registered yet. Register using the /start command."
        )

    # Round to 2 decimal places as the API has 0.5x0.5 degree precision anyway
    lat = round(coordinates[0], 2)
    lon = round(coordinates[1], 2)

    # Get the forecast type based on the command
    type = message.text[1:]

    # Get the local datetime based on coordinates.
    cursor = await db.execute(
        "SELECT timezone from Users WHERE chat_id = ?", (chat_id,)
    )
    timezone = (await cursor.fetchone())[0]
    user_datetime = datetime.datetime.now(zoneinfo.ZoneInfo(timezone))

    # To get the options, we shift the local datetime by 0, 1, 2 days into the future.
    kb_builder = InlineKeyboardBuilder()
    for i in range(3):
        shifted_datetime = user_datetime + datetime.timedelta(days=i)
        kb_builder.add(
            InlineKeyboardButton(
                text=shifted_datetime.strftime("%a %d.%m"),
                callback_data=ForecastRequest(
                    type=type,
                    date=str(shifted_datetime.date()),
                    lat=lat,
                    lon=lon,
                    timezone=timezone,
                ).pack(),
            )
        )

    await message.answer(f"Select {type} time:", reply_markup=kb_builder.as_markup())


@router.callback_query(ForecastRequest.filter())
async def forecast(
    callback_query: CallbackQuery,
    callback_data: ForecastRequest,
    bot: Bot,
    API_KEY: str,
    session: aiohttp.ClientSession,
):
    await bot.send_chat_action(chat_id=callback_query.message.chat.id, action="typing")
    await callback_query.message.edit_reply_markup(None)
    await callback_query.message.edit_text("Fetching...")

    lat = callback_data.lat
    lon = callback_data.lon
    date = callback_data.date
    type = callback_data.type
    timezone = callback_data.timezone

    try:
        async with session.get(
            f"https://api.sunsethue.com/event?key={API_KEY}&latitude={lat}&longitude={lon}&date={date}&type={type}"
        ) as response:
            if response.status != 200:
                callback_query.answer()
                callback_query.message.answer(
                    f"Couldn't fetch. API returned {response.status}"
                )
                callback_query.message.delete()
                return None

            response_json = await response.text()

    except aiohttp.ConnectionTimeoutError:
        callback_query.answer()
        callback_query.message.answer(f"API timed out.")
        callback_query.message.delete()
        return None

    await callback_query.answer()
    await callback_query.message.answer(format_forecast(response_json, timezone))
    await callback_query.message.delete()
