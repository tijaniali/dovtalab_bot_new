import json, logging
from utils.helpers import load_json
from config import CFG

def load_questions(logger: logging.Logger) -> dict[str, list[dict]]:
    files = {
        "БИОЛОГИЯ": "db/Biology.json",
        "ГЕОГРАФИЯ": "db/Geography.json",
        "ИСТОРИЯ": "db/History.json",
        "ЛИТЕРАТУРА": "db/Literature.json",
        "ПРАВО": "db/Rights.json",
        "ЯЗЫК": "db/Zabon.json",
        "ДИПЛОМАТИЯ": "db/Diplomacy.json"
    }
    data: dict[str, list[dict]] = {}
    for key, fname in files.items():
        data[key] = load_json(fname, logger=logger, default=[])
    return data

def load_posts_map(logger: logging.Logger) -> dict[str, list[dict]]:
    files = {
        "БИОЛОГИЯ": "db/Biology.json",
        "ГЕОГРАФИЯ": "db/Geography.json",
        "ТАЪРИХ": "db/History.json",
        "АДАБИЁТ": "db/Literature.json",
        "ХУҚУҚ": "db/Rights.json",
        "ЗАБОН": "db/Zabon.json"
    }
    data: dict[str, list[dict]] = {}
    for key, fname in files.items():
        data[key] = load_json(fname, logger=logger, default=[])
    return data

def save_post(subject:str, post:dict):
    files = {
        "БИОЛОГИЯ": "db/Biology.json",
        "ГЕОГРАФИЯ": "db/Geography.json",
        "ИСТОРИЯ": "db/History.json",
        "ЛИТЕРАТУРА": "db/Literature.json",
        "ПРАВО": "db/Rights.json",
        "ЯЗЫК": "db/Zabon.json",
        "ДИПЛОМАТИЯ": "db/Diplomacy.json"
    }
    if subject in files:
        try:
            json.dump(post, open(files[subject], "w", encoding="utf-8"), indent=4, ensure_ascii=False)
            return True
        except:
            return False
    else:
        return False

def load_messages(logger):
    return load_json(CFG.MESSAGES_FILE, logger=logger, default={})

def load_lemma(logger):
    return load_json(CFG.LEMMA_FILE, logger=logger, default={})
