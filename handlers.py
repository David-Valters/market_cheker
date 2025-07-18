from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.types import LinkPreviewOptions
#read json from data.json
import json
from aiogram.utils.formatting import Text, Bold
from config import config 
from cheker import  get_lowest_price_lots
import cheker
from utils import *
import logging
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

data_file = 'data.json'

data = {}

with open(data_file, 'r') as file:
    data = json.load(file)

from aiogram import types
from aiogram.types import InlineQueryResultArticle, InputTextMessageContent, InlineQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.command import Command
# from aiogram.utils import executor
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from typing import Callable, Awaitable, Dict, Any
import uuid
import db
from cheker import  make_url_in_market, make_url_icon
import cheker

router = Router()

class AccessControlMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        chat = data.get("event_chat")
        chat_type = getattr(chat, "type", None)
        if chat and str(chat.id) != config["chat_id"]:
            if chat_type == "private":
                if hasattr(event, "answer"):
                    await event.answer("⛔ Цей чат не має доступу до бота.")
                elif hasattr(event, "message"):
                    await event.message.answer("⛔ Цей чат не має доступу до бота.")
            return  
        return await handler(event, data)

async def add_legendary_skins():
    if not db.get_token():
        logger.error("Token is not set.")
    while not db.get_token():
        logger.info("Waiting for token to be set...")
        await asyncio.sleep(10)
    legendary_skin = [skin for skin in data if "rarity:legendary" in skin["tags"][0]]
    for count, item in enumerate(legendary_skin):
        skin_id = item["id"]
        # price = (await get_sale_prices(skin_id))[0]["price"]
        lot = await get_lowest_price_lots(skin_id)
        price = lot[0]["salePrice"]
        db.add_skin(skin_id, item.get("name", "Unknown Skin"), price, make_url_icon(item.get("iconUrl", "")))
        logger.info(f"Done {count+1}/{len(legendary_skin)}: {item['name']} ({skin_id}) - {price}")



@router.message(Command(commands=["start","menu"]))
async def menu(message: types.Message):
    logger.info(f"[START] Name: {message.chat.full_name}, ChatId: {message.chat.id}")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Вибрати скін", switch_inline_query_current_chat="")],
    ])
    await message.answer("Натисни кнопку щоб почати пошук 👇", reply_markup=keyboard)


@router.message(Command("skin"))
async def on_selected_result(message: types.Message):
    logger.info(f"[SKIN COMMAND] Name: {message.chat.full_name}, ChatId: {message.chat.id}, text: '{message.text}'")
    args = message.text.split(" ", 1)  # type: ignore[union-attr]
    if len(args) < 2:
        await message.answer("Будь ласка, вкажіть ID скіна після команди /skin")
        return
    await message.delete()  # Видаляємо команду, щоб не засмічувати чат
    
    selected_id = args[1].strip()
    data_element = next((item for item in data if item['id'] == selected_id), None)
    
    if not data_element:
        await message.answer("Невірний ID скіна. Спробуйте ще раз.")
        return
    
    is_in_db = db.get_skin(selected_id) is not None
    if is_in_db:
        second_button = InlineKeyboardButton(text="❌ Видалити з обраного", callback_data=f"del:{selected_id}")  
    else:
        second_button = InlineKeyboardButton(text="➕ Додати до обраного", callback_data=f"add:{selected_id}")

    inline_keyboard=[
        [
            InlineKeyboardButton(text="ℹ️ Ціна", callback_data=f"info:{selected_id}"),
            second_button
        ]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


    text = Text(Bold(data_element["name"])) # type: ignore
    await message.answer_photo(
        photo=make_url_icon(data_element.get("iconUrl", "")),
        caption=text.as_html(),
        reply_markup=keyboard,
        parse_mode="HTML"
    )

# @router.message(F.text)
# async def echo(message: types.Message):
#     logger.info(f"[MESSAGE] Name: {message.chat.full_name}, ChatId: {message.chat.id}, text: '{message.text}'")
#     await message.answer(f"Ти написав: {message.text}\nСпробуй ввести /menu для початку пошуку скіна.")

@router.inline_query()
async def inline_handler(query: InlineQuery):
    user_query = query.query.strip()
    logger.info(f"[INLINE QUERY] From: {query.from_user.username}, query: '{user_query}'")
    if not user_query:
        results = [
            InlineQueryResultArticle(
                id=str(uuid.uuid4()),
                title="Введіть щось для пошуку",
                input_message_content=InputTextMessageContent(
                    message_text="Спробуй ввести щось після @назва_бота"
                )
            )
        ]
    else:
        # Сюди можеш підключити справжній пошук
        data_filter = [item for item in data if user_query.lower() in item['name'].lower()]
        results = [
            InlineQueryResultArticle(
                id=str(uuid.uuid4()),
                title=item['name'],
                description=item.get('description', 'Немає опису'),
                thumbnail_url= make_url_icon(item.get('iconUrl', '')),
                input_message_content=InputTextMessageContent(
                    message_text=f"/skin {item['id']}"
                )
            ) for item in data_filter
        ]
    await query.answer(results, cache_time=1000) # type: ignore[arg-type]


    
@router.callback_query(F.data.startswith("add:"))
async def handle_add(callback: CallbackQuery):
    logger.info(f"[CALLBACK ADD] From: {callback.from_user.username}, data: '{callback.data}'")
    selected_id = callback.data.split("add:")[1]# type: ignore[union-attr]
    data_element = next((item for item in data if item['id'] == selected_id), None)
    if not data_element:
        await callback.answer("Невірний ID скіна. Спробуйте ще раз.", show_alert=True)
        return
    else:
        try:
            # price = (await get_sale_prices(selected_id))[0]["price"]
            lot = await get_lowest_price_lots(selected_id)
            price = lot[0]["salePrice"]
        except Exception as e:
            logger.error(f"Error getting price for skin {selected_id}: {str(e)}")
            await callback.message.answer(f"❌ Помилка при отриманні ціни: {str(e)}") # type: ignore[union-attr]
            return
        db.add_skin(selected_id, data_element.get("name", "Unknown Skin"), price, make_url_icon(data_element.get("iconUrl", "")))
        await callback.answer(f"✅ Додано до обраного, ціна: {price}", show_alert=False)
    await callback.message.delete() # type: ignore[union-attr]

@router.callback_query(F.data.startswith("del:"))
async def handle_del(callback: CallbackQuery):
    logger.info(f"[CALLBACK DEL] From: {callback.from_user.username}, data: '{callback.data}'")
    selected_id = callback.data.split("del:")[1]# type: ignore[union-attr]

    db.remove_skin(selected_id)

    await callback.answer("❌ Видалено з обраного", show_alert=False)
    await callback.message.delete() # type: ignore[union-attr]

@router.callback_query(F.data.startswith("info:"))
async def handle_info(callback: CallbackQuery):
    logger.info(f"[CALLBACK INFO] From: {callback.from_user.username}, data: '{callback.data}'")
    skin_id = callback.data.split("info:")[1]# type: ignore[union-attr]
    new_lots = await get_lowest_price_lots(skin_id)
    mes = [
        *[
            #1: 3.08 (#22)  
            f"{i+1}. {lot['salePrice']} (#{html_link(lot['serial'], make_url_in_market(lot['id']) )})\n" 
            for i, lot in enumerate(new_lots)
         ]    
    ]
    mes_text = "\n".join(mes)
    await callback.answer()
    await callback.message.reply( # type: ignore[union-attr]
        text=mes_text,
        parse_mode="HTML",
        link_preview_options = LinkPreviewOptions(is_disabled=True),
    )

@router.message(Command("token"))
async def set_token(message: types.Message):
    args = message.text.split(" ", 1)  # type: ignore[union-attr]
    if len(args) < 2:
        await message.answer("Будь ласка, вкажіть token скіна після команди /token (наприклад, /token 1234567890)")
        return    
    new_token = args[1].strip()
    db.set_token(new_token)
    await message.answer(f"✅ Токен встановлено")


@router.message(Command("ping"))
async def ping(message: types.Message):
    if not cheker.datetime_lascheck_skins:
        await message.answer("Бот ще не здійснював перевірку цін.")
        return

    delta = datetime.now() - cheker.datetime_lascheck_skins
    time_text = format_timedelta(delta)

    await message.answer(f"Бот останній раз перевіряв ціни {time_text}.")