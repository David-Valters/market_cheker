# from time import sleep
import asyncio
from config import config
import db
import logging

logger = logging.getLogger(__name__)

def make_url_in_market(id):
    id=id.replace("-", "")
    return f"https://t.me/mrkt/app?startapp=gameitemshare{id}"

def make_url_icon(url: str) -> str:
   return f"https://cdn.tgmrkt.io/{url}"

import httpx
from typing import List

async def get_sale_prices(id: str) -> List[dict]:
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

    for item in items[:3]:
        price = item.get("salePrice")
        item_id = item.get("id")
        if price is not None:
            result.append({
                "id": item_id,
                "price": round(float(price) / 1_000_000_000, 2)
            })

    return result


from aiogram import Bot
async def loop(bot: Bot) -> None:
    logger.info("Starting skin price check loop...")
    if not db.get_token():
        logger.error("Token is not set. Please set the token using /token command.")
        await bot.send_message(
            chat_id=config["chat_id"],  # type: ignore
            text="❗ Токен не встановлено. Будь ласка, встановіть токен за допомогою команди /token."
        )
    while not db.get_token():
        logger.info("Waiting for token to be set...")
        await asyncio.sleep(10)
    while True:
        skin = db.get_next_skin_to_check()
        if not skin:
            logger.info("No more skins to check.")
            await asyncio.sleep(60)  # Wait before checking again
            continue
        try:
            prices = await get_sale_prices(skin["skin_id"])
            current_price = prices[0]["price"]
            new_price = None
            old_price = skin["price"]
            if current_price != old_price:
                new_price = current_price
                difference = new_price - old_price
                difference_str = f"{difference:+.2f}"  # Format with sign
                other_price_text = "Інші ціни:\n"+"\n".join([f"{count+1}: {price['price']}\n" for count, price in enumerate(prices)])
                
                await bot.send_photo(
                    photo=skin["icon_url"],
                    chat_id=config["chat_id"], #type: ignore
                    caption=f"Skin {skin['name']} ({skin["skin_id"]}) price changed from {old_price} to {new_price} ({difference_str}).\nCheck it out: {make_url_in_market(prices[0]["id"])}\n{other_price_text}",
                )
                logger.info(f"Skin {skin['skin_id']} price changed from {old_price} to {new_price} ({difference_str}).")
            else:
                logger.info(f"Skin {skin["skin_id"]} price has not changed: {old_price}")
            db.mark_skin_checked(skin["skin_id"],new_price)
        except Exception as e:
            logger.error(f"Error checking skin {skin["skin_id"]}: {e}")
            await bot.send_message(
                chat_id=config["chat_id"], #type: ignore
                text=f"Error checking skin {skin["skin_id"]}: {e}"
            )
            await asyncio.sleep(160)  
        await asyncio.sleep(20)  # Wait before checking the next skin