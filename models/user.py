from dataclasses import dataclass, field
from typing import Dict, Any
from datetime import datetime

from utils.helpers import load_json, save_json
from config import CFG, LANGUAGES

DEFAULTS = {
    "num_questions": 10,
    "quiz_time": 30,
    "lang": "tg",
}

@dataclass
class UserManager:
    users_file: str = CFG.USERS_FILE
    users: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self):
        self.users = load_json(self.users_file, default={})

    def ensure(self, chat_id: int | str,
               is_group: bool,
               title: str | None = None,
               username: str | None = None,
               first_name: str | None = None,
               is_started: bool | None = None) -> None:

        cid = str(chat_id)
        entry = self.users.get(cid)
        if entry is None:
            entry = {
                "started": bool(is_started),
                "type": "group" if is_group else "private",
                "chat_title": title if is_group else None,
                "chat_link": f"https://t.me/{username}" if is_group and username else "",
                "num_questions": DEFAULTS["num_questions"],
                "quiz_time": DEFAULTS["quiz_time"],
                "lang": DEFAULTS["lang"],
                "registered_at": datetime.now().isoformat(),
                "username": username,
                "first_name": first_name,
            }
            self.users[cid] = entry
            self.save()
        else:
            if is_started is not None:
                entry["started"] = bool(is_started)
            if "lang" not in entry:
                entry["lang"] = DEFAULTS["lang"]
            self.save()

    def started(self, chat_id: int | str) -> bool:
        return self.users.get(str(chat_id), {}).get("started", False)

    def set_lang(self, key: str, lang_code: str):
        self.users.setdefault(key, {})["lang"] = lang_code
        self.save()

    def get_lang(self, key: str, default: str = "tg") -> str:
        return self.users.get(key, {}).get("lang", default)

    def set_quiz_time(self, key: str, seconds: int):
        self.users.setdefault(key, {})["quiz_time"] = seconds
        self.save()

    def set_num_questions(self, key: str, n: int):
        self.users.setdefault(key, {})["num_questions"] = n
        self.save()

    def get_username(self, key: str):
        user = self.users.get(key, {})
        if user:
            return user.get("username")
        return None

    def get_fullname(self, key: str):
        user = self.users.get(key, {})
        if user:
            return user.get("fullname")
        return None

    def get_settings(self, key: str) -> dict:
        data = self.users.get(key, {})
        return {
            "num_questions": data.get("num_questions", DEFAULTS["num_questions"]),
            "quiz_time": data.get("quiz_time", DEFAULTS["quiz_time"]),
            "lang": data.get("lang", DEFAULTS["lang"]),
        }

    def get_type(self, key: str) -> str:
        data = self.users.get(key, {})
        return data.get("type")

    def save(self):
        save_json(self.users_file, self.users)

    def get_all_users(self):
        return self.users
