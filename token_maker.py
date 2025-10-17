# from mimetypes import init
# from operator import ge
# import time
# import json
from pathlib import Path
from urllib.parse import unquote
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.common.exceptions import NoSuchWindowException, WebDriverException
# import logging
from utils import post_with_retry
from config import config

# logger = logging.getLogger(__name__)

BUTTON_SELECTOR = "div.bubbles-group:nth-child(6) > div:nth-child(1) > div:nth-child(1) > div:nth-child(2) > div:nth-child(1) > button:nth-child(1)"
PROFILE_DIR = config["PROFILE_PATH"] if "PROFILE_PATH" in config and config["PROFILE_PATH"] else str(Path.home() / ".chrome_selenium_profile")
TIMEOUT = 40

import os, shutil, time

for name in ["SingletonLock", "SingletonCookie", "SingletonSocket", "SingletonSharedMemory"]:
    f = os.path.join(PROFILE_DIR, name)
    if os.path.exists(f):
        try:
            os.remove(f)
        except:
            pass

options = webdriver.ChromeOptions()


options.add_argument("--start-maximized")
options.add_argument("--disable-extensions")
options.add_argument("--no-sandbox")
options.add_argument("--user-data-dir=" + PROFILE_DIR)
options.add_argument("--profile-directory=Default")

def is_browser_open(driver: WebDriver) -> bool:
    try:
        # будь-який виклик, який звертається до браузера
        _ = driver.current_url
        return True
    except (NoSuchWindowException, WebDriverException):
        return False


def url_to_init_data(s: str) -> str | None:
    start_str = "query_id="
    end_str = "&tgWebAppVersion="
    start_index = s.find(start_str)
    if start_index == -1:
        return None
    # start_index += len(start_str)
    end_index = s.find(end_str, start_index)
    if end_index == -1:
        return None
    return s[start_index:end_index]


def get_init_data() -> str:
    op = webdriver.ChromeOptions()
    op.add_argument("--start-maximized")
    op.add_argument("--disable-extensions")
    op.add_argument("--no-sandbox")
    op.add_argument("--user-data-dir=" + PROFILE_DIR)
    op.add_argument("--profile-directory=Default")
    
    if config.get("HEADLESS_MODE_OFF"):
        op.add_argument("--headless")

    driver = webdriver.Chrome(options=op)

    wait = WebDriverWait(driver, TIMEOUT)

    driver.get("https://web.telegram.org/k/#@mrkt")

    button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, BUTTON_SELECTOR)))

    try:
        button.click()
    except Exception as e:
        print("Could not click the button directly:", e)
        # fallback: element covered / not clickable -> click via JS
        driver.execute_script("arguments[0].click();", button)

    iframe_element = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "/html/body/div[8]/div/div[2]/div/div/iframe")
        )
    )
    # iframe_element = driver.find_element(By.XPATH, "/html/body/div[8]/div/div[2]/div/div/iframe")

    src_attribute = iframe_element.get_attribute("src")

    driver.quit()
    if src_attribute is None:
        raise ValueError("src attribute is None")
    url = unquote(src_attribute)
    init_data = url_to_init_data(url)
    if init_data is not None:
        return init_data
    else:
        raise ValueError(f"Could not extract init data from URL {url}")


async def get_new_token() -> str:
    init_data = get_init_data()
    url = "https://api.tgmrkt.io/api/v1/auth"
    body = {"data": init_data, "appId": "null"}
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Origin": "https://cdn.tgmrkt.io",
        "Referer": "https://cdn.tgmrkt.io/",
    }
    response_json = await post_with_retry(
        url, payload=body, headers=headers, retries=3, delay=5
    )
    if "token" not in response_json:
        raise ValueError(f"'token' not found in response: {response_json}")
    return response_json["token"]


if __name__ == "__main__":
    print(f"Using profile directory: {PROFILE_DIR}")
    driver = webdriver.Chrome(options=options)
    driver.get("https://web.telegram.org/k/#@mrkt")
    input("Натисніть Enter після входу в обліковий запис Telegram у відкритому вікні браузера...")
    try:
        driver.quit()
    except:
        pass
    print("Пробую отримати токен...")
    import asyncio
    token = asyncio.run(get_new_token())
    print(f"Отримано токен: {token}")
