import random, logging, asyncio
from gc import callbacks

from aiogram import types, F
from aiogram.filters import Command, CommandObject
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ChosenInlineResult
from aiogram.types import InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.deep_linking import create_start_link
from bot import dp, bot
from models.quiz import QuizManager, DuelManager
from models.rating import RatingManager
from models.user import UserManager
from models.polls import PollRegistry
from data.loader import save_post
from config import  CFG

logger = logging.getLogger(__name__)

# Dependency container (simple)
quiz_manager: QuizManager | None = None
duel_manager: DuelManager | None = None
rating: RatingManager | None = None
users: UserManager | None = None
poll_registry: PollRegistry | None = None
questions_map: dict[str, list[dict]] = {}
questions_index: dict[str, dict[str, dict]] = {}
topics = {
    "БИОЛОГИЯ":"БИОЛОГИЯ",
    "BIOLOGY":"БИОЛОГИЯ",
    "BIOLOGIYA":"БИОЛОГИЯ",
    "ГЕОГРАФИЯ":"ГЕОГРАФИЯ",
    "GEOGRAPHY":"ГЕОГРАФИЯ",
    "GEOGRAFIYA":"ГЕОГРАФИЯ",
    "ИСТОРИЯ":"ИСТОРИЯ",
    "HISTORY":"ИСТОРИЯ",
    "ТАРИХ":"ИСТОРИЯ",
    "ТАЪРИХ":"ИСТОРИЯ",
    "TARIX":"ИСТОРИЯ",
    "ЛИТЕРАТУРА":"ЛИТЕРАТУРА",
    "АДАБИЁТ":"ЛИТЕРАТУРА",
    "АДАБИЙОТ":"ЛИТЕРАТУРА",
    "АДАБИЕТ":"ЛИТЕРАТУРА",
    "LITERATURE":"ЛИТЕРАТУРА",
    "ADABIYOT":"ЛИТЕРАТУРА",
    "ПРАВО":"ПРАВО",
    "ПРАВА":"ПРАВО",
    "LAW":"ПРАВО",
    "ХУКУК":"ПРАВО",
    "ХУҚУҚ":"ПРАВО",
    "ҲУҚУҚ":"ПРАВО",
    "HUQUQ":"ПРАВО",
    "ЯЗЫК":"ЯЗЫК",
    "ЗАБОН":"ЯЗЫК",
    "LANGUAGE":"ЯЗЫК",
    "TIL":"ЯЗЫК",
    "ДИПЛОМАТИЯ":"ДИПЛОМАТИЯ"
}

def setup(_quiz: QuizManager,
          _duel: DuelManager,
          _rating: RatingManager,
          _users: UserManager,
          _poll_registry: PollRegistry,
          _questions: dict):
    global quiz_manager, duel_manager,rating, users, poll_registry, questions_map
    quiz_manager = _quiz
    duel_manager = _duel
    rating = _rating
    users = _users
    poll_registry = _poll_registry
    questions_map = _questions
    for sub, questions in questions_map.items():
        questions_index[sub] = {}
        for q in questions:
            questions_index[sub][q["number"]] = q

@dp.message(Command("start"))
async def start(msg: types.Message, command: CommandObject):
    assert quiz_manager and rating and users
    users.ensure(msg.chat.id,
                 is_group=(msg.chat.type != "private"),
                 title=getattr(msg.chat, "title", None),
                 username=getattr(msg.from_user, "username", None),
                 first_name=getattr(msg.from_user, "first_name", None),
                 is_started=True)

    lang = users.get_lang(str(msg.chat.id) if msg.chat.type != "private" else str(msg.from_user.id), "tg")
    # messages dictionary is supposed to be loaded in main and passed via context; for brevity, store in bot['messages']
    messages = (getattr(bot, "context", {}) or {}).get("messages", {}).get(lang, {})

    if command.args and command.args.startswith("active_for_duel"):
        _, inline_message_id = command.args.split(":", 1)
        await msg.reply("Бот активирован, можете попробовать начать дуэль ✅")
        try:
            await bot.edit_message_text(
                inline_message_id=inline_message_id,
                text=f"{msg.from_user.full_name} активировал бота, можете пригласить в дуль заново!",
                reply_markup=None
            )
        except Exception as e:
            await bot.send_message(CFG.ADMIN_ID, f"Ошибка <blockquote>{e}</blockquote>", parse_mode="HTML")
        return
    elif command.args and command.args.startswith("active_for_quiz"):
        return await msg.reply(messages.get("success_activate", "✅ Бот успешно активирован! Теперь можно вернуться в чат и начать викторину."))
    else:
        await msg.reply(f"""<b>🎓 Омодагӣ барои НМТ (ММТ) ҳеҷ гоҳ ин қадар осон набуд!</b>
Дар боти мо шумо метавонед бо викторинаҳо таҳсил кунед. Ҳамааш хеле осон аст:
➡ Командаро ворид кунед <code>/start_quiz [номи фан]</code>

<b>📚 Фанҳои дастрас:</b>
Биология 🧬 | Таърих 🏛 | Ҷуғрофия 🌍 | Ҳуқуқ ⚖ | Забон ✏ | Адабиёт 📖

🎉 Мехоҳед таҳсилро шавқовартар кунед? Ботро ба гурӯҳи худ илова кунед ва бо дӯстон рақобат кунед!\n
<b>Ё ба гурӯҳи мавҷудаи мо ҳамроҳ шавед: @mmt_taj</b>""", parse_mode="HTML")


@dp.message(Command("start_quiz"))
async def start_quiz(msg: types.Message):
    assert quiz_manager and rating and users
    users.ensure(msg.chat.id,
                 is_group=(msg.chat.type != "private"),
                 title=getattr(msg.chat, "title", None),
                 username=getattr(msg.from_user, "username", None),
                 first_name=getattr(msg.from_user, "first_name", None),
                 is_started=True)

    lang = users.get_lang(str(msg.chat.id) if msg.chat.type != "private" else str(msg.from_user.id), "tg")
    # messages dictionary is supposed to be loaded in main and passed via context; for brevity, store in bot['messages']
    messages = (getattr(bot, "context", {}) or {}).get("messages", {}).get(lang, {})

    if not users.started(str(msg.chat.id) if msg.chat.type != "private" else str(msg.from_user.id)):
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=messages.get("start_bot", "Активировать бота"),
                                                                         url="https://t.me/Dovtalabbot?start=active_for_quiz:None")]])
        return await msg.reply(messages.get("bot_inactive", "Бот не активирован"), reply_markup=kb)

    settings = users.get_settings(str(msg.chat.id))
    num_questions = settings["num_questions"]
    quiz_time = settings["quiz_time"]

    if quiz_manager.is_running(msg.chat.id):
        return await msg.reply(messages.get("quiz_alr_started", "Викторина уже идёт"), parse_mode="HTML")
    if duel_manager.is_running(msg.chat.id):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"Остановить дуэль",
                                  callback_data=f"stop_duel:{msg.chat.id}")]
        ])
        return await msg.reply("У вас есть активный дуль, завершите его", reply_markup=kb)

    parts = msg.text.split(maxsplit=1)
    topic = parts[1].upper() if len(parts) > 1 else None
    if topic and topic in topics:
        selected = random.sample(questions_map[topics.get(topic)], num_questions) if len(questions_map[topics.get(topic)]) >= num_questions else questions_map[topic[1]][:]
        quiz_manager.start(msg.chat.id, selected)
        await msg.reply(messages.get("quiz_start", "Старт!").format(num_questions=num_questions, quiz_time=quiz_time), parse_mode="HTML")
        asyncio.create_task(quiz_manager.run_quiz(bot, msg.chat.id, quiz_time, messages))
    else:
        return await msg.reply(messages.get("topic_error", "Неверная тема"), parse_mode="HTML")

@dp.message(Command("stop_quiz"))
async def stop_quiz(msg: types.Message):
    assert quiz_manager and rating and users
    users.ensure(msg.chat.id,
                 is_group=(msg.chat.type != "private"),
                 title=getattr(msg.chat, "title", None),
                 username=getattr(msg.from_user, "username", None),
                 first_name=getattr(msg.from_user, "first_name", None),
                 is_started=True)

    lang = users.get_lang(str(msg.chat.id) if msg.chat.type != "private" else str(msg.from_user.id), "tg")
    messages = (getattr(bot, "context", {}) or {}).get("messages", {}).get(lang, {})
    if (users.get_type(str(msg.chat.id)) != "private"):
        chat_member = await bot.get_chat_member(msg.chat.id, msg.from_user.id)
        if chat_member.status not in ["administrator", "creator"]:
            return await msg.reply(messages.get("quiz_stp_not_admin"), parse_mode="HTML")
    if quiz_manager.is_running(msg.chat.id):
        await quiz_manager.send_results(bot, msg.chat.id,messages)
        quiz_manager.stop(msg.chat.id)
        return await msg.reply(messages.get("quiz_stopped"), parse_mode="HTML")
    return await msg.reply(messages.get("not_actv_quiz"), parse_mode="HTML")

@dp.poll_answer()
async def on_poll_answer(ans: types.PollAnswer):
    assert poll_registry
    poll_id = ans.poll_id
    telegram_user = ans.user
    option_ids = ans.option_ids
    await poll_registry.dispatch(poll_id=poll_id,
                                 telegram_user=telegram_user,
                                 chat=ans.voter_chat,
                                 option_ids=option_ids,
                                 bot=bot)

@dp.message(Command("set_picture"))
async def set_picture(msg: types.Message):
    assert quiz_manager and rating and users
    users.ensure(msg.chat.id,
                 is_group=(msg.chat.type != "private"),
                 title=getattr(msg.chat, "title", None),
                 username=getattr(msg.from_user, "username", None),
                 first_name=getattr(msg.from_user, "first_name", None),
                 is_started=True)

    lang = users.get_lang(str(msg.chat.id) if msg.chat.type != "private" else str(msg.from_user.id), "tg")
    messages = (getattr(bot, "context", {}) or {}).get("messages", {}).get(lang, {})
    if (str(msg.from_user.id) != CFG.ADMIN_ID):
        return await msg.reply(messages.get("not_admin",  "Эта настройка доступна только Админстратору!"),
                               parse_mode="HTML")
    if (not msg.photo):
        return await msg.reply(messages.get("no_image",  "⚠\uFE0F Прикрепите фото к команде!"),
                               parse_mode="HTML")
    args = msg.caption.split()
    if len(args) != 3:
        return await msg.reply(messages.get("pic_error", "❗ Формат: /set_picture [предмет] [номер]"),
                               parse_mode="HTML")
    command, subject, q_num = args
    q_num = int(q_num)
    subject = subject.upper()
    if (subject not in topics):
        return await msg.reply(
            messages.get("topic_error", "Неправильное название викторины"),
            parse_mode="HTML"
        )
    photo = msg.photo[-1].file_id
    channel_post = await bot.send_photo(
        chat_id=CFG.CHANNEL_ID,
        photo=photo,
        caption=f"📌 Ресурс: <b>{topics.get(subject)} #{q_num}</b>",
        parse_mode="HTML"
    )

    pic_id = channel_post.photo[-1].file_id
    q = questions_index[topics.get(subject)].get(str(q_num))
    if not q:
        await bot.delete_message(CFG.CHANNEL_ID, channel_post.message_id)
        return await msg.reply(messages.get("quiz_not_finde", "Вопрос   {subject} | {q_num}  не найдено!").format(subject=topics.get(subject),q_num=q_num), parse_mode="HTML")
    q["picture_id"] = pic_id
    if (save_post(topics.get(subject), questions_map[topics.get(subject)])):
        return await msg.reply(
            messages.get("picture_is_set", "✅ Картинка сохранена и привязана к вопросу {q_num}").format(q_num=q_num),
            parse_mode="HTML")
    else:
        await msg.reply("Ошибка!", parse_mode="HTML")
        await bot.delete_message(CFG.CHANNEL_ID, channel_post.message_id)

@dp.message(Command("del_picture"))
async def del_picture(msg: types.Message):
    assert quiz_manager and rating and users
    users.ensure(msg.chat.id,
                 is_group=(msg.chat.type != "private"),
                 title=getattr(msg.chat, "title", None),
                 username=getattr(msg.from_user, "username", None),
                 first_name=getattr(msg.from_user, "first_name", None),
                 is_started=True)

    lang = users.get_lang(str(msg.chat.id) if msg.chat.type != "private" else str(msg.from_user.id), "tg")
    messages = (getattr(bot, "context", {}) or {}).get("messages", {}).get(lang, {})
    if (str(msg.from_user.id) != CFG.ADMIN_ID):
        return await msg.reply(messages.get("not_admin", "Эта настройка доступна только Админстратору!"),
                               parse_mode="HTML")
    args = msg.text.split()
    if len(args) != 3:
        return await msg.reply(messages.get("del_pic_error", "❗ Формат: /del_picture [предмет] [номер]"),
                               parse_mode="HTML")
    command, subject, q_num = args
    subject = subject.upper()
    q_num = int(q_num)
    if (subject not in topics):
        return await msg.reply(
            messages.get("topic_error", "Неправильное название викторины"),
            parse_mode="HTML"
        )
    channel_post = await bot.send_message(
        chat_id=CFG.CHANNEL_ID,
        text=f"📌 Удаление ресурса: {topics.get(subject)} #{q_num}",
        parse_mode = "HTML"
    )
    q = questions_index[topics.get(subject)].get(str(q_num))
    if not q:
        await bot.delete_message(CFG.CHANNEL_ID, channel_post.message_id)
        return await msg.reply(messages.get("quiz_not_finde", "Вопрос   {subject} | {q_num}  не найдено!").format(subject=topics.get(subject),q_num=q_num), parse_mode="HTML")
    q["picture_id"] = None
    if (save_post(topics.get(subject), questions_map[topics.get(subject)])):
        return await msg.reply(
            messages.get("pic_is_del", "Картинка вопроса {subject} | {q_num} удалена!").format(q_num=q_num,
                                                                                               subject=topics.get(subject)),
            parse_mode="HTML")
    else:
        await msg.reply("Ошибка!", parse_mode="HTML")
        await bot.delete_message(CFG.CHANNEL_ID, channel_post.message_id)


@dp.message(Command("get_quiz"))
async def get_quiz(msg: types.Message):
    assert quiz_manager and rating and users
    users.ensure(msg.chat.id,
                 is_group=(msg.chat.type != "private"),
                 title=getattr(msg.chat, "title", None),
                 username=getattr(msg.from_user, "username", None),
                 first_name=getattr(msg.from_user, "first_name", None),
                 is_started=True)

    lang = users.get_lang(str(msg.chat.id) if msg.chat.type != "private" else str(msg.from_user.id), "tg")
    messages = (getattr(bot, "context", {}) or {}).get("messages", {}).get(lang, {})
    args = msg.text.split()
    if len(args) != 3:
        return await msg.reply(messages.get("get_quiz_error","❗ Формат: /get_quiz [предмет] [номер]"), parse_mode="HTML")
    command, subject, q_num = args
    q_num = int(q_num)
    subject = subject.upper()
    if (subject not in topics):
        return await msg.reply(
            messages.get("topic_error", "Неправильное название викторины"),
            parse_mode="HTML"
        )
    q = questions_index[topics.get(subject)].get(str(q_num))
    if not q:
        return await msg.reply(messages.get("quiz_not_finde", "Вопрос   {subject} | {q_num}  не найдено!").format(subject=topics.get(subject),q_num=q_num), parse_mode="HTML")
    if not users.started(str(msg.chat.id) if msg.chat.type != "private" else str(msg.from_user.id)):
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text=messages.get("start_bot", "Активировать бота"),
                                                   url="https://t.me/Dovtalabbot?start=command_start")]])
        return await msg.reply(messages.get("bot_inactive", "Бот не активирован"), reply_markup=kb, parse_mode="HTML")

    settings = users.get_settings(str(msg.chat.id))
    num_questions = settings["num_questions"]
    quiz_time = 1

    if quiz_manager.is_running(msg.chat.id):
        return await msg.reply(messages.get("quiz_alr_started", "Викторина уже идёт"), parse_mode="HTML")
    try:
        selected = []
        selected.append(q)
        quiz_manager.start(msg.chat.id, selected)
        await msg.reply(messages.get("quiz_start", "Старт!").format(num_questions=num_questions, quiz_time=quiz_time), parse_mode="HTML")
        asyncio.create_task(quiz_manager.run_quiz(bot, msg.chat.id, quiz_time, messages))
    except Exception as e:
        await bot.send_message(
            CFG.ADMIN_ID,
            "Ошибка при получении вопроса",
             parse_mode = "HTML"
        )


@dp.callback_query(F.data.startswith("stop_quiz:"))
async def stop_quiz(callback: CallbackQuery):
    _, from_user = callback.data.split(":", 1)
    user_id = callback.from_user.id
    from_user = int(from_user)
    if user_id != from_user:
        return await callback.answer("Ты не можешь остановить чужую викторину", show_alert=True)
    if not quiz_manager.is_running(user_id):
        if callback.message:
            await bot.edit_message_text(
                chat_id=callback.message.chat.id,
                message_id=callback.message.message_id,
                text=f"У вас нет активной викторины",
                reply_markup=None
            )
        elif callback.inline_message_id:
            await bot.edit_message_text(
                inline_message_id=callback.inline_message_id,
                text=f"У вас нет активной викторины",
                reply_markup=None
            )
        else:
            # fallback, например просто уведомление
            await callback.answer("Сообщение недоступно", show_alert=True)
        return

    quiz_manager.stop(user_id)
    if callback.message:
        await bot.edit_message_text(
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            text=f"Викторина остановлена",
            reply_markup=None
        )
    elif callback.inline_message_id:
        await bot.edit_message_text(
            inline_message_id=callback.inline_message_id,
            text=f"Викторина остановлена",
            reply_markup=None
        )
    else:
        # fallback, например просто уведомление
        await callback.answer("Сообщение недоступно", show_alert=True)
#ДУЭЛЬ

@dp.inline_query()
async def inline_duel(query: types.InlineQuery):
    duel_commands = ["DUEL", "ДУЭЛЬ", "ДУЭЛ", "ДУЕЛ"]
    duel_topics = {
        "БИОЛОГИЯ": "БИОЛОГИЯ",
        "BIOLOGY": "БИОЛОГИЯ",
        "ГЕОГРАФИЯ": "ГЕОГРАФИЯ",
        "GEOGRAPHY": "ГЕОГРАФИЯ",
        "ИСТОРИЯ": "ИСТОРИЯ",
        "HISTORY": "ИСТОРИЯ",
        "ТАЪРИХ": "ИСТОРИЯ",
        "ЛИТЕРАТУРА": "ЛИТЕРАТУРА",
        "АДАБИЁТ": "ЛИТЕРАТУРА",
        "LITERATURE": "ЛИТЕРАТУРА",
        "ПРАВО": "ПРАВО",
        "LAW": "ПРАВО",
        "ХУКУК": "ПРАВО",
        "ЯЗЫК": "ЯЗЫК",
        "ЗАБОН": "ЯЗЫК",
        "LANGUAGE": "ЯЗЫК",
        "ДИПЛОМАТИЯ": "ДИПЛОМАТИЯ"
    }
    user_id = query.from_user.id
    if quiz_manager.is_running(user_id):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"Остановить викторину",
                                  callback_data=f"stop_quiz:{user_id}")]
        ])
        res = []
        res.append(
            InlineQueryResultArticle(
                id=f"err:has_active_quiz",
                title="У вас есть активная викторина",
                input_message_content=InputTextMessageContent(message_text="Вы можете остановить активнюю викторину"),
                reply_markup=kb
            )
        )
        await  query.answer(results=res, cache_time=0)
        return
    if duel_manager.is_running(user_id):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"Остановить дуэль",
                                  callback_data=f"stop_duel:{user_id}")]
        ])
        res = []
        res.append(
            InlineQueryResultArticle(
                id=f"err:has_active_duel",
                title="У вас есть активный дуэль",
                input_message_content=InputTextMessageContent(message_text="Вы можете остановить активный дуэль"),
                reply_markup=kb
            )
        )
        await  query.answer(results=res, cache_time=0)
        return
        return
    items = query.query.split(maxsplit=2)
    if (len(items)<2):
        return
    command = items[0].strip().upper()
    topic = items[1].strip().upper()
    if command not in duel_commands:
        return

    matches = [duel_topics[w] for w in duel_topics if topic in w]
    results = []

    if len(matches) < 1:
        await query.answer(results=[],
                           cache_time=0,
                           is_personal=True,
                           switch_pm_text="Предмет не найден!",
                           switch_pm_parameter="no_results")
        return

    for idx, word in enumerate(matches):
        text = f"⚔️ Приглашение на дуэль по теме: {word}!"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"Принять дуэль по {word}",
                                  callback_data=f"accept_duel:{user_id}:{word}")]
        ])
        results.append(
            InlineQueryResultArticle(
                id=f"duel:{word}",
                title=f"Пригласить в дуэль по {word}",
                description=f"Отправь другу приглашение по {word}",
                input_message_content=InputTextMessageContent(message_text=text),
                reply_markup = kb
            )
        )
    await query.answer(results=results, cache_time=0)
    return

@dp.chosen_inline_result()
async def invite_duel(chosen_result: ChosenInlineResult):
    assert users
    print("Обработан инлайнчуз")
    user_id = chosen_result.from_user.id
    user_name = chosen_result.from_user.username
    first_name = chosen_result.from_user.first_name
    result_id = chosen_result.result_id
    try:
        await bot.get_chat(user_id)
        if not users.started(str(chosen_result.from_user.id)):
            users.ensure(chat_id=user_id,
                         is_group=False,
                         title=None,
                         username=user_name,
                         first_name=first_name,
                         is_started=True)
    except:
        print("forbidden")

    if not users.started(str(chosen_result.from_user.id)):
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="Активировать бота",
                                                   url=f"https://t.me/Dovtalabbot?start=active_for_duel:{chosen_result.inline_message_id}")]])
        return await bot.edit_message_text(
            inline_message_id=chosen_result.inline_message_id,
            text=f"У {first_name if first_name else user_name} бот неактивирован",
            reply_markup=kb
        )
    if result_id.startswith("duel:"):
        topic = result_id.split(":", 1)[1]
        if topic not in topics:
            await bot.edit_message_text(
                inline_message_id=chosen_result.inline_message_id,
                text="Предмет не найден!",
                reply_markup=None
            )
        q_list = questions_map[topics.get(topic)]
        selected = random.sample(q_list, min(10, len(q_list)))

        duel_manager.create_invite(inviter_id=int(user_id),
                                   questions=selected,
                                   user_name=user_name,
                                   full_name=first_name)
        print("Дуэль создан")


@dp.callback_query(F.data.startswith("accept_duel:"))
async def accept_duel(callback: CallbackQuery):
    _, inviter_id, topic = callback.data.split(":", 2)
    inviter_id = int(inviter_id)
    opponent_id = int(callback.from_user.id)
    user_name = callback.from_user.username
    first_name = callback.from_user.first_name
    try:
        await bot.get_chat(opponent_id)
        if not users.started(opponent_id):
            users.ensure(chat_id=opponent_id,
                         is_group=False,
                         title=None,
                         username=user_name,
                         first_name=first_name,
                         is_started=True)
    except:
        print("forbidden")

    if not users.started(str(callback.from_user.id)):
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="Активировать бота",
                                                   url=f"https://t.me/Dovtalabbot?start=active_for_duel:{callback.inline_message_id}")]])
        return await bot.edit_message_text(
            inline_message_id=callback.inline_message_id,
            text=f"У {first_name if first_name else user_name} бот неактивирован",
            reply_markup=kb
        )

    if inviter_id == opponent_id:
        return await callback.answer("Ты не можешь принять свою дуэль!", show_alert=True)

    if quiz_manager.is_running(opponent_id):
        return await bot.edit_message_text(inline_message_id=callback.inline_message_id,
                                           text=f"У вас уже начата викторина, завершите её и отправьте новый приглашение в дуэль",
                                           reply_markup=None)
    if duel_manager.is_running(opponent_id):
        return await bot.edit_message_text(inline_message_id=callback.inline_message_id,
                                           text=f"У вас уже начата дуэль, завершите его и отправьте новый приглашение в дуэль",
                                           reply_markup=None)
    if quiz_manager.is_running(inviter_id):
        return await bot.edit_message_text(inline_message_id=callback.inline_message_id,
                                           text=f"У пригласившего уже начата викторина, вы можете отправить новая приглашения в дуэль",
                                           reply_markup=None)
    if duel_manager.is_running(inviter_id):
        return await bot.edit_message_text(inline_message_id=callback.inline_message_id,
                                           text=f"У пригласившего уже начат дуэль, вы можете отправить новая приглашения в дуэль",
                                           reply_markup=None)

    if topic not in topics:
        await bot.edit_message_text(
            inline_message_id=callback.inline_message_id,
            text="Предмет не найден!",
            reply_markup=None
        )
    try:
        duel_manager.accept_invite(inviter_id=inviter_id,
                                   opponent_id=opponent_id,
                                   user_name=user_name,
                                   full_name=first_name)
    except:
        bot.send_message(CFG.ADMIN_ID, "ОШИБКА В СОЗДАНИ ДУЭЛЬЯ")
        bot.edit_message_text(inline_message_id=callback.inline_message_id,
                              text="Неизвестная ошибка",
                              reply_markup=None)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Перейти в бота", url="https://t.me/Dovtalabbot")]
    ])
    await bot.edit_message_text(inline_message_id=callback.inline_message_id,
                                text=f"✅ {first_name if first_name else user_name} принял вызов!",
                                reply_markup=kb)
    for uid in [inviter_id, opponent_id]:
        await bot.send_message(uid, "🔥 Дуэль началась! Готовься к вопросам...")

    await duel_manager.run_duel(bot=bot, duel_id=inviter_id)
    print("Дуэль принять")

@dp.callback_query(F.data.startswith("stop_duel:"))
async def stop_duel(callback: CallbackQuery):
    _, from_user = callback.data.split(":", 1)
    user_id = callback.from_user.id
    from_user = int(from_user)
    print(user_id, from_user)
    if user_id != from_user:
        return await callback.answer("Ты не можешь остановить чужой дуэль", show_alert=True)
    if not duel_manager.is_running(user_id):
        if callback.message:
            await bot.edit_message_text(
                chat_id=callback.message.chat.id,
                message_id=callback.message.message_id,
                text=f"У вас нет активный дуэль",
                reply_markup=None
            )
        elif callback.inline_message_id:
            await bot.edit_message_text(
                inline_message_id=callback.inline_message_id,
                text=f"У вас нет активный дуэль",
                reply_markup=None
            )
        else:
            await callback.answer("Сообщение недоступно", show_alert=True)
        return

    duel_manager.stop(user_id)
    if callback.message:
        await bot.edit_message_text(
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            text="Дуэль остановлен",
            reply_markup=None
        )
    elif callback.inline_message_id:
        await bot.edit_message_text(
            inline_message_id=callback.inline_message_id,
            text="Дуэль остановлен",
            reply_markup=None
        )
    else:
        await callback.answer("Сообщение недоступно", show_alert=True)