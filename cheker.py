# from time import sleep
import asyncio
from datetime import datetime, timedelta
from aiogram import Bot
import os

from more_itertools import first, last
from config import config
import db
import logging
from utils import html_link
import traceback

logger = logging.getLogger(__name__)

datetime_lascheck_skins = None
status: str = "*Відсутній*"


def make_url_in_market(id):
    id = id.replace("-", "")
    return f"https://t.me/mrkt/app?startapp=gameitemshare{id}"


def make_url_icon(url: str) -> str:
    return f"https://cdn.tgmrkt.io/{url}"


import httpx
from typing import List


async def post_with_retry(url, payload, headers, retries=3, delay=5):
    for attempt in range(1, retries + 1):
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
        except httpx.ConnectError:
            logging.warning(f"❌ ConnectError: спроба {attempt}/{retries}")
            if attempt == retries:
                raise
            await asyncio.sleep(delay)


async def get_lowest_price_lots(id: str) -> List[dict]:
    url = "https://api.tgmrkt.io/api/v1/notgames/saling"
    headers = {
        "Authorization": db.get_token() or "",  # type: ignore
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Origin": "https://cdn.tgmrkt.io",
        "Referer": "https://cdn.tgmrkt.io/",
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
        "query": None,
    }

    data = await post_with_retry(url, payload, headers)

    items = data.get("gameItems", [])
    result: List[dict] = []

    for item in items[:10]:
        price = item.get("salePrice")
        if price is not None:
            r = item
            r["serial"] = str(item.get("serial", "unknown (bug)"))
            r["salePrice"] = round(float(price) / 1_000_000_000, 2)
            result.append(r)

    return result


# async def check(skin: dict) -> tuple[int | None, str, List[str]]:
#     skin_id = skin["skin_id"]
#     new_lots = (await get_lowest_price_lots(skin_id))[:5]
#     old_price = skin["price"]
#     current_price = new_lots[0]["salePrice"]
#     new_lots_id = [lot["id"] for lot in new_lots]

#     if current_price == old_price:
#         return None, "", new_lots_id

#     past_lots = db.get_top_lots(skin_id)
#     ids_past_lots = [id for id in past_lots]
#     mes = [
#         skin["name"],
#         (
#             f"Price changed from {old_price} > {current_price}."
#             if past_lots and past_lots[0].lot_id == new_lots_id[0]
#             else f"The {html_link("skin",make_url_in_market(skin_id))} was most likely purchased for {old_price}"
#         ),
#         "\nІнші ціни:",
#         *[
#             # 1: 3.08 (#22)
#             f"{i+1}. {lot['salePrice']} (#{html_link(lot['serial'], make_url_in_market(lot['id']) )}) {"! N E W !" if lot['id'] not in ids_past_lots else ""}\n"
#             for i, lot in enumerate(new_lots)
#         ],
#     ]
#     return current_price, "\n".join(mes), new_lots_id


# async def skin_check(bot: Bot) -> None | str:
#     skin = db.get_next_skin_to_check()
#     if not skin:
#         logger.info("No skins to check.")
#         return None
#     new_price, mes, new_lots_id = await check(skin)
#     if new_price:
#         await bot.send_photo(
#             photo=skin["icon_url"],
#             chat_id=config["chat_id"],  # type: ignore
#             caption=mes,
#             parse_mode="HTML",
#         )
#         logger.info(f"Skin {skin['skin_id']} price changed to {new_price}).")
#     else:
#         logger.info(f"Skin {skin["skin_id"]} price has not changed")
#     db.mark_skin_checked(skin["skin_id"], new_price)
#     db.save_top_lots(skin["skin_id"], new_lots_id)
#     global datetime_lascheck_skins
#     datetime_lascheck_skins = datetime.now()
#     return db.get_next_skin_to_check().get("skin_id")  # type: ignore


async def get_feed(cursor: str | None) -> tuple[list[dict[str, str]], str]:
    url = "https://api.tgmrkt.io/api/v1/notgames-feed"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Language": "uk-UA,uk;q=0.8,en-US;q=0.5,en;q=0.3",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Referer": "https://cdn.tgmrkt.io/",
        "Content-Type": "application/json",
        "authorization": db.get_token() or "",
        "Origin": "https://cdn.tgmrkt.io",
        "DNT": "1",
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
        "Priority": "u=0",
        "TE": "trailers",
    }
    payload = {
        "count": 20,
        "cursor": cursor or "",
        "collectionNames": [],
        "gameIds": [2],
        "number": None,
        "type": [],
        "ordering": "Latest",
        "lowToHigh": False,
        "isPremarket": None,
        "query": None,
    }

    data = await post_with_retry(url, payload, headers)

    items = data.get("items", [])
    result: List[dict] = []

    for item in items:
        r = item.get("gameItem", {})
        r["type"] = item.get("type", "")
        r["lot_id"] = item.get("id", "")
        r["serial"] = str(r.get("serial", "unknown"))
        price = r.get("salePrice")
        if price is not None:
            r["salePrice"] = round(float(price) / 1_000_000_000, 2)
            result.append(r)

    return result, data.get("cursor")


async def get_new_feed_lots(max_requests=10) -> tuple[List[dict], bool]:
    logger.info("Checking for new feed lots...")
    result = []
    old_cursor = db.get_feed_cursor()
    global status
    r, cursor = await get_feed(None)
    status = "Зроблене початкове онволення feed."
    new_cursor = r[0]["lot_id"]
    is_find_cursor = False

    if not old_cursor:
        result.extend(r)
    else:
        requests_count = 1
        while True:
            for item in r:
                if item["lot_id"] != old_cursor:
                    result.append(item)
                else:
                    is_find_cursor = True
                    break

            if is_find_cursor:
                logger.info(f"Found old cursor {old_cursor} in feed.")
                break

            requests_count += 1
            if requests_count > max_requests:
                logger.warning("Too many requests, stopping feed check.")
                break
            logger.info(f"Checking feed {requests_count}/{max_requests}")
            status = f"Оновлення feed {requests_count}/{max_requests}..."
            await asyncio.sleep(1)
            r, cursor = await get_feed(cursor)

    db.set_feed_cursor(new_cursor)
    return result, is_find_cursor


# async def feed_check_old(bot: Bot) -> None:
#     lots = await get_new_feed_lots()
#     for lot in lots[::-1]:
#         skin_id = lot["gameItemDefId"]
#         skin = db.get_skin(skin_id)
#         if not skin:
#             continue
#         mes: list[str] = [
#             f"{lot["name"]} #{lot["serial"]}",
#             (
#                 f"{html_link("Listing",make_url_in_market(lot["id"]))} for {lot["salePrice"]}"
#                 if lot["type"] == "listing"
#                 else f"{html_link("Sale",make_url_in_market(lot["id"]))} for {lot["salePrice"]}"
#             ),
#             "",
#             "(fast info from feed)",
#         ]
#         await bot.send_photo(
#             photo=make_url_icon(lot["iconUrl"]),
#             chat_id=config["chat_id"],  # type: ignore
#             caption="\n".join(mes),
#             parse_mode="HTML",
#         )
#         logger.info(f"New lot: {skin_id} - {lot['salePrice']} ({lot['type']})")


async def processing_lot(bot: Bot, lot: dict, cache_top_lot: dict) -> bool:
    skin_id = lot["gameItemDefId"]
    skin = db.get_skin(skin_id)
    was_request = False

    if not skin:  # цей скін не відслідковується
        return was_request

    save_lots = db.get_top_lots(skin_id)
    last_save_lot = last(save_lots, None)

    if (
        lot["type"] == "listing"
        and last_save_lot
        and last_save_lot.price != 0
        and lot["salePrice"] >= last_save_lot.price
    ):
        logger.info(
            f"Lot {lot['lot_id']} for skin {skin["name"]} price {lot["salePrice"]} not interested."
        )
        return was_request

    if skin_id in cache_top_lot:
        new_top_lots = cache_top_lot[skin_id]
    else:
        logger.info(f"Getting top lots for skin {skin_id}.")
        new_top_lots = (await get_lowest_price_lots(skin_id))[:5]
        cache_top_lot[skin_id] = new_top_lots
        db.update_lots(skin_id, new_top_lots)
        was_request = True

    target_lot_in_save = next((l for l in save_lots if l.serial == lot["serial"]), None)
    best_lot = first(new_top_lots, None)

    if (
        lot["type"] == "listing"
        and target_lot_in_save
        and target_lot_in_save.price != 0
    ):  # price changed
        mes_info = f"Skin reLISTING {target_lot_in_save.price} > {lot['salePrice']}. {"(This is not the best price)" if best_lot and best_lot["salePrice"] < lot["salePrice"] else ""}"
    elif lot["type"] == "listing":
        mes_info = f"The skin was LISTING for {lot['salePrice']} {"\n(This is not the best price)" if best_lot and best_lot["salePrice"] < lot["salePrice"] else ""}"
    else:  # sale
        mes_info = f"The skin was SALE for {lot['salePrice']}"

    ids_old_lots = [l.lot_id for l in save_lots]

    mes = [
        f"{html_link(skin['name'],make_url_in_market(skin_id))  } #{lot['serial']}",
        mes_info,
        "\nІнші ціни:",
        *[
            f"{i+1}. {new_lot['salePrice']} (#{html_link(new_lot['serial'], make_url_in_market(new_lot['id']))}) {'! N E W !' if new_lot['id'] not in ids_old_lots else ''}\n"
            for i, new_lot in enumerate(new_top_lots)
        ],
        f"SUPLAY({lot["supply"]})"
    ]

    await bot.send_photo(
        photo=make_url_icon(lot["iconUrl"]),
        chat_id=config["chat_id"],  # type: ignore
        caption="\n".join(mes),
        parse_mode="HTML",
    )
    db.mark_skin_checked(skin_id)
    return was_request


async def processing_skin(bot: Bot, skin_id: str) -> None:
    skin = db.get_skin(skin_id)

    if not skin:
        logger.error(f"Skin {skin_id} not found in database.")
        return

    save_lots = db.get_top_lots(skin_id)
    first_save_lot = first(save_lots, None)

    if first_save_lot and first_save_lot.price != 0:
        old_price = first_save_lot.price
    else:
        old_price = float(skin["price"])

    many_new_top_lots = await get_lowest_price_lots(skin_id)
    new_top_lots = many_new_top_lots[:5]

    if old_price == new_top_lots[0]["salePrice"]:
        logger.info(f"Skin {skin["name"]} price has not changed.")
    else:
        logger.info(
            f"Skin {skin['name']} price changed from {old_price} to {new_top_lots[0]['salePrice']}."
        )
        if first_save_lot and first_save_lot.serial != "unknown":
            link = html_link(
                first_save_lot.serial, make_url_in_market(first_save_lot.lot_id)
            )
            if first_save_lot.serial == new_top_lots[0]["serial"]:
                mes_info = f"Skin #{link} price changed from {old_price} > {new_top_lots[0]['salePrice']}."
            elif first_save_lot.serial in [
                new_lot["serial"] for new_lot in many_new_top_lots
            ]:
                mes_info = f"Skin #{link} not top 1st lot"
            else:
                mes_info = f"Skin #{link} was most likely sold {first_save_lot.price}."
        else:
            mes_info = (
                f"Best price changed from {old_price} > {new_top_lots[0]['salePrice']}."
            )

        mes = [
            f"{skin['name']}",
            mes_info,
            "\nІнші ціни:",
            *[
                f"{i+1}. {lot['salePrice']} (#{html_link(lot['serial'], make_url_in_market(lot['id']))}) {'! N E W !' if lot['id'] not in [l.lot_id for l in save_lots] else ''}\n"
                for i, lot in enumerate(new_top_lots)
            ],
            f"SUPLAY({new_top_lots[0]["supply"]})"
        ]

        skin_photo_url = make_url_icon(new_top_lots[0]["iconUrl"])

        await bot.send_photo(
            photo=skin_photo_url,
            chat_id=config["chat_id"],  # type: ignore
            caption="\n".join(mes),
            parse_mode="HTML",
        )
        logger.info(
            f"Skin {skin['skin_id']} price changed to {new_top_lots[0]['salePrice']})."
        )

    db.update_lots(skin_id, new_top_lots)
    db.mark_skin_checked(skin_id)


async def loop(bot: Bot) -> None:
    global status
    logger.info("Starting skin price check loop...")
    # sem mes bot runing
    if not db.get_token():
        logger.error("Token is not set. Please set the token using /token command.")
        status = "Очікування встановлення токена..."
        await bot.send_message(
            chat_id=config["chat_id"],  # type: ignore
            text="❗ Токен не встановлено. Будь ласка, встановіть токен за допомогою команди /token.",
        )
    await bot.send_message(
        chat_id=config["chat_id"], text="✅ Бот запущено"  # type: ignore
    )
    while not db.get_token():
        logger.info("Waiting for token to be set...")
        await asyncio.sleep(10)

    first_skin = db.get_next_skin_to_check()
    while first_skin is None:
        status = "No more skins to check."
        logger.info("No more skins to check.")
        await asyncio.sleep(10)  # Wait before checking again
        first_skin = db.get_next_skin_to_check()

    ids_skins_need_check: set[str] = set()

    skins = db.get_all_skins()
    ids = [skin["skin_id"] for skin in skins]
    ids_skins_need_check.update(ids)
    global datetime_lascheck_skins

    while True:
        try:
            # ----------
            current_token = db.get_token()

            lots, is_find_cursor = await get_new_feed_lots()

            if not is_find_cursor:
                my_skins = db.get_oldest_skins(timedelta(hours=1))
                ids = [skin["skin_id"] for skin in my_skins]
                ids_skins_need_check.update(ids)

            cache_top_lot: dict = {}
            status = "Обробка лотів з feed..."
            datetime_lascheck_skins = datetime.now()
            for lot in lots[::-1]:
                was_request = await processing_lot(bot, lot, cache_top_lot)
                skin_id = lot["gameItemDefId"]
                if skin_id in ids_skins_need_check:
                    ids_skins_need_check.remove(skin_id)
                if was_request:
                    await asyncio.sleep(2)

            if ids_skins_need_check:
                status = "Обробка давно не перевірених скінів..."
                logger.info(f"! Processing skin {len(ids_skins_need_check)}th ...")
                skin_id = ids_skins_need_check.pop()
                await processing_skin(bot, skin_id)
                if not ids_skins_need_check:
                    logger.info("\n\nAll skins have been checked.\n")

            status = "Очікування 25 секунд перед наступною перевіркою..."
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                last_notif_time = None
                start_wait = datetime.now()
                send_warning = True
                status = "Токен не дійсний, очікування оновлення токена..."
                while current_token == db.get_token():
                    now = datetime.now()
                    if send_warning and (now - start_wait) >= timedelta(minutes=25):
                        logger.warning(
                            "⚠️The laptop will shut down in 5 minutes if the token is not updated!"
                        )
                        await bot.send_message(
                            chat_id=config["chat_id"],  # type: ignore
                            text="⚠️Warning: The laptop will shut down in 5 minutes if the token is not updated!!!",
                        )
                        send_warning = False

                    if (now - start_wait) >= timedelta(minutes=30):
                        await bot.send_message(
                            chat_id=config["chat_id"],  # type: ignore
                            text="🛑 Вимикаю ноутбук...",
                        )
                        await asyncio.sleep(1)
                        logger.warning("Shutting down the laptop...")
                        os.system("shutdown /s /t 1")  # для Windows
                        await asyncio.sleep(10)
                        # Якщо ноутбук не вимкнувся, вимикаємо програму
                        logger.error("🛑 Ноутбук не вимкнувся, вимикаю програму")
                        await bot.send_message(
                            chat_id=config["chat_id"],  # type: ignore
                            text="🛑 Ноутбук не вимкнувся, вимикаю програму",
                        )
                        import sys

                        sys.exit(1)  # Вимкнути програму

                    if last_notif_time is None or (now - last_notif_time) > timedelta(
                        minutes=10
                    ):
                        logger.error("📛Expired TOKEN📛 ")
                        await bot.send_message(
                            chat_id=config["chat_id"],  # type: ignore
                            text="📛Expired TOKEN📛 ",
                        )
                        last_notif_time = now
                    await asyncio.sleep(10)
                continue
            # elif e.response.status_code == 403:
            #     logger.error("❌ Access denied. Check your token.")
            #     await asyncio.sleep(10*60)
            else:
                logger.error(f"HTTP error while checking skin: {e}")
                await bot.send_message(
                    chat_id=config["chat_id"],  # type: ignore
                    text=f"HTTP error while checking skin: {e}",
                )
                await asyncio.sleep(120)
        except httpx.ConnectError as e:
            logger.warning(f"❌ ConnectError: {e}")
            await bot.send_message(
                chat_id=config["chat_id"],  # type: ignore
                text=f"❌ ConnectError while checking skin: {e}",
            )
            await asyncio.sleep(20)
        except httpx.ReadTimeout as e:
            tb = traceback.format_exc()
            logger.warning("⏱ TIMEOUT: Запит до tgmrkt.io завис на skin_id")
            await bot.send_message(config["chat_id"], text=f"⚠️ TIMEOUT при перевірці: {e}\n\n{tb}")  # type: ignore
            await asyncio.sleep(20)
            continue
        except Exception as e:
            tb = traceback.format_exc()
            logger.error(f"Error checking skin: {e}\n\n{tb}")
            text = f"Error checking skin: {e}\n\n{tb}"
            for i in range(0, len(text), 4096):
                await bot.send_message(
                    chat_id=config["chat_id"], text=text[i : i + 4096]  # type: ignore
                )
            await asyncio.sleep(180)
        await asyncio.sleep(25)  # Wait before checking the next skin


# bot = Bot(token=config["TOKEN_BOT"])  # type: ignore
# logger = logging.getLogger(__name__)
# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s [%(levelname)s] %(message)s",
#     handlers=[
#         logging.FileHandler("app.log", mode="a", encoding="utf-8"),  # У файл
#         logging.StreamHandler(),  # У консоль
#     ],
# )
# logger.info("Starting the bot...")
# asyncio.run(feed_check(bot))
