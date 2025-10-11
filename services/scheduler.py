import asyncio
import pytz
from datetime import datetime, timedelta
from aiogram import Bot

TAJIKISTAN_TZ = pytz.timezone("Asia/Dushanbe")

class DailyStats:
    def __init__(self):
        self.games_started = 0
        self.players = set()

    def inc_games(self):
        self.games_started += 1

    def add_player(self, user_id: int):
        self.players.add(user_id)

    def get_stats(self):
        now = datetime.now(pytz.timezone('Europe/Moscow'))
        txt = (f"📊 <b>Дневная статистика</b>\n\n"
               f"🎮 Начато игр: {self.games_started}\n"
               f"👥 Участвовало игроков: {len(self.players)}\n"
               f"⏳ Время сбора: {now.date()} {now.strftime('%H:%M')}")
        return txt

    def reset_and_dump(self):
        data = (self.games_started, len(self.players))
        self.games_started = 0
        self.players = set()
        return data

async def send_daily_stats(bot: Bot, admin_id: str, stats: DailyStats):
    now = datetime.now(pytz.timezone('Europe/Moscow'))
    n, players = stats.reset_and_dump()
    txt = (f"📊 <b>Дневная статистика</b>\n\n"
           f"🎮 Начато игр: {n}\n"
           f"👥 Участвовало игроков: {players}\n"
           f"⏳ Время сбора: {now.date()} {now.strftime('%H:%M')}")
    await bot.send_message(admin_id, txt, parse_mode="HTML")

async def schedule_daily_stats(bot: Bot, admin_id: str, stats: DailyStats):
    while True:
        utc_now = datetime.now(pytz.utc)
        midnight_utc = datetime.combine(utc_now.date(), datetime.min.time(), tzinfo=pytz.utc) + timedelta(days=1)
        seconds = (midnight_utc - utc_now).total_seconds()
        await asyncio.sleep(seconds)
        await send_daily_stats(bot, admin_id, stats)

r"""
async def periodic_posts(bot: Bot, channel_id: str):
    posts_map = load_posts_map(logger=None)
    while True:
        now = datetime.now(TAJIKISTAN_TZ)
        if 8 <= now.hour < 22 and posts_map:
            topic = random.choice(list(posts_map.keys()))
            quizes = random.sample(posts_map[topic], 3) if len(posts_map[topic]) >= 3 else posts_map[topic][:]
            for q in quizes:
                options = list(q["answers"].values())
                correct_label = q["CorrectAnswers"]
                try:
                    await bot.send_poll(channel_id, f"[{topic}] " + q["question"],
                                        options, type="quiz", is_anonymous=True,
                                        correct_option_id=list(q["answers"].keys()).index(correct_label))
                except Exception:
                    pass
                await asyncio.sleep(3)
        await asyncio.sleep(10800)
"""