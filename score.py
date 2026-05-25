import json

SCORES_FILE = "highscores.json"


def calculate_score(game_stats: dict) -> int:
    kills = game_stats.get("kills", 0)
    max_combo = game_stats.get("max_combo", 0)
    base = kills * 5
    combo_bonus = max_combo * (max_combo * 5)  # doubles per combo count
    return base + combo_bonus


def load_high_score() -> int:
    try:
        with open(SCORES_FILE) as f:
            return json.load(f).get("high_score", 0)
    except (FileNotFoundError, json.JSONDecodeError):
        return 0


def save_high_score(score: int) -> bool:
    current = load_high_score()
    if score > current:
        with open(SCORES_FILE, "w") as f:
            json.dump({"high_score": score}, f)
        return True  # new record
    return False
