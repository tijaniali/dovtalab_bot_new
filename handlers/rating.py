from aiogram import types
from aiogram.filters import Command
from aiogram.types import LinkPreviewOptions, InlineKeyboardMarkup, InlineKeyboardButton

from bot import dp, bot
from models.rating import RatingManager
from models.user import UserManager
from utils.helpers import escape
from config import AD

rating: RatingManager | None = None
users: UserManager | None = None
ad: AD | None = None

def setup(_rating: RatingManager,
          _users: UserManager, _ad: AD):
    global rating, users, ad
    rating = _rating
    users = _users
    ad = _ad

@dp.message(Command("rating"))
async def global_rating(msg: types.Message):
    assert rating and users
    lang_key = str(msg.from_user.id)
    lang = users.get_lang(lang_key, "tg")
    messages = (getattr(bot, "context", {}) or {}).get("messages", {}).get(lang, {})

    if not users.started(str(msg.from_user.id)):
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text=messages.get("start_bot", "Активировать бота"),
                                                   url="https://t.me/Dovtalabbot?start=active_for_quiz:None")]])
        return await msg.reply(messages.get("bot_inactive", "Бот не активирован"), reply_markup=kb)

    sorted_scores = sorted(rating.global_scores.items(), key=lambda x: x[1]["score"], reverse=True)
    text = messages.get("top_users", "<b>Топ игроков</b>\n")
    f = 1
    for i, (uid, data) in enumerate(sorted_scores[:10], start=1):
        if (i > 1):
            if int(data["score"]) != int(sorted_scores[i - 2][1]["score"]):
                f += 1
        if data.get("user_name") and data.get("full_name"):
            user_disp = f"<a href='tg://user?id={uid}'>{escape(data['full_name'])}</a>"
        elif data.get("user_name"):
            user_disp = f"@{data['user_name']}"
        else:
            user_disp = data.get("full_name") or messages.get("unknown_user", "Unknown")
        num = f
        if (f == 1):
            num = "🥇"
        elif (f ==2):
            num = "🥈"
        elif (f ==3):
            num = "🥉"
        text += messages.get("user_score", "{num}. {user} — {score}\n").format(num=num, user=user_disp,
                                                                               score=int(data["score"]))

    text += messages.get("total_users", "\nВсего пользователей: {value}").format(value=len(rating.global_scores))
    # find current user rank
    rank = None
    for i, (uid, data) in enumerate(sorted_scores, start=1):
        if uid == str(msg.from_user.id):
            rank = i
            text += messages.get("your_score", "\nВаше место: {i}, очки: {score}\n").format(i=i, score=int(data["score"]))
            break
    text +=  "<blockquote>" + ad.get_ad().strip() + "</blockquote>\n"
    await msg.reply(text + "\u200B\n\n", parse_mode="HTML",
                    link_preview_options=LinkPreviewOptions(
                        url=ad.get_link()
                        if ad.get_link()
                           or ad.get_link() != " "
                        else None,
                        prefer_small_media=True)
                    )

@dp.message(Command("group_rating"))
async def group_rating(msg: types.Message):
    assert rating and users
    lang_key = str(msg.from_user.id)
    lang = users.get_lang(lang_key, "tg")
    messages = (getattr(bot, "context", {}) or {}).get("messages", {}).get(lang, {})
    if (msg.chat.type == "private"):
        return await msg.reply(messages.get("gr_rating_error", "Групповые рейтинги доступны только в группах!"), parse_mode="HTML")

    if not users.started(str(msg.from_user.id)):
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text=messages.get("start_bot", "Активировать бота"),
                                                   url="https://t.me/Dovtalabbot?start=active_for_quiz:None")]])
        return await msg.reply(messages.get("bot_inactive", "Бот не активирован"), reply_markup=kb)

    sorted_scores = sorted(rating.group_scores[str(msg.chat.id)].items(), key=lambda x: x[1]["score"], reverse=True)

    text = messages.get("top_users", "<b>Топ игроков</b>\n")

    f = 1
    for i, (uid, data) in enumerate(sorted_scores[:10], start=1):
        if (i > 1):
            if int(data["score"]) != int(sorted_scores[i - 2][1]["score"]):
                f += 1
        if data.get("user_name") and data.get("full_name"):
            user_disp = f"<a href='tg://user?id={uid}'>{escape(data['full_name'])}</a>"
        elif data.get("user_name"):
            user_disp = f"@{data['user_name']}"
        else:
            user_disp = data.get("full_name") or messages.get("unknown_user", "Unknown")
        num = f
        if (f == 1):
            num = "🥇"
        elif (f == 2):
            num = "🥈"
        elif (f == 3):
            num = "🥉"
        text += messages.get("user_score", "{num}. {user} — {score}\n").format(num=num, user=user_disp,
                                                                               score=int(data["score"]))

    text += messages.get("total_users", "\nВсего пользователей: {value}").format(value=len(rating.group_scores[str(msg.chat.id)]))
    # find current user rank
    rank = None
    for i, (uid, data) in enumerate(sorted_scores, start=1):
        if uid == str(msg.from_user.id):
            rank = i
            text += messages.get("your_score", "\nВаше место: {i}, очки: {score}\n").format(i=i,
                                                                                            score=int(data["score"]))
            break
    text += "<blockquote>" + ad.get_ad().strip() + "</blockquote>\n"
    await msg.reply(text + "\u200B\n\n", parse_mode="HTML",
                    link_preview_options=LinkPreviewOptions(
                        url=ad.get_link()
                        if ad.get_link()
                           or ad.get_link() != " "
                        else None,
                        prefer_small_media=True)
                    )

