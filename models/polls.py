# вставь/замени в quiz.py (или вынеси PollRegistry в poll_registry.py)
import time
import asyncio
import inspect
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Dict, Callable, Set, Any, List
from models.rating import RatingManager
from aiogram import Bot


# --- PollRegistry ----------------------------------------------------------
class PollKind(Enum):
    QUIZ = auto()
    DUEL = auto()

@dataclass
class PollInfo:
    poll_id: str
    kind: PollKind
    owner_id: int                      # для QUIZ: chat_id, для DUEL: duel_id
    target_user_id: Optional[int] = None  # для DUEL: user who got this poll (uid)
    correct_option_id: Optional[int] = None
    start_time: float = field(default_factory=time.time)
    processed_users: Set[int] = field(default_factory=set)

class PollRegistry:
    rating: RatingManager = field(default_factory=RatingManager)

    def __init__(self, rating:RatingManager):
        self._by_poll: Dict[str, PollInfo] = {}
        self._handlers: Dict[PollKind, Callable] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        self.rating = rating


    def record_poll(self, poll_id: str, kind: PollKind, owner_id: int,
                    target_user_id: Optional[int]=None,
                    correct_option_id: Optional[int]=None):
        """Register poll metadata."""
        self._by_poll[poll_id] = PollInfo(
            poll_id=poll_id,
            kind=kind,
            owner_id=owner_id,
            target_user_id=target_user_id,
            correct_option_id=correct_option_id,
            start_time=time.time()
        )
        # ensure lock exists
        self._locks.setdefault(poll_id, asyncio.Lock())

    def get(self, poll_id: str) -> Optional[PollInfo]:
        return self._by_poll.get(poll_id)

    def pop(self, poll_id: str) -> Optional[PollInfo]:
        self._locks.pop(poll_id, None)
        return self._by_poll.pop(poll_id, None)

    def cleanup_by_owner(self, kind: PollKind, owner_id: int):
        """Remove all polls owned by owner_id+kind (used when ending quiz/duel)."""
        for pid, info in list(self._by_poll.items()):
            if info.kind == kind and info.owner_id == owner_id:
                self._by_poll.pop(pid, None)
                self._locks.pop(pid, None)

    def register_handler(self, kind: PollKind, handler: Callable):
        """Register manager handler: handler(poll_info, telegram_user, is_correct, option_ids)"""
        self._handlers[kind] = handler

    async def dispatch(self, poll_id: str,
                       telegram_user: Any,
                       chat: Any,
                       option_ids: List[int],
                       bot: Bot):
        """
        Called by Telegram PollAnswer handler.
        telegram_user - object with .id, .username, .full_name (or adapt)
        option_ids - list of selected option indices from the update
        """
        info = self.get(poll_id)
        if not info:
            # unknown poll, ignore or log
            return None

        lock = self._locks.setdefault(poll_id, asyncio.Lock())
        async with lock:
            user_id = int(getattr(telegram_user, "id", telegram_user) )
            # prevent duplicate processing for same user & poll
            if user_id in info.processed_users:
                return None

            # determine correctness (if recorded)
            is_correct = False
            if info.correct_option_id is not None:
                is_correct = info.correct_option_id in option_ids

            info.processed_users.add(user_id)

            if is_correct:
                self.rating.add_point(chat_id=info.owner_id,
                                      user_id=str(user_id),
                                      username=getattr(telegram_user, "username", None),
                                      full_name=getattr(telegram_user, "full_name", None))
                self.rating.save()

            handler = self._handlers.get(info.kind)
            if not handler:
                return None

            if inspect.iscoroutinefunction(handler):
                return await handler(info, telegram_user, is_correct, option_ids, bot)
            else:
                return handler(info, telegram_user, is_correct, option_ids, bot)
