# from time import sleep
import asyncio
from datetime import datetime, timedelta
from config import config
import db
import logging
from utils import html_link
import traceback

logger = logging.getLogger(__name__)
datetime_lascheck = None

def make_url_in_market(id):
    id=id.replace("-", "")
    return f"https://t.me/mrkt/app?startapp=gameitemshare{id}"

def make_url_icon(url: str) -> str:
   return f"https://cdn.tgmrkt.io/{url}"

import httpx
from typing import List

async def get_lowest_price_lots(id: str) -> List[dict]:
    url = "https://api.tgmrkt.io/api/v1/notgames/saling"
    headers = {
        "Authorization": db.get_token() or "",  # type: ignore
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:137.0) Gecko/20100101 Firefox/137.0",
        "Origin": "https://cdn.tgmrkt.io",
        "Referer": "https://cdn.tgmrkt.io/"
    }

    payload = {
        "count": 20,
        "cursor": "",
        "collectionNames": [],
        "gameIds": [2],
        "displayTypes": [],
        "gameItemDefIds": [id],
        "minPrice": None,
        "maxPrice": None,
        "serial": None,
        "ordering": "Price",
        "lowToHigh": True,
        "isPremarket": None,
        "query": None
    }

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(url, json=payload, headers=headers) #type: ignore
        response.raise_for_status()
        data = response.json()

    items = data.get("gameItems", [])
    result: List[dict] = []

    for item in items[:10]:
        price = item.get("salePrice")
        if price is not None:
            r=item
            r["salePrice"] = round(float(price) / 1_000_000_000, 2)
            result.append(r)

    return result


async def check(skin:dict) -> tuple[int|None, str, List[str]]:
    skin_id = skin["skin_id"]
    new_lots = (await get_lowest_price_lots(skin_id))[:5]
    old_price = skin["price"]
    current_price = new_lots[0]["salePrice"]
    new_lots_id = [lot["id"] for lot in new_lots]
    
    if current_price == old_price:
        return None, "", new_lots_id
    
    past_lots_id = db.get_top_lots(skin_id)
    mes = [
        skin["name"],
        f"Price changed from {old_price} > {current_price}."  if past_lots_id and past_lots_id[0] == new_lots_id[0] else 
        f"The {html_link("skin",make_url_in_market(skin_id))} was most likely purchased for {old_price}",
        "\nІнші ціни:",
        *[
            #1: 3.08 (#22)  
            f"{i+1}. {lot['salePrice']} (#{html_link(lot['serial'], make_url_in_market(lot['id']) )}) {"! N E W !" if lot['id'] not in past_lots_id else ""}\n" 
            for i, lot in enumerate(new_lots)
         ]    
    ]    
    return current_price, "\n".join(mes), new_lots_id

from aiogram import Bot
async def loop(bot: Bot) -> None:
    logger.info("Starting skin price check loop...")
    #sem mes bot runing
    if not db.get_token():
        logger.error("Token is not set. Please set the token using /token command.")
        await bot.send_message(
            chat_id=config["chat_id"],  # type: ignore
            text="❗ Токен не встановлено. Будь ласка, встановіть токен за допомогою команди /token."
        )
    await bot.send_message(
        chat_id=config["chat_id"],  # type: ignore
        text="✅ Бот запущено"
    )
    while not db.get_token():
        logger.info("Waiting for token to be set...")
        await asyncio.sleep(10)
    while True:
        skin = db.get_next_skin_to_check()
        if not skin:
            logger.info("No more skins to check.")
            await asyncio.sleep(10)  # Wait before checking again
            continue
        try:
            new_price, mes, new_lots_id = await check(skin)
            if new_price:
                await bot.send_photo(
                    photo=skin["icon_url"],
                    chat_id=config["chat_id"],  # type: ignore
                    caption=mes,
                    parse_mode="HTML"
                )                
                logger.info(f"Skin {skin['skin_id']} price changed to {new_price}).")
            else:
                logger.info(f"Skin {skin["skin_id"]} price has not changed")
            db.mark_skin_checked(skin["skin_id"],new_price)
            db.save_top_lots(skin['skin_id'], new_lots_id)
            global datetime_lascheck
            datetime_lascheck = datetime.now()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                current_token = db.get_token()
                last_notif_time = None
                while current_token == db.get_token():
                    now = datetime.now()
                    if last_notif_time is None or (now - last_notif_time) > timedelta(minutes=10):             
                        logger.error("📛Expired TOKEN📛 ")
                        await bot.send_message(
                            chat_id=config["chat_id"],  # type: ignore
                            text="📛Expired TOKEN📛 "
                        )
                        last_notif_time = now
                    await asyncio.sleep(10)
                continue
            else:
                logger.error(f"HTTP error while checking skin {skin['skin_id']}: {e}")
                await bot.send_message(
                    chat_id=config["chat_id"],  # type: ignore
                    text=f"HTTP error while checking skin {skin['skin_id']}: {e}"
                )
                await asyncio.sleep(120)
        except httpx.ReadTimeout:
            logger.warning(f"⏱ TIMEOUT: Запит до tgmrkt.io завис на skin_id {skin['skin_id']}")
            await bot.send_message(config["chat_id"], text=f"⚠️ TIMEOUT при перевірці {skin['skin_id']}") # type: ignore
            await asyncio.sleep(20)
            continue
        except Exception as e:
            tb = traceback.format_exc()
            logger.error(f"Error checking skin {skin["skin_id"]}: {e}\n\n{tb}")
            text=f"Error checking skin {skin["skin_id"]}: {e}\n\n{tb}"
            for i in range(0, len(text), 4096):
                await bot.send_message(
                    chat_id=config["chat_id"],  # type: ignore
                    text=text[i:i+4096]
                )
            await asyncio.sleep(180)  
        await asyncio.sleep(25)  # Wait before checking the next skin