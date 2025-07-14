def html_link(text: str, url: str) -> str:
    return f'<a href="{url}">{text}</a>'

from datetime import timedelta

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

# print(format_timedelta(timedelta( seconds=1000)))  # Example usage