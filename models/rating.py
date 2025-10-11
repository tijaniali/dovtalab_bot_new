from dataclasses import dataclass, field
from typing import Dict
from utils.helpers import load_json, save_json
from config import CFG

@dataclass
class RatingManager:
    rating_file: str = CFG.RATING_FILE
    group_file: str = CFG.GROUP_RATING_FILE
    global_scores: Dict[str, dict] = field(default_factory=dict)
    group_scores: Dict[str, dict] = field(default_factory=dict)


    def __post_init__(self):
        self.global_scores = load_json(self.rating_file, default={})
        self.group_scores = load_json(self.group_file, default={})

    def add_point(self, chat_id: int | str, user_id: str, username: str|None, full_name: str|None):
        chat_id = str(chat_id)
        if user_id not in self.global_scores:
            self.global_scores[user_id] = {"score": 0, "user_name": "", "full_name": ""}
        self.global_scores[user_id]["score"] += 1
        self.global_scores[user_id]["user_name"] = username
        self.global_scores[user_id]["full_name"] = full_name

        if chat_id not in self.group_scores:
            self.group_scores[chat_id] = {}
        if user_id not in self.group_scores[chat_id]:
            self.group_scores[chat_id][user_id] = {"score": 0, "user_name": "", "full_name": ""}
        self.group_scores[chat_id][user_id]["score"] += 1
        self.group_scores[chat_id][user_id]["user_name"] = username
        self.group_scores[chat_id][user_id]["full_name"] = full_name

    def touch_user(self, chat_id: int | str, user_id: str, username: str|None, full_name: str|None):
        chat_id = str(chat_id)
        if user_id not in self.global_scores:
            self.global_scores[user_id] = {"score": 0, "user_name": "", "full_name": ""}
        self.global_scores[user_id]["user_name"] = username
        self.global_scores[user_id]["full_name"] = full_name

        if chat_id not in self.group_scores:
            self.group_scores[chat_id] = {}
        if user_id not in self.group_scores[chat_id]:
            self.group_scores[chat_id][user_id] = {"score": 0, "user_name": "", "full_name": ""}
        self.group_scores[chat_id][user_id]["user_name"] = username
        self.group_scores[chat_id][user_id]["full_name"] = full_name

    def save(self):
        save_json(self.rating_file, self.global_scores)
        save_json(self.group_file, self.group_scores)
