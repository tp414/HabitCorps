"""
Spiellogik von Habit Corps.

Enthält alle Regeln (Streak, Multiplikator, XP, Ränge, Orden) und die
JSON-Persistenz. Die Datei kennt keinen Webserver und lässt sich daher
direkt testen (siehe test_logic.py).

Kleines Python-Wörterbuch für Einsteiger:
  - Liste       [a, b, c]            geordnete Sammlung, Zugriff mit liste[0]
  - Dictionary  {"name": "Kuno"}     Sammlung aus Schlüssel -> Wert, Zugriff mit d["name"]
  - Menge       {a, b}               wie eine Liste, aber ohne Doppelte und ohne Reihenfolge
  - None        "nichts", kein Wert vorhanden
  - for x in liste:   wiederholt den eingerückten Block für jedes Element
  - if / elif / else  Verzweigung: "wenn / sonst wenn / sonst"
  - return wert       beendet eine Funktion und gibt den Wert zurück
  - raise Fehler      bricht ab und meldet einen Fehler
  - "-> int" hinter einer Funktion ist nur ein Hinweis, welcher Typ herauskommt

Wie die Daten in data.json aussehen:
  {
    "habits":      [ {Mission}, ... ]        die angelegten Missionen
    "completions": [ {Erledigung}, ... ]     jedes einzelne Abhaken mit Datum und XP
    "orders":      [ {Orden}, ... ]          ein Eintrag pro abgeschlossenem Monat
    "last_processed": "2026-10-07"           bis zu diesem Tag ist alles ausgewertet
    ...
  }
"""

# Importe: fertige Werkzeuge aus der Python-Standardbibliothek
# calendar  -> wie viele Tage hat ein Monat?
# json      -> Daten in Text umwandeln und zurück (für data.json)
# os        -> Dateien und Ordner
# tempfile  -> temporäre Dateien (für sicheres Speichern)
# uuid      -> zufällige, eindeutige IDs für Missionen
# datetime  -> Datum und Uhrzeit rechnen (timedelta = Zeitspanne, z. B. 1 Tag)
import calendar
import json
import os
import tempfile
import uuid
from datetime import date, datetime, timedelta

# --------------------------------------------------------------------------
# Konstanten
# --------------------------------------------------------------------------

# Diese Werte steuern das ganze Spiel. Wer z. B. mehr XP pro Mission will,
# ändert nur BASE_XP – der Rest passt sich automatisch an.
BASE_XP = 10                  # FR-09
CORE_HABITS = 5               # Anzahl Habits für das Monats-Maximum M
MAX_MULTIPLIER = 3.0
NAME_MAX = 50                 # FR-01
GOAL_MAX = 200                # FR-02

# (Streak ab, Multiplikator) – FR-10
# Liste von Paaren (Tupeln). Gelesen von oben nach unten:
# ab 30 Tagen Streak x3,0 | ab 14 Tagen x2,0 | ab 7 Tagen x1,5 | sonst x1,0
MULTIPLIER_STEPS = [(30, 3.0), (14, 2.0), (7, 1.5), (1, 1.0)]

# Ränge der US Army – FR-11
# pct = Anteil an M, prev = Index des Mindestrangs im Vormonat (FR-28)
# Jeder Rang ist ein Dictionary. Die Position in der Liste ist der "Index":
# RANKS[0] = Private, RANKS[13] = General. Damit rechnet das Programm intern.
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
# len(...) = Anzahl der Elemente. 14 Ränge -> der letzte hat den Index 13.
GENERAL = len(RANKS) - 1
GENERAL_LIVE_PCT = 100     # FR-32: nach dem ersten General-Orden als XP-Rang erreichbar

# Eine Anekdote pro Rang, gleiche Reihenfolge wie RANKS.
# Zwei Texte direkt hintereinander ("a" "b") fügt Python automatisch zusammen.
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


# Hier kann ein "gefälschtes" heutiges Datum hinterlegt werden (Demo-Modus).
# Der Unterstrich am Anfang heißt: nur für den internen Gebrauch.
_today_override = None


def set_today(d) -> None:
    """Setzt ein simuliertes Datum (Demo-Modus). None = echtes Datum."""
    # "global" erlaubt, die Variable außerhalb der Funktion zu verändern.
    global _today_override
    _today_override = d


# Liefert "heute". Reihenfolge: 1. Demo-Datum, 2. Umgebungsvariable HABIT_TODAY
# (für Tests und Präsentation), 3. das echte Datum des Computers.
def today() -> date:
    if _today_override is not None:
        return _today_override
    override = os.environ.get("HABIT_TODAY")
    if override:
        return date.fromisoformat(override)
    return date.today()


# Macht aus einem Datum den Monats-Schlüssel, z. B. 2026-10-08 -> "2026-10".
def month_key(d: date) -> str:
    return d.strftime("%Y-%m")


# Schlüssel des Vormonats, z. B. "2026-01" -> "2025-12".
def prev_month_key(key: str) -> str:
    # "2026-10".split("-") ergibt ["2026", "10"]; map(int, ...) macht Zahlen daraus.
    y, m = map(int, key.split("-"))
    return f"{y - 1}-12" if m == 1 else f"{y}-{m - 1:02d}"


# Anzahl der Tage im Monat (28 bis 31).
def days_in_month(key: str) -> int:
    y, m = map(int, key.split("-"))
    return calendar.monthrange(y, m)[1]


def month_max_xp(key: str) -> int:
    """M = 5 Habits x 10 XP x 3,0 x Tage im Monat."""
    return int(CORE_HABITS * BASE_XP * MAX_MULTIPLIER * days_in_month(key))


# Sucht die erste Stufe, deren Mindest-Streak erreicht ist, und gibt ihren Multiplikator zurück.
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


# Erzeugt einen leeren Spielstand (wird beim allerersten Start verwendet).
def new_data(start: date) -> dict:
    return {
        "version": 1,
        "start_date": start.isoformat(),
        "last_processed": (start - timedelta(days=1)).isoformat(),
        "last_reset": None,
        "habits": [],
        "completions": [],
        "orders": [],
        "tutorial_done": False,      # FR-33: Kunos Tutorial noch nicht gesehen
    }


# Liest data.json ein. Gibt es die Datei nicht oder ist sie leer,
# wird ein neuer, leerer Spielstand angelegt.
def load(path: str) -> dict:
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        data = new_data(today())
        save(path, data)
        return data
    # "with open(...)" öffnet die Datei und schließt sie danach automatisch wieder.
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if "habits" not in data:              # leere Vorlage {} im Ordner
        data = new_data(today())
        save(path, data)
    return data


# Speichert den Spielstand SICHER (NFR-04/05):
# 1. Zuerst in eine temporäre Datei schreiben.
# 2. Erst wenn das vollständig geklappt hat, die alte data.json damit ersetzen.
# Stürzt das Programm mitten im Schreiben ab, bleibt die alte Datei heil.
def save(path: str, data: dict) -> None:
    folder = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(prefix=".data-", suffix=".tmp", dir=folder)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            # flush + fsync: dafür sorgen, dass die Daten wirklich auf der Festplatte stehen
            f.flush()
            os.fsync(f.fileno())
        # Ersetzen in einem Schritt: entweder alte oder neue Datei, nie eine halbe
        os.replace(tmp, path)
    # Bei einem Fehler: temporäre Datei aufräumen und den Fehler weitermelden (raise)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


# --------------------------------------------------------------------------
# Tageswechsel und Monatswechsel
# --------------------------------------------------------------------------


# Alle Erledigungen eines bestimmten Tages.
# [c for c in liste if Bedingung] ist eine "List Comprehension":
# eine kurze Schreibweise für "nimm alle Elemente, die die Bedingung erfüllen".
def _completions_on(data: dict, day: str) -> list:
    return [c for c in data["completions"] if c["date"] == day]


def catch_up(data: dict, now: date = None) -> bool:
    """Wertet alle abgeschlossenen Tage seit dem letzten Aufruf aus.

    FR-08: Ein Tag mit mindestens einem unerledigten Habit setzt ALLE
    Streaks auf 0. FR-22/24: Am Monatsende wird ein Orden gespeichert.
    Gibt True zurück, wenn sich etwas geändert hat.
    """
    now = now or today()
    # Mit dem ersten Tag beginnen, der noch nicht ausgewertet wurde
    d = date.fromisoformat(data["last_processed"]) + timedelta(days=1)
    changed = False
    # "while" wiederholt den Block, solange die Bedingung stimmt –
    # hier für jeden vergangenen Tag bis gestern (heute läuft ja noch).
    while d < now:
        day = d.isoformat()
        # Welche Missionen waren an diesem Tag fällig? (erst ab dem Erstellungstag)
        due = [h for h in data["habits"] if h["created"] <= day]
        # Welche davon wurden erledigt? (als Menge der IDs)
        done = {c["habit_id"] for c in _completions_on(data, day)}
        # FR-08: Fehlt auch nur EINE Mission, fallen ALLE Streaks auf 0
        if due and any(h["id"] not in done for h in due):
            for h in data["habits"]:
                h["streak"] = 0
            data["last_reset"] = day
        # War das der letzte Tag des Monats? Dann den Monats-Orden verleihen
        if (d + timedelta(days=1)).month != d.month:
            finalize_month(data, month_key(d))
        data["last_processed"] = day
        changed = True
        d += timedelta(days=1)
    return changed


# Summe aller XP eines Monats (alle Erledigungen, deren Datum mit "2026-10" beginnt).
def month_xp(data: dict, key: str) -> float:
    return round(sum(c["xp"] for c in data["completions"]
                     if c["date"].startswith(key)), 2)


# Sucht den Orden eines Monats. Gibt None zurück, wenn es keinen gibt.
def order_for(data: dict, key: str):
    for o in data["orders"]:
        if o["month"] == key:
            return o
    return None


def general_condition(data: dict, key: str) -> bool:
    """FR-27: jeden Tag des Monats mind. 5 Erledigungen mit Multiplikator 3,0."""
    # range(1, 32) zählt 1, 2, ..., 31 (die obere Grenze ist nicht dabei)
    for day in range(1, days_in_month(key) + 1):
        # {day:02d} = Zahl immer zweistellig, also "05" statt "5"
        day_key = f"{key}-{day:02d}"
        full = [c for c in _completions_on(data, day_key)
                if c["multiplier"] >= MAX_MULTIPLIER]
        if len(full) < CORE_HABITS:
            return False
    return True


def general_unlocked(data: dict, key: str) -> bool:
    """FR-32: Wurde General vor diesem Monat schon einmal verliehen?"""
    return any(o["rank"] == GENERAL and o["month"] < key for o in data["orders"])


def rank_for(data: dict, key: str, month_end: bool = False):
    """Höchster Rang, dessen XP- UND Vormonatsbedingung erfüllt ist.

    Liefert (Rang-Index, Hinweis auf blockierten nächsten Rang oder None).
    """
    # Grundwerte holen: bisherige XP, Monats-Maximum M, Rang des Vormonats (-1 = keiner)
    xp = month_xp(data, key)
    m = month_max_xp(key)
    prev = order_for(data, prev_month_key(key))
    prev_rank = prev["rank"] if prev else -1

    unlocked = general_unlocked(data, key)
    best, blocked = 0, None
    # Alle Ränge von unten nach oben durchgehen. enumerate liefert Index i UND Rang r.
    # Am Ende steht in "best" der höchste Rang, dessen Bedingungen erfüllt sind.
    for i, r in enumerate(RANKS):
        if i == GENERAL:
            # strenge Monatsbedingung (FR-27) oder – nach dem ersten General – 100 % von M (FR-32)
            ok_value = ((month_end and general_condition(data, key)) or
                        (unlocked and xp >= GENERAL_LIVE_PCT / 100 * m))
        else:
            ok_value = xp >= r["pct"] / 100 * m
        # Vormonatsbedingung (FR-28): nur Colonel, Brigadier General und General haben eine
        ok_prev = r["prev"] is None or prev_rank >= r["prev"]
        if ok_value and ok_prev:
            best = i
        # XP würden reichen, aber der Vormonat nicht -> Hinweis für die Oberfläche merken
        elif ok_value and not ok_prev and blocked is None:
            blocked = (f"{r['name']} erfordert im Vormonat mindestens "
                       f"{RANKS[r['prev']]['name']}.")
    return best, blocked


def finalize_month(data: dict, key: str) -> None:
    """FR-22: Monats-Erfolg (Orden) speichern. FR-25: Streaks bleiben."""
    # Keinen Orden für Monate vor dem ersten Start und keinen doppelten Orden
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


# Eigener Fehlertyp für Eingabefehler (z. B. leerer Name).
# Der Webserver fängt ihn ab und zeigt die Meldung in der Oberfläche an.
class ValidationError(ValueError):
    pass


# Prüft eine Erinnerungszeit. Leer -> None (keine Erinnerung),
# sonst muss sie im Format HH:MM sein (z. B. "07:30").
def _clean_reminder(value):
    if not value:
        return None
    try:
        datetime.strptime(value, "%H:%M")
    except ValueError:
        raise ValidationError("Die Uhrzeit muss im Format HH:MM sein.")
    return value


# Legt eine neue Mission an (FR-01 bis FR-03).
# goal="" bedeutet: Wird kein Ziel übergeben, ist es ein leerer Text.
def add_habit(data: dict, name: str, goal: str = "", reminder=None) -> dict:
    # .strip() entfernt Leerzeichen am Anfang und Ende; "or" fängt None ab
    name = (name or "").strip()
    goal = (goal or "").strip()
    if not name:
        raise ValidationError("Die Mission braucht einen Namen.")      # FR-03
    if len(name) > NAME_MAX:
        raise ValidationError(f"Der Name darf höchstens {NAME_MAX} Zeichen haben.")
    if len(goal) > GOAL_MAX:
        raise ValidationError(f"Das Ziel darf höchstens {GOAL_MAX} Zeichen haben.")
    # Die neue Mission als Dictionary. Die ID sind 8 zufällige Zeichen.
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


# FR-33: Merkt sich, dass das Tutorial abgeschlossen (oder übersprungen) wurde.
# Dadurch erscheint es beim nächsten Öffnen der App nicht noch einmal.
def finish_tutorial(data: dict) -> bool:
    data["tutorial_done"] = True
    return True


# FR-34: Gesamten Fortschritt zurücksetzen.
# Sicherheitsnetz: Vorher wird der alte Stand als Kopie im Unterordner
# "backups" gespeichert (Dateiname mit Datum und Uhrzeit). So kann man
# einen versehentlichen Neustart rückgängig machen, indem man die Kopie
# wieder in data.json umbenennt.
def reset_progress(data: dict, path: str) -> dict:
    # Ordner "backups" neben data.json anlegen (exist_ok: kein Fehler, falls er schon existiert)
    folder = os.path.join(os.path.dirname(os.path.abspath(path)), "backups")
    os.makedirs(folder, exist_ok=True)
    # Dateiname mit Zeitstempel, z. B. data_2026-10-12_15-30-00.json
    name = "data_" + datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".json"
    save(os.path.join(folder, name), data)
    # Den Spielstand durch einen komplett neuen ersetzen.
    # .clear() leert das Dictionary, .update() füllt es mit dem neuen Inhalt.
    data.clear()
    data.update(new_data(today()))
    return {"backup": os.path.join("backups", name)}


# Sucht eine Mission über ihre ID, sonst Fehlermeldung.
def find_habit(data: dict, habit_id: str) -> dict:
    for h in data["habits"]:
        if h["id"] == habit_id:
            return h
    raise ValidationError("Diese Mission gibt es nicht.")


def complete_habit(data: dict, habit_id: str) -> dict:
    """FR-04/05/06/07/09: abhaken, Streak erhöhen, XP gutschreiben."""
    habit = find_habit(data, habit_id)
    day = today().isoformat()
    # FR-05: höchstens einmal pro Tag abhaken
    if any(c["habit_id"] == habit_id for c in _completions_on(data, day)):
        raise ValidationError("Diese Mission ist heute schon erledigt.")

    key = day[:7]
    # Rang VOR dem Abhaken merken, um eine Beförderung zu erkennen.
    # Der Unterstrich _ heißt: Diesen zweiten Rückgabewert brauchen wir nicht.
    rank_before, _ = rank_for(data, key)

    # Streak erhöhen (+= 1 heißt "um 1 erhöhen"), dann Multiplikator und XP berechnen
    habit["streak"] += 1
    mult = multiplier_for(habit["streak"])
    xp = round(BASE_XP * mult, 2)
    # Die Erledigung mit allen Details speichern (.append hängt ans Listenende an)
    data["completions"].append({
        "habit_id": habit_id,
        "date": day,
        "time": datetime.now().strftime("%H:%M:%S"),
        "streak": habit["streak"],
        "multiplier": mult,
        "xp": xp,
    })

    # Rang NACH dem Abhaken: ist er höher, gab es eine Beförderung
    rank_after, _ = rank_for(data, key)
    return {
        "xp": xp,
        "multiplier": mult,
        "streak": habit["streak"],
        "promoted": rank_after > rank_before,
        "rank": rank_after,
    }


# Erinnerungszeit einer Mission ändern oder entfernen.
def set_reminder(data: dict, habit_id: str, reminder) -> None:
    find_habit(data, habit_id)["reminder"] = _clean_reminder(reminder)


# Mission löschen. Bereits verdiente XP bleiben erhalten.
def delete_habit(data: dict, habit_id: str) -> None:
    habit = find_habit(data, habit_id)
    data["habits"].remove(habit)


# --------------------------------------------------------------------------
# Rang-Prognose (FR-31): Markov-Kette + dynamische Programmierung
# --------------------------------------------------------------------------
#
# Idee: Jeder verbleibende Tag des Monats ist ein Zufallsexperiment.
#   - Mit Wahrscheinlichkeit p schafft der Nutzer ALLE Missionen
#     -> jeder Streak steigt um 1, volle XP.
#   - Mit Wahrscheinlichkeit 1 - p verpasst er mindestens eine
#     -> er bekommt nur einen Teil q der XP, danach fallen ALLE Streaks auf 0.
# Der Zustand nach jedem Tag ist (Streak-Zustand, bisherige XP). Weil der
# nächste Tag nur vom aktuellen Zustand abhängt, ist das eine Markov-Kette.
# Statt tausende Monate zu simulieren, rechnen wir die exakte
# Wahrscheinlichkeitsverteilung Tag für Tag weiter (dynamische Programmierung).
#
# Streak-Zustände:
#   "A"     = seit heute noch kein Fehltag -> jedes Habit behält seinen
#             eigenen Streak (Habits können unterschiedlich alt sein)
#   c >= 0  = nach einem Fehltag: alle Habits haben denselben Streak c
#
# XP sind immer Vielfache von 5 (10 x 1 / 1,5 / 2 / 3), deshalb rechnen wir
# in 5er-Einheiten exakt mit ganzen Zahlen.

# Einstellungen der Prognose
HISTORY_DAYS = 60          # so weit schaut die Schätzung zurück
PRIOR_SUCCESS = 2          # Beta-Prior: 2 Erfolge ...
PRIOR_FAIL = 1             # ... und 1 Fehltag als Startannahme
DEFAULT_PARTIAL = 0.5      # Anteil erledigter Missionen an einem Fehltag


def estimate_behaviour(data: dict, now: date):
    """Schätzt p (alles geschafft) und q (Anteil an Fehltagen) aus dem Verlauf."""
    # Schritt 1: Für jeden Tag die Menge der erledigten Missions-IDs sammeln
    # setdefault legt einen leeren Eintrag an, falls es den Tag noch nicht gibt
    by_day = {}
    for c in data["completions"]:
        by_day.setdefault(c["date"], set()).add(c["habit_id"])
    # Schritt 2: Höchstens 60 Tage zurück, aber nicht vor dem ersten Start
    start = max(date.fromisoformat(data["start_date"]), now - timedelta(days=HISTORY_DAYS))
    full = days = 0
    partial_sum = partial_days = 0.0
    d = start
    while d < now:
        key = d.isoformat()
        due = [h["id"] for h in data["habits"] if h["created"] <= key]
        if due:
            # & = Schnittmenge: erledigt UND fällig
            done = len(by_day.get(key, set()) & set(due))
            days += 1
            if done == len(due):
                full += 1
            else:
                partial_sum += done / len(due)
                partial_days += 1
        d += timedelta(days=1)
    # Schritt 3: p = Anteil der perfekten Tage, mit Startannahme (Beta-Prior),
    # damit am Anfang ohne Verlauf nicht 0 % oder 100 % herauskommt.
    # Beispiel ohne Verlauf: (0 + 2) / (0 + 2 + 1) = 67 %
    p = (full + PRIOR_SUCCESS) / (days + PRIOR_SUCCESS + PRIOR_FAIL)
    q = partial_sum / partial_days if partial_days else DEFAULT_PARTIAL
    return p, q, full, days


def _units(streak_after: int) -> int:
    """XP einer Erledigung in 5er-Einheiten, abhängig vom Streak danach."""
    return int(round(BASE_XP * multiplier_for(streak_after) / 5))


# Hilfsfunktion: Wahrscheinlichkeit zu einem Zustand dazuzählen
def _add(dist: dict, key, prob: float) -> None:
    if prob > 0:
        dist[key] = dist.get(key, 0.0) + prob


# Welcher Rang ergibt sich aus einer XP-Summe? (vereinfachte Form von rank_for)
def _rank_from_xp(xp: float, m: int, prev_rank: int, unlocked: bool = False) -> int:
    best = 0
    for i, r in enumerate(RANKS):
        pct = r["pct"] if i < GENERAL else (GENERAL_LIVE_PCT if unlocked else None)
        if pct is None:
            continue
        ok_prev = r["prev"] is None or prev_rank >= r["prev"]
        if xp >= pct / 100 * m and ok_prev:
            best = i
    return best


def forecast(data: dict, p: float = None, q: float = None) -> dict:
    """Wahrscheinlichkeit für jeden Rang am Monatsende."""
    now = today()
    # Ohne Missionen gibt es nichts vorherzusagen
    if not data["habits"]:
        return None
    key = month_key(now)
    m = month_max_xp(key)
    # p und q aus dem Verlauf schätzen – außer sie wurden vorgegeben (für Tests)
    est_p, est_q, full_days, hist_days = estimate_behaviour(data, now)
    p = est_p if p is None else p
    q = est_q if q is None else q

    day = now.isoformat()
    done_today = {c["habit_id"] for c in _completions_on(data, day)}
    habits = data["habits"]
    n = len(habits)
    # Bisherige XP dieses Monats
    xp_now = int(round(month_xp(data, key) / 5))     # in 5er-Einheiten

    # ---- heute: offene Missionen
    open_h = [h for h in habits if h["id"] not in done_today]
    base = [h["streak"] + (0 if h["id"] in done_today else 1) for h in habits]
    gain_today = sum(_units(h["streak"] + 1) for h in open_h)
    p_today = p if open_h else 1.0

    # Verteilung: Schlüssel (Zustand, XP-Einheiten) -> Wahrscheinlichkeit
    # Startverteilung nach dem heutigen Tag:
    # mit Wahrscheinlichkeit p_today alles geschafft (Zustand "A"),
    # sonst Fehltag (Zustand 0, nur Teil-XP).
    dist = {}
    _add(dist, ("A", xp_now + gain_today), p_today)
    _add(dist, (0, xp_now + int(round(q * gain_today))), 1 - p_today)

    # ---- restliche Tage
    remaining = days_in_month(key) - now.day
    # DYNAMISCHE PROGRAMMIERUNG: Tag für Tag die gesamte Verteilung weiterrechnen.
    # Jeder Zustand verzweigt in "Erfolg" (Wahrscheinlichkeit p) und "Fehltag" (1 - p).
    # Gleiche Zustände werden zusammengefasst – deshalb bleibt das schnell.
    for j in range(1, remaining + 1):
        full_a = sum(_units(b + j) for b in base)       # Zustand A: eigene Streaks
        nxt = {}
        for (state, xp), prob in dist.items():
            if state == "A":
                gain = full_a
                succ_state = "A"
            else:
                gain = n * _units(state + 1)
                succ_state = state + 1
            _add(nxt, (succ_state, xp + gain), prob * p)
            _add(nxt, (0, xp + int(round(q * gain))), prob * (1 - p))
        dist = nxt

    # ---- Ränge auswerten
    prev = order_for(data, prev_month_key(key))
    prev_rank = prev["rank"] if prev else -1
    unlocked = general_unlocked(data, key)
    # Für jeden Endzustand den Rang bestimmen und die Wahrscheinlichkeiten aufsummieren.
    # [0.0] * 14 erzeugt eine Liste mit 14 Nullen.
    probs = [0.0] * len(RANKS)
    expected = 0.0
    for (state, xp), prob in dist.items():
        probs[_rank_from_xp(xp * 5, m, prev_rank, unlocked)] += prob
        expected += prob * xp * 5

    # ---- General: nur ohne Fehltag und wenn jeden Tag >= 5 Missionen x3,0
    # Sonderfall erster General: geht nur, wenn bisher jeder Tag perfekt war
    # und auch alle restlichen Tage perfekt sein müssen -> p hoch Anzahl Tage
    general_possible = not unlocked and (     # freigeschaltet: oben schon über XP erfasst
        prev_rank >= RANKS[GENERAL]["prev"] and n >= CORE_HABITS and
        all(len([c for c in _completions_on(data, f"{key}-{d:02d}") if c["multiplier"] >= MAX_MULTIPLIER]) >= CORE_HABITS
            for d in range(1, now.day)) and
        all(sum(1 for b in base if multiplier_for(b + j) >= MAX_MULTIPLIER) >= CORE_HABITS
            for j in range(0, remaining + 1))
    )
    if general_possible:
        p_gen = p_today * p ** remaining
        probs[GENERAL] = p_gen
        probs[GENERAL - 1] = max(0.0, probs[GENERAL - 1] - p_gen)

    # Wahrscheinlichster Rang = Index mit der höchsten Wahrscheinlichkeit
    likely = max(range(len(RANKS)), key=lambda i: probs[i])
    # Rang, den man mit mindestens 50 % Wahrscheinlichkeit mindestens erreicht
    cum, safe = 0.0, 0
    for i in range(len(RANKS) - 1, -1, -1):
        cum += probs[i]
        if cum >= 0.5:
            safe = i
            break

    # Bestfall: ab jetzt kein einziger Fehltag
    # Die Funktion ruft sich hier selbst auf (Rekursion), nur eben mit p = 100 %
    best = None
    if p < 1:
        best = forecast(data, p=1.0, q=q)["likely"]["index"]

    return {
        "p": round(p, 3),
        "q": round(q, 3),
        "full_days": full_days,
        "history_days": hist_days,
        "expected_xp": round(expected, 1),
        "probabilities": [{"index": i, "name": RANKS[i]["name"], "p": round(x, 4)}
                          for i, x in enumerate(probs) if x >= 0.0005],
        "likely": {"index": likely, "name": RANKS[likely]["name"], "p": round(probs[likely], 4)},
        "safe": {"index": safe, "name": RANKS[safe]["name"]},
        "best_case": None if best is None else {"index": best, "name": RANKS[best]["name"]},
    }


# --------------------------------------------------------------------------
# Zustand für die Oberfläche
# --------------------------------------------------------------------------

# Monatsnamen auf Österreichisch (Jänner statt Januar)
MONTHS_DE = ["Jänner", "Februar", "März", "April", "Mai", "Juni", "Juli",
             "August", "September", "Oktober", "November", "Dezember"]


def month_label(key: str) -> str:
    y, m = map(int, key.split("-"))
    return f"{MONTHS_DE[m - 1]} {y}"


# Stellt ALLES zusammen, was die Oberfläche anzeigen muss:
# Missionen, Monats-XP, Rang, Rangliste, Orden, Prognose.
# Das Ergebnis wird als JSON an den Browser geschickt.
def state(data: dict) -> dict:
    now = today()
    day = now.isoformat()
    key = month_key(now)
    done_today = {c["habit_id"] for c in _completions_on(data, day)}

    habits = []
    # Für jede Mission zusätzliche Anzeige-Infos berechnen.
    # **h kopiert alle Einträge des Dictionaries h in das neue Dictionary.
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
    unlocked = general_unlocked(data, key)
    last = GENERAL if unlocked else GENERAL - 1
    nxt = rank + 1 if rank + 1 <= last else None
    prev = order_for(data, prev_month_key(key))

    # Eine Funktion innerhalb einer Funktion: Schwelle eines Rangs in Prozent
    # (General hat erst nach dem ersten General-Orden eine feste Schwelle)
    def pct_of(i):
        return GENERAL_LIVE_PCT if (i == GENERAL and unlocked) else RANKS[i]["pct"]

    ranks = []
    for i, r in enumerate(RANKS):
        ranks.append({
            "index": i, **r, "pct": pct_of(i),
            "xp": None if pct_of(i) is None else round(pct_of(i) / 100 * m),
            "locked_by_prev": r["prev"] is not None and
            (prev["rank"] if prev else -1) < r["prev"],
        })

    # Das fertige Ergebnis – genau so kommt es als JSON im Browser an
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
            "xp_needed": max(0, round(pct_of(nxt) / 100 * m - xp, 2)),
        },
        "blocked": blocked,
        "general_unlocked": unlocked,
        # Fehlt der Eintrag (ältere data.json), gilt das Tutorial als noch nicht gesehen
        "tutorial_done": data.get("tutorial_done", False),
        "forecast": forecast(data),
        "ranks": ranks,
        "orders": [
            {**o, "label": month_label(o["month"]),
             "grade": RANKS[o["rank"]]["grade"]}
            for o in sorted(data["orders"], key=lambda o: o["month"], reverse=True)
        ],
    }
