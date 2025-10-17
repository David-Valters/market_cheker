from config import config
from datetime import timedelta
import logging
import httpx
import asyncio

logger = logging.getLogger(__name__)


def html_link(text: str, url: str) -> str:
    return f'<a href="{url}">{text}</a>'


def format_timedelta(delta: timedelta) -> str:
    seconds = int(delta.total_seconds())
    
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    print(seconds)
    secs = seconds % 60

    parts = []
    if days > 0:
        parts.append(f"{days} дн")
    if hours > 0:
        parts.append(f"{hours} год")
    if minutes > 0:
        parts.append(f"{minutes} хв")
    if secs > 0 or not parts:  
        parts.append(f"{secs} сек")

    return " ".join(parts) + " тому"


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

async def send_ping_request(arg=None):
    url = config.get("PING_URL")
    if not url:
        logger.warning("⚠️ PING_URL is not set in config")
        return
    if arg:
        url = url+'/'+arg
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(url)
            response.raise_for_status()
            logger.info(f"✅ Ping successful: {url} ({response.status_code})")
    except httpx.HTTPStatusError as e:
        logger.error(f"❌ Ping failed with status {e.response.status_code} for {url}")
    except httpx.RequestError as e:
        logger.error(f"❌ Request error while pinging {url}: {e}")  
        
                  
# print(format_timedelta(timedelta( seconds=1000)))  # Example usage