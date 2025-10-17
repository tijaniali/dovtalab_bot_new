from dataclasses import dataclass, field
from typing import Dict, List, Any
from aiogram.enums import PollType
from aiogram import Bot
from utils.helpers import escape
import asyncio, logging, re
from config import CFG, AD
from services.scheduler import DailyStats
import time
from models.polls import PollRegistry, PollKind, PollInfo
from models.rating import RatingManager

russian_to_latin_map = {'А':'A','В':'B','С':'C','D':'D'}
superscript_map = {
    "0": "⁰",
    "1": "¹",
    "2": "²",
    "3": "³",
    "4": "⁴",
    "5": "⁵",
    "6": "⁶",
    "7": "⁷",
    "8": "⁸",
    "9": "⁹"
}

def normalize_answer(answer: str) -> str:
    return ''.join([russian_to_latin_map.get(c, c) for c in answer])

@dataclass
class QuizState:
    questions: List[dict]
    user_scores: Dict[str, Dict[str, Any]] = field(default_factory=dict)

@dataclass
class QuizManager:
    logger: logging.Logger
    ad: AD
    stats: DailyStats
    poll_registry: PollRegistry  # poll_id -> {chat_id, correct_option_id}
    active: Dict[int, QuizState] = field(default_factory=dict)     # chat_id -> QuizState

    def __post_init__(self):
        self.poll_registry.register_handler(PollKind.QUIZ, self._handle_poll)

    def is_running(self, chat_id: int) -> bool:
        return chat_id in self.active

    def start(self, chat_id: int, questions: List[dict]):
        self.active[chat_id] = QuizState(questions=questions)

    async def stop(self, chat_id: int):
        if chat_id in self.active:
            del self.active[chat_id]
            self.poll_registry.cleanup_by_owner(PollKind.QUIZ, chat_id)

    async def _handle_poll(self, poll_info: PollInfo, telegram_user: Any, is_correct: bool, option_ids: List[int], bot: Bot):
        """
        poll_info.owner_id == chat_id
        telegram_user expected to have properties: id, username, (optionally) full_name
        """
        chat_id = poll_info.owner_id
        user_id = int(getattr(telegram_user, "id", telegram_user))
        username = getattr(telegram_user, "username", None)
        full_name = getattr(telegram_user, "full_name", None)

        self.stats.add_player(int(user_id))
        st = self.active.get(chat_id)
        if not st:
            return None
        st.user_scores.setdefault(str(user_id), {"score": 0, "user_name": "", "full_name": ""})
        st.user_scores[str(user_id)]["user_name"] = username
        st.user_scores[str(user_id)]["full_name"] = full_name
        if is_correct:
            st.user_scores[str(user_id)]["score"] += 1
        return chat_id

    async def run_quiz(self, bot: Bot, chat_id: int, quiz_time: int, messages: dict):
        st = self.active.get(chat_id)
        if not st:
            return

        self.stats.inc_games()
        for i, q in enumerate(st.questions):
            if chat_id not in self.active:
                return  # остановлено
            try:
                print(q)
                options = list(q["answers"].keys())
                correct_answer = normalize_answer(q["CorrectAnswers"].upper())
                options_norm = [normalize_answer(o).upper() for o in options]

                if len(q["question"]) >= 299:
                    self.logger.error("Слишком длинный вопрос — пропущено")
                    continue

                f = False
                for opt in options:
                    if len(opt) >= 99:
                        f = True
                        self.logger.error(f"Слишком длинный вопрос — пропущено")
                if f:
                    continue

                if correct_answer not in options_norm:
                    self.logger.error("Правильный ответ не найден в вариантах — пропущено")
                    continue

                if "picture_id" in q:
                    if q["picture_id"]:
                        try:
                            await bot.send_photo(
                                chat_id=chat_id,
                                photo=q["picture_id"]
                            )
                            await asyncio.sleep(1)
                        except:
                            await bot.send_message(
                                CFG.ADMIN_ID,
                                f"⚠️ Не удалось отправить картинку для вопроса:\n{q['question']}"
                            )
                            continue

                correct_index = options_norm.index(correct_answer)
                try:
                    num = "".join(superscript_map[c] for c in q["number"])
                    poll_msg = await bot.send_poll(
                        chat_id,
                        f"[{i+1}/{len(st.questions)}]" + num + " " + q["question"],
                        list(q["answers"].values()),
                        type=PollType.QUIZ,
                        correct_option_id=correct_index,
                        is_anonymous=False,
                        open_period=False if quiz_time == 0 else quiz_time
                    )
                except Exception as e:
                    await bot.send_message(
                        CFG.ADMIN_ID,
                        f"<b>Не удалось отправить вопрос!</b>"
                        f"\n {q['question']} \n\n<b>Ошибка</b>"
                        f"\n<blockquote><code>{e}</code></blockquote>", parse_mode="HTML"
                    )
                    continue

                self.poll_registry.record_poll(
                    poll_id=poll_msg.poll.id,
                    kind=PollKind.QUIZ,
                    owner_id=chat_id,
                    target_user_id=None,
                    correct_option_id=poll_msg.poll.correct_option_id
                )

                await asyncio.sleep(30 if quiz_time == 0 else quiz_time)

                if chat_id not in self.active:
                    return  # остановлено
            except Exception as e:
                self.logger.error(f"Неожиданная ошибка в вопросе {i+1}, пропускаем: {e}")
                continue

        await self.send_results(bot, chat_id, messages)

    async def send_results(self, bot: Bot, chat_id: int, messages: dict):
        st = self.active.get(chat_id)
        if not st:
            return
        try:
            sorted_scores = sorted(st.user_scores.items(), key=lambda x: x[1]["score"], reverse=True)
            text = messages["quiz_res"]
            f = 1
            for idx, (uid, data) in enumerate(sorted_scores, start=1):
                if (idx > 1):
                    if int(data["score"]) != int(sorted_scores[idx - 2][1]["score"]):
                        f += 1
                if data["user_name"] and data["full_name"]:
                    user_disp = f"<a href='tg://user?id={uid}'>{escape(data['full_name'])}</a>"
                elif data["user_name"]:
                    user_disp = f"@{data['user_name']}"
                else:
                    user_disp = data["full_name"] or messages.get("unknown_user", "Unknown")
                num = f
                if (f == 1):
                    num = "🥇"
                elif (f == 2):
                    num = "🥈"
                elif (f == 3):
                    num = "🥉"
                text += messages["user_score"].format(num=num, user=user_disp, score=str(data["score"]))

            add_text = f"<blockquote>{self.ad.get_ad()}</blockquote>\n" if self.ad.get_ad() != " " else messages.get("default_ad", "").format(chat_link="@mmt_taj")
            text += "\n" + add_text

            from aiogram.types import LinkPreviewOptions
            await bot.send_message(
                chat_id, text, parse_mode="HTML",
                link_preview_options=LinkPreviewOptions(
                    url=self.ad.get_link()
                    if self.ad.get_link()
                       or self.ad.get_link() != " "
                    else None,
                    prefer_small_media=True)
            )
        except Exception as e:
            self.logger.error(f"Ошибка при отправке результатов: {e}")
        finally:
            self.poll_registry.cleanup_by_owner(PollKind.QUIZ, chat_id)
            del self.active[chat_id]

#ДУЭЛь
@dataclass
class DuelState:
    players: Dict[int, dict]
    questions: List[dict]
    current_q: int = 0
    answered: Dict[int, bool] = field(default_factory=dict)
    isStarted: bool = False
    finished: bool = False

@dataclass
class DuelManager:
    stats: DailyStats
    poll_registry: PollRegistry
    ad: AD
    active_duels: Dict[int, DuelState] = field(default_factory=dict)
    user_duels: Dict[int, int] = field(default_factory=dict)
    invites: Dict[int, int] = field(default_factory=dict)

    def __post_init__(self):
        self.poll_registry.register_handler(PollKind.DUEL, self._handle_poll)

    def is_running(self, user_id: int) -> bool:
        if user_id in self.user_duels:
            duel_id = self.user_duels[user_id]
            if self.active_duels[duel_id].isStarted:
                return True
        return False

    def stop(self, user_id: int):
        duel_id = self.user_duels[user_id]
        if duel_id in self.active_duels:
            self.active_duels[duel_id].finished = True
            for uid in list(self.active_duels[duel_id].players.keys()):
                self.user_duels.pop(uid, None)
            self.poll_registry.cleanup_by_owner(PollKind.DUEL, duel_id)
            return True
        return False

    async def _handle_poll(self, poll_info: PollInfo,
                           telegram_user: Any,
                           is_correct: bool,
                           option_ids: List[int],
                           bot: Bot):
        """
        poll_info.owner_id == duel_id
        poll_info.target_user_id == uid who received the poll
        """
        duel_id = poll_info.owner_id
        user_id = int(getattr(telegram_user, "id", telegram_user))
        user_name = getattr(telegram_user, "username", None)
        full_name = getattr(telegram_user, "full_name", None)

        self.stats.add_player(int(user_id))
        st = self.active_duels.get(duel_id)
        if not st:
            return None

        st.players.setdefault(user_id, {
            "score": 0,
            "streak": 0,
            "user_name": user_name,
            "full_name": full_name
        })
        st.players[user_id]["user_name"] = user_name
        st.players[user_id]["full_name"] = full_name
        st.players[user_id]["streak"] = 0
        time_now = time.time()
        elapsed = time_now - poll_info.start_time
        if is_correct:
            if elapsed <= 5:
                score = 5
            else:
                seconds = max(0, min(elapsed, 30))  # ограничиваем 0–30
                # линейное уменьшение от 5 до 2
                score = 5 - (seconds - 5) * (3 / 25)

            score = round(score, 1)
            st.players[user_id]["score"] += score
            try:
                await bot.send_message(chat_id=user_id, text=f"Вы получили +{str(score)} баллов")
            except:
                print("Ошибка")
        st.answered[user_id] = True


    def create_invite(self, inviter_id:int,
                      questions: List[dict],
                      user_name:str|None, full_name:str|None):
        duel_id = inviter_id
        self.invites[inviter_id] = duel_id
        self.active_duels[duel_id] = DuelState(
            players={inviter_id: {
                "score": 0,
                "streak": 0,
                "user_name": user_name,
                "full_name": full_name
            }},
            questions=questions
        )
        self.user_duels[duel_id]=duel_id
        return duel_id

    def accept_invite(self, inviter_id:int,
                      opponent_id:int,
                      user_name:str|None,
                      full_name:str|None):

        duel_id = inviter_id
        if not duel_id or duel_id not in self.active_duels:
            return None
        st = self.active_duels[duel_id]
        st.players[opponent_id] = {
            "score": 0,
            "streak": 0,
            "user_name": user_name,
            "full_name": full_name
        }
        self.user_duels[opponent_id] = duel_id
        return duel_id

    async def run_duel(self, bot: Bot, duel_id:int):

        st = self.active_duels.get(duel_id)
        if not st:
            print("Нет активных дуэлей")
            return

        st.isStarted = True
        await asyncio.sleep(5)
        self.stats.inc_games()
        for i, q in enumerate(st.questions):
            options = list(q["answers"].keys())
            correct_answer = normalize_answer(q["CorrectAnswers"].upper())
            options_norm = [normalize_answer(o).upper() for o in options]

            if st.finished:
                break

            if len(q["question"]) >= 299:
                self.logger.error("Слишком длинный вопрос — пропущено")
                continue

            f = False
            for opt in options:
                if len(opt) >= 99:
                    f = True
                    self.logger.error(f"Слишком длинный вопрос — пропущено")
            if f:
                continue

            if correct_answer not in options_norm:
                self.logger.error("Правильный ответ не найден в вариантах — пропущено")
                continue

            st.answered = {uid: False for uid in list(st.players.keys())}

            # если есть картинка — отправляем каждому отдельно и в своём try/except
            if "picture_id" in q and q.get("picture_id"):
                for uid in list(st.players.keys()):
                    try:
                        await bot.send_photo(chat_id=uid, photo=q["picture_id"])
                        await asyncio.sleep(0.2)  # небольшая пауза между отправками
                    except Exception as e:
                        await bot.send_message(CFG.ADMIN_ID,
                                               f"⚠️ Не удалось отправить картинку пользователю {uid} для вопроса:\n{q['question']}\n{e}")

            # теперь отправляем опросы по отдельности
            correct_index = options_norm.index(correct_answer)
            poll_message_map = {}  # poll_id -> user_id (для удобства)
            for uid in list(st.players.keys()):
                try:
                    msg = await bot.send_poll(
                        chat_id=uid,
                        question=f"[{i + 1}/{len(st.questions)}] " + q["question"],
                        options=list(q["answers"].values()),
                        type=PollType.QUIZ,
                        correct_option_id=correct_index,
                        is_anonymous=False,
                        open_period=30
                    )
                    # msg — это Message; реальный Poll лежит в msg.poll
                    if not getattr(msg, "poll", None):
                        # на всякий случай — если библиотека вернула что-то неожиданное
                        await bot.send_message(CFG.ADMIN_ID, f"Не получил poll в ответе от send_poll для {uid}")
                        continue

                    poll_obj = msg.poll
                    self.poll_registry.record_poll(
                        poll_id=poll_obj.id,
                        kind=PollKind.DUEL,
                        owner_id=duel_id,
                        target_user_id=uid,
                        correct_option_id=poll_obj.correct_option_id
                    )
                    poll_message_map[poll_obj.id] = uid
                    # st.answered[uid] уже инициализирован ранее как False

                    await asyncio.sleep(0.15)  # чтобы не спамить API одновременно
                except Exception as e:
                    # логируем отдельно по пользователю — чтобы отправка другим не прервалась
                    await bot.send_message(CFG.ADMIN_ID,
                                           f"<b>Не удалось отправить вопрос пользователю {uid}!</b>\n"
                                           f"{q['question']}\n\n<b>Ошибка</b>\n<code>{e}</code>", parse_mode="HTML")
                    # можно пометить пользователя как пропустившего (или оставить st.answered[uid]=False)
                    # и продолжить отправлять другим

            # ждём ответов — либо оба ответили, либо timeout 30 сек
            try:
                await asyncio.wait_for(wait_for_answers(st), timeout=30)
            except asyncio.TimeoutError:
                # обработка таймаута (как у вас)
                for uid, answered in st.answered.items():
                    if not answered:
                        await bot.send_message(uid, "Время вышло")
                        st.players[uid]["streak"] += 1
                    if st.players[uid]["streak"] >= 2:
                        await bot.send_message(uid, "Вы пропустили двух вопросов подряд, игра закончена")
                        st.finished = True
                        break

        await self.send_result(bot, st, duel_id)

    async def send_result(self, bot:Bot, st, duel_id):
        results = sorted(st.players.items(), key=lambda x: x[1]["score"], reverse=True)
        if len(results) < 2:
            winner = results[0]
            text = f"🏆 Победитель по умолчанию: {winner[1]['full_name']} ({winner[1]['score']} баллов)"
        else:
            winner = results[0]
            loser = results[1]
            text = f"🏆 Победитель: {winner[1]['full_name']} ({winner[1]['score']} баллов)\n" \
                    f"❌ Проигравший: {loser[1]['full_name']} ({loser[1]['score']} баллов)"

        add_text = f"<blockquote>{self.ad.get_ad()}</blockquote>\n" if self.ad.get_ad() != " " else "<blockquote>Наш чат: @mmt_taj</blockquote>"
        text += "\n" + add_text

        for uid in st.players:
            await bot.send_message(uid, text)
        # очистка polls_info по duel_id
        self.poll_registry.cleanup_by_owner(PollKind.DUEL, duel_id)
        if duel_id in self.active_duels:
            self.active_duels[duel_id].finished = True
            for uid in list(self.active_duels[duel_id].players.keys()):
                self.user_duels.pop(uid, None)
            self.poll_registry.cleanup_by_owner(PollKind.DUEL, duel_id)


async def wait_for_answers(st):
    while not all(st.answered.values()) and not st.finished:
        await asyncio.sleep(0.5)
    return