from dotenv import dotenv_values # type: ignore

config:dict[str,str|None] = {
    **dotenv_values(".env"),
}

KEYS_NEEDED:list[str] = ["TOKEN_BOT", "chat_id", "mrkt_token"]

if not all(key in config for key in KEYS_NEEDED):
    raise ValueError(f"Відсутнє значення у файлі .env: {', '.join(key for key in KEYS_NEEDED if key not in config)}")



