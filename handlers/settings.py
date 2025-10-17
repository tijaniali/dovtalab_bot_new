from aiogram import types
from aiogram.filters import Command
from bot import dp, bot
from models.user import UserManager
from utils.keyboards import vertical_kb
from config import LANGUAGES
users: UserManager | None = None

def setup(_users: UserManager):
    global users
    users = _users

@dp.message(Command("help"))
async def help(msg: types.Message):
    assert  users
    lang_key = str(msg.from_user.id)
    lang = users.get_lang(lang_key, "tg")
    messages = (getattr(bot, "context", {}) or {}).get("messages", {}).get(lang, {})
    await msg.reply(messages.get("help", "Доступные команды:\n\n/start_quiz [Тема предмета] - начать викторину.\n• Эта команда используется для запуска викторины.\n• В поле [Тема предмета] укажите название предмета, по которому хотите пройти викторину.\n• Пример: /start_quiz БИОЛОГИЯ\n\n/stop_quiz - завершить викторину.\n• Если викторина уже началась, и вы хотите её завершить, эта команда немедленно остановит её.\n• Команда используется для остановки викторины в текущем чате.\n\n/rating - показать рейтинг игроков.\n• Используйте эту команду, чтобы увидеть рейтинг (очки) игроков.\n• Рейтинг рассчитывается на основе количества правильных ответов.\n\n/set_time [время] - установить время ответа для викторины.\n• Эта команда задаёт допустимое время для ответа на каждый вопрос.\n• В поле [время] укажите количество секунд.\n• Пример: /set_time 30 (означает, что на каждый вопрос даётся 30 секунд)\n\n/set_count [количество] - задать количество вопросов в викторине.\n• Эта команда определяет, сколько вопросов будет в викторине.\n• Число должно быть в допустимых пределах (например, от 3 до 30 вопросов).\n• Пример: /set_count 10 для 10 вопросов в викторине\n\n/help - показать список доступных команд с подробным описанием.\n• Эта команда отображает все доступные команды с пояснениями и примерами."
                    ),
                    parse_mode="HTML")

@dp.message(Command("set_time"))
async def set_time(msg: types.Message):
    assert users
    users.ensure(msg.from_user.id,
                 username=getattr(msg.from_user, "username", None),
                 first_name=getattr(msg.from_user, "first_name", None),
                 is_started=True)

    lang = users.get_lang(str(msg.chat.id) if msg.chat.type != "private" else str(msg.from_user.id), "tg")
    messages = (getattr(bot, "context", {}) or {}).get("messages", {}).get(lang, {})
    key = str(msg.chat.id if msg.chat.type != "private" else msg.from_user.id)
    parts = msg.text.split(maxsplit=1)
    if (users.get_type(key) == "group"):
        chat_member = await bot.get_chat_member(key, msg.from_user.id)
        if  chat_member.status not in ["administrator", "creator"]:
            return await msg.reply(messages.get("set_time_not_admin", "Только админ может изменить время викторины!"), parse_mode="HTML")
    if len(parts) < 2:
        return await msg.reply(messages.get('set_time_not_value', "⚠ Не указано время викторины!"), parse_mode="HTML")
    try:
        val = int(parts[1])
    except ValueError:
        return await msg.reply(messages.get('set_time_incorrect',"⚠ Некорректное время викторины!"), parse_mode="HTML")
    if val != 0 and not (5 <= val <= 60):
        return await msg.reply(messages.get("set_time_limit", "⚠ Время викторины должно быть от 5 до 60 секунд!"), parse_mode="HTML")
    users.set_quiz_time(key, val)
    await msg.reply(messages.get("time_is_set", "✅ Время викторины установлено на {value} секунд").format(value=val), parse_mode="HTML")

@dp.message(Command("set_count"))
async def set_count(msg: types.Message):
    assert users
    users.ensure(msg.from_user.id,
                 username=getattr(msg.from_user, "username", None),
                 first_name=getattr(msg.from_user, "first_name", None),
                 is_started=True)

    lang = users.get_lang(str(msg.chat.id) if msg.chat.type != "private" else str(msg.from_user.id), "tg")
    messages = (getattr(bot, "context", {}) or {}).get("messages", {}).get(lang, {})
    key = str(msg.chat.id if msg.chat.type != "private" else msg.from_user.id)
    if (users.get_type(key) == "group"):
        chat_member = await bot.get_chat_member(key, msg.from_user.id)
        if chat_member.status not in ["administrator", "creator"]:
            return await msg.reply(messages.get("set_count_not_admin", "Только админ может изменить количество вопросов в викторине!"), parse_mode="HTML")
    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2:
        return await msg.reply(messages.get("set_count_not_value", "⚠ Не указано количество вопросов в викторине!"), parse_mode="HTML")
    try:
        n = int(parts[1])
    except ValueError:
        return await msg.reply(messages.get("set_count_incorrect", "⚠ Некорректное количество вопросов в викторине!"), parse_mode="HTML")
    if not (3 <= n <= 30):
        return await msg.reply(messages.get("set_count_limit", "⚠ Количество вопросов должно быть от 3 до 30!"))
    users.set_num_questions(key, n)
    await msg.reply(messages.get("count_is_set", "✅ Количество вопросов в викторине установлено на {value}").format(value=n), parse_mode="HTML")

@dp.message(Command("set_lang"))
async def set_lang(msg: types.Message):
    assert users
    users.ensure(msg.from_user.id,
                 username=getattr(msg.from_user, "username", None),
                 first_name=getattr(msg.from_user, "first_name", None),
                 is_started=True)

    lang = users.get_lang(str(msg.chat.id) if msg.chat.type != "private" else str(msg.from_user.id), "tg")
    messages = (getattr(bot, "context", {}) or {}).get("messages", {}).get(lang, {})
    if msg.chat.type == "private":
        rows = [(name, f"set_lang:user:{code}") for code, name in LANGUAGES.items()]
        return await msg.answer(messages.get("choose_lang",  "Выберите язык:"), reply_markup=vertical_kb(rows), parse_mode="HTML")
    else:
        chat_member = await bot.get_chat_member(msg.chat.id, msg.from_user.id)
        if chat_member.status not in ["administrator", "creator"]:
            return await msg.reply(messages.get("lang_for_gr_error", "Только админ может изменить язык для группы!"), parse_mode="HTML")
        rows = [(name, f"set_lang:group:{msg.chat.id}:{code}") for code, name in LANGUAGES.items()]
        try:
            await bot.send_message(chat_id=str(msg.from_user.id), text=messages.get("lang_for_gr", "Настройка языка для группы «{group}».\nВыберите язык:").format(group=msg.chat.title), reply_markup=vertical_kb(rows), parse_mode="HTML")
            await msg.reply(messages.get("lang_for_gr_sent",  "✅ Настройка языка отправлена вам в личные сообщения."), parse_mode="HTML")
        except:
            await msg.answer("Ощибка! Админстратор уведомлено.", parse_mode="HTML")
        return


@dp.callback_query(lambda c: c.data and c.data.startswith("set_lang:"))
async def set_lang_callback(msg: types.CallbackQuery):
    assert users
    users.ensure(msg.from_user.id,
                 username=getattr(msg.from_user, "username", None),
                 first_name=getattr(msg.from_user, "first_name", None),
                 is_started=True)

    lang = users.get_lang(str(msg.from_user.id), "tg")
    messages = (getattr(bot, "context", {}) or {}).get("messages", {}).get(lang, {})

    parts = msg.data.split(":")
    if parts[1] == "group":
        if len(parts) < 4:
            return await msg.answer(messages.get("incorrect_lang",  "❌ Неверный язык! Пожалуйста, выберите один из доступных языков:\n<b>РУССКИЙ, ТАДЖИКСКИЙ, АНГЛИЙСКИЙ</b>.\n🔹 Пример: <code>/set_lang РУССКИЙ</code>"), show_alert=True, parse_mode="HTML")
        group_id, code = parts[2], parts[3]
        users.set_lang(group_id, code)
        messages = (getattr(bot, "context", {}) or {}).get("messages", {}).get(code, {})
        await msg.message.edit_text(messages.get("lang_is_set","✅ Язык установлен на {value}" ).format(value=LANGUAGES[code]), parse_mode="HTML")
        await bot.send_message(group_id, messages.get("lang_is_set","✅ Язык установлен на {value}" ).format(value=LANGUAGES[code]), parse_mode="HTML")
        return await msg.answer("OK")
    else:
        if len(parts) < 3:
            return await msg.answer(messages.get("incorrect_lang",
                                                 "❌ Неверный язык! Пожалуйста, выберите один из доступных языков:\n<b>РУССКИЙ, ТАДЖИКСКИЙ, АНГЛИЙСКИЙ</b>.\n🔹 Пример: <code>/set_lang РУССКИЙ</code>"),
                                    show_alert=True, parse_mode="HTML")
        code = parts[2]
        users.set_lang(str(msg.from_user.id), code)
        messages = (getattr(bot, "context", {}) or {}).get("messages", {}).get(code, {})
        await msg.message.edit_text(messages.get("lang_is_set", "✅ Язык установлен на {value}").format(value=LANGUAGES[code]), parse_mode="HTML")
        return await msg.answer("OK")
