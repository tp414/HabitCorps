"""
Spiellogik von Habit Corps.

Enthält alle Regeln (Streak, Multiplikator, XP, Ränge, Orden) und die
JSON-Persistenz. Die Datei kennt keinen Webserver und lässt sich daher
direkt testen (siehe test_logic.py).
"""

import calendar
import json
import os
import tempfile
import uuid
from datetime import date, datetime, timedelta

# --------------------------------------------------------------------------
# Konstanten
# --------------------------------------------------------------------------

BASE_XP = 10                  # FR-09
CORE_HABITS = 5               # Anzahl Habits für das Monats-Maximum M
MAX_MULTIPLIER = 3.0
NAME_MAX = 50                 # FR-01
GOAL_MAX = 200                # FR-02

# (Streak ab, Multiplikator) – FR-10
MULTIPLIER_STEPS = [(30, 3.0), (14, 2.0), (7, 1.5), (1, 1.0)]

# Ränge der US Army – FR-11
# pct = Anteil an M, prev = Index des Mindestrangs im Vormonat (FR-28)
RANKS = [
    {"name": "Private",              "grade": "E-1",  "pct": 0,    "prev": None},
    {"name": "Private First Class",  "grade": "E-3",  "pct": 5,    "prev": None},
    {"name": "Specialist",           "grade": "E-4",  "pct": 10,   "prev": None},
    {"name": "Sergeant",             "grade": "E-5",  "pct": 20,   "prev": None},
    {"name": "Staff Sergeant",       "grade": "E-6",  "pct": 30,   "prev": None},
    {"name": "Sergeant First Class", "grade": "E-7",  "pct": 40,   "prev": None},
    {"name": "Master Sergeant",      "grade": "E-8",  "pct": 50,   "prev": None},
    {"name": "Sergeant Major",       "grade": "E-9",  "pct": 60,   "prev": None},
    {"name": "Second Lieutenant",    "grade": "O-1",  "pct": 70,   "prev": None},
    {"name": "Captain",              "grade": "O-3",  "pct": 80,   "prev": None},
    {"name": "Major",                "grade": "O-4",  "pct": 87,   "prev": None},
    {"name": "Colonel",              "grade": "O-6",  "pct": 93,   "prev": 10},
    {"name": "Brigadier General",    "grade": "O-7",  "pct": 97,   "prev": 11},
    {"name": "General",              "grade": "O-10", "pct": None, "prev": 12},
]
GENERAL = len(RANKS) - 1

ANECDOTES = [
    "Ein Private (E-1) trägt kein Rangabzeichen. Im Soldatenjargon heißt das "
    "„slick sleeve“ – glatter Ärmel. Jeder fängt hier an.",
    "Der Private First Class trägt einen Winkel mit einem Bogen darunter. "
    "Dieser Bogen heißt „Rocker“.",
    "Specialist und Corporal haben denselben Soldgrad E-4. Der Specialist ist "
    "aber kein Unteroffizier, sondern Fachkraft.",
    "Mit drei Winkeln beginnt die Laufbahn der Unteroffiziere (NCOs). Sie "
    "gelten als „Backbone of the Army“ – das Rückgrat der Armee.",
    "Ein Staff Sergeant führt typischerweise eine Gruppe (Squad) von rund "
    "neun Soldaten.",
    "Der Sergeant First Class ist meist Platoon Sergeant – die rechte Hand "
    "des Zugführers.",
    "Master Sergeant und First Sergeant sind beide E-8. Der First Sergeant "
    "trägt zusätzlich eine Raute im Abzeichen.",
    "Den ranghöchsten Unteroffizier der ganzen Army, den Sergeant Major of "
    "the Army, gibt es seit 1966.",
    "Kurios: Der goldene Balken des Second Lieutenant steht UNTER dem "
    "silbernen des First Lieutenant. Hier schlägt Silber Gold.",
    "Die zwei silbernen Balken des Captain heißen im Jargon „railroad "
    "tracks“ – Bahngleise.",
    "Der Major trägt ein goldenes Eichenblatt, der Lieutenant Colonel ein "
    "silbernes. Auch hier steht Silber über Gold.",
    "Wegen des Adlers im Abzeichen nennt man den Colonel auch „full bird "
    "colonel“.",
    "Mit dem ersten Stern beginnt die Generalität: Willkommen im Kreis der "
    "„One-Star Generals“.",
    "Ein Gesetz von 1976 machte George Washington posthum zum „General of "
    "the Armies of the United States“. Damit steht er für immer über allen "
    "anderen Generälen der US-Geschichte.",
]

# --------------------------------------------------------------------------
# Datum (über HABIT_TODAY simulierbar, z. B. für Tests und Präsentation)
# --------------------------------------------------------------------------


def today() -> date:
    override = os.environ.get("HABIT_TODAY")
    if override:
        return date.fromisoformat(override)
    return date.today()


def month_key(d: date) -> str:
    return d.strftime("%Y-%m")


def prev_month_key(key: str) -> str:
    y, m = map(int, key.split("-"))
    return f"{y - 1}-12" if m == 1 else f"{y}-{m - 1:02d}"


def days_in_month(key: str) -> int:
    y, m = map(int, key.split("-"))
    return calendar.monthrange(y, m)[1]


def month_max_xp(key: str) -> int:
    """M = 5 Habits x 10 XP x 3,0 x Tage im Monat."""
    return int(CORE_HABITS * BASE_XP * MAX_MULTIPLIER * days_in_month(key))


def multiplier_for(streak: int) -> float:
    for start, mult in MULTIPLIER_STEPS:
        if streak >= start:
            return mult
    return 1.0


def next_multiplier_step(streak: int):
    """Liefert (Tage bis zur nächsten Stufe, nächster Multiplikator) oder None."""
    for start, mult in sorted(MULTIPLIER_STEPS):
        if streak < start and mult > multiplier_for(streak):
            return start - streak, mult
    return None


# --------------------------------------------------------------------------
# Persistenz (NFR-04/05): atomar schreiben über temporäre Datei + Umbenennen
# --------------------------------------------------------------------------


def new_data(start: date) -> dict:
    return {
        "version": 1,
        "start_date": start.isoformat(),
        "last_processed": (start - timedelta(days=1)).isoformat(),
        "last_reset": None,
        "habits": [],
        "completions": [],
        "orders": [],
    }


def load(path: str) -> dict:
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        data = new_data(today())
        save(path, data)
        return data
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if "habits" not in data:              # leere Vorlage {} im Ordner
        data = new_data(today())
        save(path, data)
    return data


def save(path: str, data: dict) -> None:
    folder = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(prefix=".data-", suffix=".tmp", dir=folder)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


# --------------------------------------------------------------------------
# Tageswechsel und Monatswechsel
# --------------------------------------------------------------------------


def _completions_on(data: dict, day: str) -> list:
    return [c for c in data["completions"] if c["date"] == day]


def catch_up(data: dict, now: date = None) -> bool:
    """Wertet alle abgeschlossenen Tage seit dem letzten Aufruf aus.

    FR-08: Ein Tag mit mindestens einem unerledigten Habit setzt ALLE
    Streaks auf 0. FR-22/24: Am Monatsende wird ein Orden gespeichert.
    Gibt True zurück, wenn sich etwas geändert hat.
    """
    now = now or today()
    d = date.fromisoformat(data["last_processed"]) + timedelta(days=1)
    changed = False
    while d < now:
        day = d.isoformat()
        due = [h for h in data["habits"] if h["created"] <= day]
        done = {c["habit_id"] for c in _completions_on(data, day)}
        if due and any(h["id"] not in done for h in due):
            for h in data["habits"]:
                h["streak"] = 0
            data["last_reset"] = day
        if (d + timedelta(days=1)).month != d.month:
            finalize_month(data, month_key(d))
        data["last_processed"] = day
        changed = True
        d += timedelta(days=1)
    return changed


def month_xp(data: dict, key: str) -> float:
    return round(sum(c["xp"] for c in data["completions"]
                     if c["date"].startswith(key)), 2)


def order_for(data: dict, key: str):
    for o in data["orders"]:
        if o["month"] == key:
            return o
    return None


def general_condition(data: dict, key: str) -> bool:
    """FR-27: jeden Tag des Monats mind. 5 Erledigungen mit Multiplikator 3,0."""
    for day in range(1, days_in_month(key) + 1):
        day_key = f"{key}-{day:02d}"
        full = [c for c in _completions_on(data, day_key)
                if c["multiplier"] >= MAX_MULTIPLIER]
        if len(full) < CORE_HABITS:
            return False
    return True


def rank_for(data: dict, key: str, month_end: bool = False):
    """Höchster Rang, dessen XP- UND Vormonatsbedingung erfüllt ist.

    Liefert (Rang-Index, Hinweis auf blockierten nächsten Rang oder None).
    """
    xp = month_xp(data, key)
    m = month_max_xp(key)
    prev = order_for(data, prev_month_key(key))
    prev_rank = prev["rank"] if prev else -1

    best, blocked = 0, None
    for i, r in enumerate(RANKS):
        if i == GENERAL:
            ok_value = month_end and general_condition(data, key)
        else:
            ok_value = xp >= r["pct"] / 100 * m
        ok_prev = r["prev"] is None or prev_rank >= r["prev"]
        if ok_value and ok_prev:
            best = i
        elif ok_value and not ok_prev and blocked is None:
            blocked = (f"{r['name']} erfordert im Vormonat mindestens "
                       f"{RANKS[r['prev']]['name']}.")
    return best, blocked


def finalize_month(data: dict, key: str) -> None:
    """FR-22: Monats-Erfolg (Orden) speichern. FR-25: Streaks bleiben."""
    if key < data["start_date"][:7] or order_for(data, key):
        return
    rank, _ = rank_for(data, key, month_end=True)
    xp = month_xp(data, key)
    m = month_max_xp(key)
    data["orders"].append({
        "month": key,
        "rank": rank,
        "rank_name": RANKS[rank]["name"],
        "xp": xp,
        "max_xp": m,
        "percent": round(xp / m * 100, 1),
    })


# --------------------------------------------------------------------------
# Aktionen
# --------------------------------------------------------------------------


class ValidationError(ValueError):
    pass


def _clean_reminder(value):
    if not value:
        return None
    try:
        datetime.strptime(value, "%H:%M")
    except ValueError:
        raise ValidationError("Die Uhrzeit muss im Format HH:MM sein.")
    return value


def add_habit(data: dict, name: str, goal: str = "", reminder=None) -> dict:
    name = (name or "").strip()
    goal = (goal or "").strip()
    if not name:
        raise ValidationError("Die Mission braucht einen Namen.")      # FR-03
    if len(name) > NAME_MAX:
        raise ValidationError(f"Der Name darf höchstens {NAME_MAX} Zeichen haben.")
    if len(goal) > GOAL_MAX:
        raise ValidationError(f"Das Ziel darf höchstens {GOAL_MAX} Zeichen haben.")
    habit = {
        "id": uuid.uuid4().hex[:8],
        "name": name,
        "goal": goal,
        "created": today().isoformat(),
        "streak": 0,
        "reminder": _clean_reminder(reminder),
    }
    data["habits"].append(habit)
    return habit


def find_habit(data: dict, habit_id: str) -> dict:
    for h in data["habits"]:
        if h["id"] == habit_id:
            return h
    raise ValidationError("Diese Mission gibt es nicht.")


def complete_habit(data: dict, habit_id: str) -> dict:
    """FR-04/05/06/07/09: abhaken, Streak erhöhen, XP gutschreiben."""
    habit = find_habit(data, habit_id)
    day = today().isoformat()
    if any(c["habit_id"] == habit_id for c in _completions_on(data, day)):
        raise ValidationError("Diese Mission ist heute schon erledigt.")

    key = day[:7]
    rank_before, _ = rank_for(data, key)

    habit["streak"] += 1
    mult = multiplier_for(habit["streak"])
    xp = round(BASE_XP * mult, 2)
    data["completions"].append({
        "habit_id": habit_id,
        "date": day,
        "time": datetime.now().strftime("%H:%M:%S"),
        "streak": habit["streak"],
        "multiplier": mult,
        "xp": xp,
    })

    rank_after, _ = rank_for(data, key)
    return {
        "xp": xp,
        "multiplier": mult,
        "streak": habit["streak"],
        "promoted": rank_after > rank_before,
        "rank": rank_after,
    }


def set_reminder(data: dict, habit_id: str, reminder) -> None:
    find_habit(data, habit_id)["reminder"] = _clean_reminder(reminder)


def delete_habit(data: dict, habit_id: str) -> None:
    habit = find_habit(data, habit_id)
    data["habits"].remove(habit)


# --------------------------------------------------------------------------
# Zustand für die Oberfläche
# --------------------------------------------------------------------------

MONTHS_DE = ["Jänner", "Februar", "März", "April", "Mai", "Juni", "Juli",
             "August", "September", "Oktober", "November", "Dezember"]


def month_label(key: str) -> str:
    y, m = map(int, key.split("-"))
    return f"{MONTHS_DE[m - 1]} {y}"


def state(data: dict) -> dict:
    now = today()
    day = now.isoformat()
    key = month_key(now)
    done_today = {c["habit_id"] for c in _completions_on(data, day)}

    habits = []
    for h in data["habits"]:
        # Multiplikator, den die nächste Erledigung bekommt
        upcoming = h["streak"] if h["id"] in done_today else h["streak"] + 1
        step = next_multiplier_step(h["streak"])
        habits.append({
            **h,
            "done_today": h["id"] in done_today,
            "multiplier": multiplier_for(h["streak"]),
            "next_multiplier": multiplier_for(upcoming),
            "next_step": {"days": step[0], "multiplier": step[1]} if step else None,
        })

    xp = month_xp(data, key)
    m = month_max_xp(key)
    rank, blocked = rank_for(data, key)
    nxt = rank + 1 if rank + 1 < GENERAL else None
    prev = order_for(data, prev_month_key(key))

    ranks = []
    for i, r in enumerate(RANKS):
        ranks.append({
            "index": i, **r,
            "xp": None if r["pct"] is None else round(r["pct"] / 100 * m),
            "locked_by_prev": r["prev"] is not None and
            (prev["rank"] if prev else -1) < r["prev"],
        })

    yesterday = (now - timedelta(days=1)).isoformat()
    return {
        "today": day,
        "month": {
            "key": key,
            "label": month_label(key),
            "xp": xp,
            "max_xp": m,
            "percent": round(xp / m * 100, 1),
            "days_left": days_in_month(key) - now.day,
        },
        "habits": habits,
        "open_today": sum(1 for h in habits if not h["done_today"]),
        "streak": max((h["streak"] for h in data["habits"]), default=0),
        "reset_yesterday": data.get("last_reset") == yesterday,
        "rank": {"index": rank, **RANKS[rank], "anecdote": ANECDOTES[rank]},
        "next_rank": None if nxt is None else {
            "index": nxt,
            "name": RANKS[nxt]["name"],
            "xp_needed": max(0, round(RANKS[nxt]["pct"] / 100 * m - xp, 2)),
        },
        "blocked": blocked,
        "ranks": ranks,
        "orders": [
            {**o, "label": month_label(o["month"]),
             "grade": RANKS[o["rank"]]["grade"]}
            for o in sorted(data["orders"], key=lambda o: o["month"], reverse=True)
        ],
    }
