import html, json, os, logging
from typing import Any, Dict

def escape(text: str) -> str:
    return html.escape(text or "")

def load_json(path: str, logger: logging.Logger | None = None, default: Any = None) -> Any:
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return {} if default is None else default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        if logger:
            logger.error(f"Ошибка загрузки {path}: {e}")
        return {} if default is None else default

def save_json(path: str, data: Any, logger: logging.Logger | None = None) -> None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        if logger:
            logger.error(f"Ошибка сохранения {path}: {e}")
        else:
            print(f"Ошибка сохранения {path}: {e}")

def split_text(text: str, chunk_size: int = 4096) -> list[str]:
    return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
