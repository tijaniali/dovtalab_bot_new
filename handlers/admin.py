import asyncio
from aiogram import types
from aiogram.filters import Command
from bot import dp, bot
from config import CFG, AD
from utils.helpers import split_text
from models.user import UserManager
from services.scheduler import DailyStats

users: UserManager | None = None
ad: AD | None = None
stats: DailyStats | None = None

def setup(_users: UserManager, _ad: AD
          , _stats: DailyStats):
    global users, ad, stats
    users = _users
    ad = _ad
    stats = _stats

@dp.message(Command("send_announcement"))
async def send_announcement(msg: types.Message):
    if str(msg.from_user.id) != CFG.ADMIN_ID:
        return await msg.reply("Только администратор может использовать эту команду!")

    parts = (msg.text or msg.caption or "").split(maxsplit=1)
    if len(parts) < 2:
        return await msg.reply("Укажи текст после команды")

    text = parts[1]
    media_id = None
    media_type = None
    if msg.photo:
        media_type = "photo"
        media_id = msg.photo[-1].file_id
    elif msg.video:
        media_type = "video"
        media_id = msg.video.file_id

    ok, bad = 0, 0
    for uid, data in users.users.items():
        if not data.get("started"):
            continue
        try:
            if media_type and media_id:
                if media_type == "photo":
                    await bot.send_photo(uid, media_id, caption=text, parse_mode="HTML")
                else:
                    await bot.send_video(uid, media_id, caption=text, parse_mode="HTML")
            else:
                for chunk in split_text(text):
                    await bot.send_message(uid, chunk, parse_mode="HTML")
                    await asyncio.sleep(0.05)
            ok += 1
        except Exception:
            data["started"] = False
            bad += 1
        await asyncio.sleep(0.05)
    users.save()
    await msg.reply(f"Готово. Успех: {ok}, ошибок: {bad}")

@dp.message(Command("clear_unactives"))
async def clear_unactives(msg: types.Message):
    # Проверяем, что команду вызвал администратор
    if str(msg.from_user.id) != CFG.ADMIN_ID:
        return await msg.reply("Только администратор может использовать эту команду!")

    # Сначала собираем всех пользователей, которые не запускали бота
    inactive_users = [uid for uid, data in users.users.items() if not data.get("started")]

    # Удаляем их из словаря
    for uid in inactive_users:
        users.users.pop(uid, None)

    # Сохраняем обновлённые данные
    users.save()

    await msg.reply(f"Неактивные пользователи очищены: {len(inactive_users)}")


@dp.message(Command("set_ad"))
async def set_ad(msg: types.Message):
    assert users
    users.ensure(msg.chat.id,
                 is_group=(msg.chat.type != "private"),
                 title=getattr(msg.chat, "title", None),
                 username=getattr(msg.from_user, "username", None),
                 first_name=getattr(msg.from_user, "first_name", None),
                 is_started=True)

    lang = users.get_lang(str(msg.chat.id) if msg.chat.type != "private" else str(msg.from_user.id), "tg")
    messages = (getattr(bot, "context", {}) or {}).get("messages", {}).get(lang, {})
    if (str(msg.from_user.id) != CFG.ADMIN_ID):
        return await msg.reply(messages.get("set_ad_error", "Только админ может установить рекламу!"), parse_mode="HTML")
    try:
        ad.set_ad(msg.text.removeprefix("/set_ad"))
        return await msg.reply(messages.get("ad_is_set", "✅ Реклама успешно установлена!"), parse_mode="HTML")
    except:
        return await msg.reply("Неизвестная ошибка", parse_mode="HTML")

@dp.message(Command("dell_ad"))
async def dell_ad(msg: types.Message):
    assert users
    users.ensure(msg.chat.id,
                 is_group=(msg.chat.type != "private"),
                 title=getattr(msg.chat, "title", None),
                 username=getattr(msg.from_user, "username", None),
                 first_name=getattr(msg.from_user, "first_name", None),
                 is_started=True)

    lang = users.get_lang(str(msg.chat.id) if msg.chat.type != "private" else str(msg.from_user.id), "tg")
    messages = (getattr(bot, "context", {}) or {}).get("messages", {}).get(lang, {})
    if (str(msg.from_user.id) != CFG.ADMIN_ID):
        return await msg.reply(messages.get("del_ad_error", "Только админ может удалить рекламу!"), parse_mode="HTML")
    try:
        ad.set_ad("")
        return await msg.reply(messages.get("ad_is_deleted", "✅ Реклама успешно удалена!"), parse_mode="HTML")
    except:
        return await msg.reply("Неизвестная ошибка", parse_mode="HTML")

@dp.message(Command("get_ad"))
async def get_ad(msg: types.Message):
    assert users
    users.ensure(msg.chat.id,
                 is_group=(msg.chat.type != "private"),
                 title=getattr(msg.chat, "title", None),
                 username=getattr(msg.from_user, "username", None),
                 first_name=getattr(msg.from_user, "first_name", None),
                 is_started=True)

    lang = users.get_lang(str(msg.chat.id) if msg.chat.type != "private" else str(msg.from_user.id), "tg")
    messages = (getattr(bot, "context", {}) or {}).get("messages", {}).get(lang, {})
    if (str(msg.from_user.id) != CFG.ADMIN_ID):
        return await msg.reply(messages.get("get_ad_error", "Только админ может изменить рекламу!"), parse_mode="HTML")
    try:
        if (ad.get_ad() == ""):
            return await msg.reply(messages.get("not_ad",  "Реклама не установлена!"), parse_mode="HTML")
        return await msg.reply(messages.get("actual_ad",  "Текущая реклама: \n\n {value}").format(value=ad.get_ad()), parse_mode="HTML")
    except:
        return await msg.reply("Неизвестная ошибка", parse_mode="HTML")

@dp.message(Command("get_stats"))
async def get_stats(msg: types.Message):
    assert users
    users.ensure(msg.chat.id,
                 is_group=(msg.chat.type != "private"),
                 title=getattr(msg.chat, "title", None),
                 username=getattr(msg.from_user, "username", None),
                 first_name=getattr(msg.from_user, "first_name", None),
                 is_started=True)

    lang = users.get_lang(str(msg.chat.id) if msg.chat.type != "private" else str(msg.from_user.id), "tg")
    messages = (getattr(bot, "context", {}) or {}).get("messages", {}).get(lang, {})
    if (str(msg.from_user.id) != CFG.ADMIN_ID):
        return await msg.reply(messages.get("not_admin", "🚫 Эта настройка доступна только администратору!"), parse_mode="HTML")
    try:
        text = stats.get_stats()
        text += f"Всего пользователей бота: {len(users.get_all_users())}"
        return await msg.reply(text=text, parse_mode="HTML")
    except:
        return await msg.reply("Неизвестная ошибка", parse_mode="HTML")

@dp.message(Command("get_groups"))
async def get_gropus(msg: types.Message):
    assert users
    users.ensure(msg.chat.id,
                 is_group=(msg.chat.type != "private"),
                 title=getattr(msg.chat, "title", None),
                 username=getattr(msg.from_user, "username", None),
                 first_name=getattr(msg.from_user, "first_name", None),
                 is_started=True)

    lang = users.get_lang(str(msg.chat.id) if msg.chat.type != "private" else str(msg.from_user.id), "tg")
    messages = (getattr(bot, "context", {}) or {}).get("messages", {}).get(lang, {})
    if (str(msg.from_user.id) != CFG.ADMIN_ID):
        return await msg.reply(messages.get("not_admin", "🚫 Эта настройка доступна только администратору!"),
                               parse_mode="HTML")
    groups = users.get_all_users()
    text = ""
    i = 1
    for group_id, group_data in groups.items():  # <-- здесь .items()
        if group_data["type"] == "group" and group_data["started"]:
            text += f"{i}: {group_data['chat_title']}\nlink: {group_data['chat_link']}\n\n"
            i += 1

    if text != "":
        await msg.reply(text, parse_mode="HTML")
    else:
        await msg.reply("Список ещё пуст")
