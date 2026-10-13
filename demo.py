"""
Demo-Modus von Habit Corps.

Alle Demo-Aktionen arbeiten auf einer eigenen Datei (demo_data.json) mit einem
simulierten Datum. Die echte data.json wird dabei nie gelesen oder geschrieben.

Die Funktionen hier verwenden dieselben Spielregeln wie die echte App
(alles aus logic.py). Sie "spulen" nur die Zeit vor oder bereiten
passende Ausgangslagen vor, damit man alles sofort ausprobieren kann.
"""

import os
from datetime import date, timedelta

import logic

# Kennzeichen für künstliche XP, die "Knapp davor setzen" hinzufügt.
# Sie gehören zu keiner echten Mission.
ARCHIVE_ID = "demo-archiv"     # Platzhalter-Erledigungen für "Rang setzen"

# Die wählbaren Szenarien: interner Name -> Anzeigename
SCENARIOS = {
    "multiplikatoren": "Alle Multiplikatoren",
    "start": "Frischer Start",
    "general": "Weg zum General",
}


# Baut einen Orden-Eintrag für einen Monat (z. B. einen passenden Vormonat).
def _order(month: str, rank: int) -> dict:
    m = logic.month_max_xp(month)
    return {"month": month, "rank": rank, "rank_name": logic.RANKS[rank]["name"],
            "xp": round(logic.RANKS[rank]["pct"] / 100 * m) if logic.RANKS[rank]["pct"] is not None else m,
            "max_xp": m, "percent": logic.RANKS[rank]["pct"] or 100.0}


def build(name: str, real_today: date) -> dict:
    """Erzeugt ein frisches Demo-Szenario."""
    if name not in SCENARIOS:
        raise logic.ValidationError("Unbekanntes Szenario.")
    # Für "Weg zum General" starten wir am 1. des nächsten Monats,
    # damit ein ganzer Monat perfekt durchgespielt werden kann.
    if name == "general":
        # Erster Tag des nächsten Monats, damit ein ganzer Monat durchgespielt werden kann
        day = (real_today.replace(day=1) + timedelta(days=32)).replace(day=1)
    else:
        day = real_today
    # Ab jetzt rechnen alle Regeln mit dem Demo-Datum
    logic.set_today(day)
    data = logic.new_data(day)
    data["demo_today"] = day.isoformat()
    data["demo_scenario"] = name
    data["tutorial_done"] = True     # im Demo-Modus kein Tutorial einblenden
    prev = logic.prev_month_key(logic.month_key(day))

    # Missionen je Szenario: (Name, Start-Streak)
    if name == "start":
        habits = [("20 Liegestütze", 0), ("30 Minuten lesen", 0), ("2 Liter Wasser", 0), ("Vokabeln", 0)]
    elif name == "multiplikatoren":
        habits = [("Liegestütze (Streak 2)", 2), ("Lesen (Streak 8)", 8),
                  ("Wasser (Streak 15)", 15), ("Vokabeln (Streak 35)", 35)]
        data["orders"].append(_order(prev, 10))            # Vormonat Major
    else:
        habits = [(f"Mission {i + 1} (Streak 40)", 40) for i in range(5)]
        data["orders"].append(_order(prev, 12))            # Vormonat Brigadier General

    # Missionen anlegen und ihren Streak direkt setzen
    for title, streak in habits:
        h = logic.add_habit(data, title, "Demo-Mission")
        h["streak"] = streak
    return data


# Demo-Datei laden; gibt es sie noch nicht, wird das Standard-Szenario erzeugt.
def load(path: str, real_today: date) -> dict:
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        data = build("multiplikatoren", real_today)
        logic.save(path, data)
        return data
    import json
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# Kurzinfo für die Oberfläche: Demo-Datum und Name des Szenarios.
def info(data: dict) -> dict:
    name = data.get("demo_scenario", "multiplikatoren")
    return {"today": data["demo_today"], "scenario": name, "label": SCENARIOS.get(name, name)}


# Orden um Anzeige-Infos ergänzen (Monatsname, Dienstgrad, Anekdote).
def _with_anecdote(order: dict) -> dict:
    return {**order, "label": logic.month_label(order["month"]),
            "grade": logic.RANKS[order["rank"]]["grade"],
            "anecdote": logic.ANECDOTES[order["rank"]]}


def next_day(data: dict, mode: str = "all") -> dict:
    """Erledigt die heutigen Missionen (alle / alle bis auf eine / keine) und springt einen Tag weiter."""
    # Welche Missionen sind heute noch offen?
    day = logic.today()
    done = {c["habit_id"] for c in data["completions"] if c["date"] == day.isoformat()}
    open_h = [h for h in data["habits"] if h["id"] not in done]
    # Je nach Knopf: alle, alle bis auf eine ([:-1] = ohne das letzte Element) oder keine
    if mode == "all":
        todo = open_h
    elif mode == "miss":
        todo = open_h[:-1]
    elif mode == "none":
        todo = []
    else:
        raise logic.ValidationError("Unbekannter Modus.")

    promoted = None
    # Missionen ganz normal abhaken – wie ein Klick in der App
    for h in todo:
        res = logic.complete_habit(data, h["id"])
        if res["promoted"]:
            promoted = res["rank"]

    orders_before = {o["month"] for o in data["orders"]}
    # Einen Tag weiterspringen und den vergangenen Tag auswerten lassen
    # (Streak-Reset bei Fehltag, Orden am Monatsende)
    new_day = day + timedelta(days=1)
    data["demo_today"] = new_day.isoformat()
    logic.set_today(new_day)
    logic.catch_up(data, new_day)
    new_orders = [_with_anecdote(o) for o in data["orders"] if o["month"] not in orders_before]
    return {
        "day": new_day.isoformat(),
        "completed": len(todo),
        "missed": len(open_h) - len(todo),
        "reset": data.get("last_reset") == day.isoformat(),
        "promoted": promoted,
        "new_orders": new_orders,
    }


def end_month(data: dict) -> dict:
    """Spielt den Rest des Monats durch (jeden Tag alles erledigt)."""
    start_month = logic.month_key(logic.today())
    total = {"days": 0, "new_orders": [], "promoted": None}
    # So lange Tage vorspulen, bis ein neuer Monat beginnt
    while logic.month_key(logic.today()) == start_month:
        res = next_day(data, "all")
        total["days"] += 1
        total["new_orders"] += res["new_orders"]
        if res["promoted"] is not None:
            total["promoted"] = res["promoted"]
    total["day"] = data["demo_today"]
    return total


def set_rank(data: dict, rank: int) -> dict:
    """Setzt die Monats-XP knapp (5 XP) unter die Schwelle des Zielrangs."""
    if not 1 <= rank <= 13:
        raise logic.ValidationError("Rang muss zwischen 1 und 13 liegen.")
    now = logic.today()
    key = logic.month_key(now)
    # Frühere künstliche XP dieses Monats entfernen, damit nichts doppelt zählt
    data["completions"] = [c for c in data["completions"]
                           if not (c["habit_id"] == ARCHIVE_ID and c["date"].startswith(key))]

    # Vormonat passend setzen, damit Colonel / Brigadier General erreichbar sind
    # Hohe Ränge brauchen einen passenden Vormonat – den tragen wir bei Bedarf ein
    need_prev = logic.RANKS[rank]["prev"]
    if need_prev is not None:
        prev_key = logic.prev_month_key(key)
        old = logic.order_for(data, prev_key)
        if not old or old["rank"] < need_prev:
            if old:
                data["orders"].remove(old)
            data["orders"].append(_order(prev_key, need_prev))

    # General während des Monats setzt einen früheren General-Orden voraus
    if rank == logic.GENERAL and not logic.general_unlocked(data, key):
        # General freischalten: früherer General-Orden vor dem Vormonat
        older = logic.prev_month_key(logic.prev_month_key(key))
        if not logic.order_for(data, older):
            data["orders"].append(_order(older, logic.GENERAL))

    # Fehlende XP berechnen: Schwelle minus 5 minus vorhandene XP
    m = logic.month_max_xp(key)
    pct = logic.GENERAL_LIVE_PCT if rank == logic.GENERAL else logic.RANKS[rank]["pct"]
    missing = pct / 100 * m - 5 - logic.month_xp(data, key)
    # In Portionen zu höchstens 30 XP als künstliche Erledigungen eintragen
    while missing > 0:
        chunk = min(30, round(missing, 2))
        data["completions"].append({"habit_id": ARCHIVE_ID, "date": now.isoformat(), "time": "00:00:00",
                                    "streak": 0, "multiplier": 1.0, "xp": chunk})
        missing = round(missing - chunk, 2)
    return {"rank": rank, "name": logic.RANKS[rank]["name"]}


# Szenario laden: den kompletten Demo-Stand durch ein frisches Szenario ersetzen.
# .clear() leert das Dictionary, .update() füllt es mit den neuen Werten.
def load_scenario(data: dict, name: str, real_today: date) -> dict:
    new = build(name, real_today)
    data.clear()
    data.update(new)
    return info(data)
