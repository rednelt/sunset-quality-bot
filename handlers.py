import aiosqlite

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

# To be attached to the dispatcher
router = Router()

# Use FSM for the registration sequence
class Registration(StatesGroup):
    waiting_for_location = State()

@router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    # Create a keyboard with a location request button
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📍 Share Location", request_location=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await message.answer("Hello! This bot can fetch sunset/sunrise quality predictions from " 
        "sunsethue.com for your location. Send a location to begin (press button to share your "
        "location or drop a pin manually)", reply_markup=kb)
    # Switch user to the waiting state
    await state.set_state(Registration.waiting_for_location)

@router.message(Registration.waiting_for_location, F.location)
async def handle_location(message: Message, state: FSMContext):
    lat = message.location.latitude
    lon = message.location.longitude
    user_id = message.from_user.id
    username = message.from_user.username

    # Save to database using UPSERT
    async with aiosqlite.connect("users.sqlite") as db:
        await db.execute("""
            INSERT INTO Users (chat_id, username, lat, lon) 
            VALUES (?, ?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                username = excluded.username,
                lat = excluded.lat,
                lon = excluded.lon
        """, (user_id, username, lat, lon))
        await db.commit()

    await message.answer(f"Saved! Location: {lat}, {lon}", reply_markup=ReplyKeyboardRemove())
    await state.clear()


# Error handler
@router.message(Registration.waiting_for_location)
async def invalid_location(message: Message):
    await message.answer("That wasn't a location. Please use the button or drop a pin.")
