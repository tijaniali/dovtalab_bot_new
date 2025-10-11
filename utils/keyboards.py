from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def vertical_kb(rows: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for text, data in rows:
        kb.inline_keyboard.append([InlineKeyboardButton(text=text, callback_data=data)])
    return kb
