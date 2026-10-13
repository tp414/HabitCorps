"""Tests der Spiellogik. Start: python3 test_logic.py

Was ist ein automatischer Test?
  Ein kleines Programm, das die Spielregeln mit festen Beispielen ausprobiert
  und prüft, ob genau das erwartete Ergebnis herauskommt. Zeigt die Ausgabe
  am Ende "OK", funktionieren alle Regeln. Bei "FAILED" steht dabei, welcher
  Test nicht gestimmt hat.

Aufbau:
  - Jede "class Test..." fasst Tests zu einem Thema zusammen.
  - Jede Funktion, die mit "test_" beginnt, ist ein einzelner Test.
  - self.assertEqual(a, b)  prüft: a muss gleich b sein
  - self.assertTrue(x)      prüft: x muss wahr sein
  - self.assertRaises(...)  prüft: hier MUSS ein Fehler gemeldet werden
"""
# unittest = das Test-Werkzeug von Python. "import logic as L" lädt unsere
# Spielregeln unter dem kurzen Namen L (also L.add_habit statt logic.add_habit).
import os, tempfile, unittest
from datetime import date, timedelta
import logic as L


# Tut so, als wäre heute der Tag d (über die Umgebungsvariable HABIT_TODAY).
# So können Tests Wochen und Monate in Sekunden durchspielen.
def set_day(d):
    os.environ["HABIT_TODAY"] = d.isoformat()


# Gemeinsame Grundlage für viele Tests: Startdatum 1. September 2026, leerer Spielstand.
class Base(unittest.TestCase):
    # setUp läuft automatisch VOR jedem einzelnen Test -> jeder Test startet frisch
    def setUp(self):
        self.start = date(2026, 9, 1)
        set_day(self.start)
        self.data = L.new_data(self.start)

    # Zu einem Tag springen und alle vergangenen Tage auswerten lassen
    def day(self, d):
        set_day(d)
        L.catch_up(self.data, d)

    # n Tage hintereinander alle Missionen abhaken (optional eine auslassen)
    def run_days(self, start, n, habits, skip=None):
        """Erledigt n Tage lang alle Habits; skip=(tag_index, habit) lässt einen aus."""
        for i in range(n):
            d = start + timedelta(days=i)
            self.day(d)
            for h in habits:
                if skip and skip == (i, h["id"]):
                    continue
                L.complete_habit(self.data, h["id"])


# === Grundregeln: Eingaben, Abhaken, Streak, Multiplikator, Monatswechsel ===
class TestRules(Base):
    # Ungültige Eingaben (leerer Name, zu lang) müssen abgelehnt werden
    def test_validation(self):
        with self.assertRaises(L.ValidationError):
            L.add_habit(self.data, "   ")
        with self.assertRaises(L.ValidationError):
            L.add_habit(self.data, "x" * 51)
        with self.assertRaises(L.ValidationError):
            L.add_habit(self.data, "ok", "y" * 201)
        h = L.add_habit(self.data, "x" * 50, "y" * 200, "07:30")
        self.assertEqual(h["reminder"], "07:30")

    # Eine Mission darf pro Tag nur einmal abgehakt werden
    def test_once_per_day(self):
        h = L.add_habit(self.data, "Laufen")
        L.complete_habit(self.data, h["id"])
        with self.assertRaises(L.ValidationError):
            L.complete_habit(self.data, h["id"])

    # Nach 7 Tagen steigt der Multiplikator auf x1,5 -> 15 XP statt 10
    def test_streak_and_multiplier(self):
        h = L.add_habit(self.data, "Laufen")
        self.run_days(self.start, 7, [h])
        self.assertEqual(h["streak"], 7)
        last = self.data["completions"][-1]
        self.assertEqual(last["multiplier"], 1.5)
        self.assertEqual(last["xp"], 15)
        self.assertEqual(L.month_xp(self.data, "2026-09"), 6 * 10 + 15)

    # Eine verpasste Mission setzt ALLE Streaks auf 0
    def test_one_miss_resets_all(self):
        a = L.add_habit(self.data, "A")
        b = L.add_habit(self.data, "B")
        self.run_days(self.start, 5, [a, b], skip=(4, b["id"]))
        self.assertEqual(a["streak"], 5)
        self.day(self.start + timedelta(days=5))   # Tag 5 ausgewertet
        self.assertEqual(a["streak"], 0)
        self.assertEqual(b["streak"], 0)
        L.complete_habit(self.data, a["id"])
        self.assertEqual(a["streak"], 1)

    # Eine neue Mission zählt ab dem Tag, an dem sie angelegt wurde
    def test_new_habit_due_from_creation(self):
        a = L.add_habit(self.data, "A")
        self.run_days(self.start, 3, [a])
        set_day(self.start + timedelta(days=3))
        b = L.add_habit(self.data, "B")           # neu, heute fällig
        L.complete_habit(self.data, a["id"])
        self.day(self.start + timedelta(days=4))
        self.assertEqual(a["streak"], 0)          # B verpasst -> Reset

    # Monatsende: Orden wird gespeichert, XP starten neu, Streaks bleiben
    def test_month_end_order_and_reset(self):
        a = L.add_habit(self.data, "A")
        self.run_days(self.start, 30, [a])        # ganzer September
        self.day(date(2026, 10, 1))
        o = L.order_for(self.data, "2026-09")
        self.assertIsNotNone(o)
        self.assertEqual(L.month_xp(self.data, "2026-10"), 0)   # FR-24
        self.assertEqual(a["streak"], 30)                       # FR-25
        st = L.state(self.data)
        self.assertEqual(st["rank"]["name"], "Private")

    # Beförderung wird erst gemeldet, wenn die XP-Schwelle wirklich erreicht ist
    def test_promotion_flag(self):
        hs = [L.add_habit(self.data, f"H{i}") for i in range(5)]
        res = [L.complete_habit(self.data, h["id"]) for h in hs]
        # 50 XP < 5 % von 4500 (=225) -> keine Beförderung am ersten Tag
        self.assertFalse(any(r["promoted"] for r in res))
        self.run_days(self.start + timedelta(days=1), 4, hs)
        promos = [c for c in self.data["completions"]]
        self.assertEqual(L.rank_for(self.data, "2026-09")[0], 1)   # 250 XP -> PFC

    # Monats-Maximum M: 5 x 10 x 3 x Tage (31 Tage -> 4650, 28 Tage -> 4200)
    def test_month_max(self):
        self.assertEqual(L.month_max_xp("2026-10"), 4650)
        self.assertEqual(L.month_max_xp("2026-02"), 4200)


# === Die höchsten Ränge und ihre Vormonatsbedingungen ===
class TestTopRanks(Base):
    def full_month(self, start, habits, skip=None):
        days = L.days_in_month(L.month_key(start))
        self.run_days(start, days, habits, skip)

    # Der Weg nach oben über vier Monate: Major -> Colonel -> Brigadier General -> General
    def test_general_path(self):
        # August: Streak auf 30 aufbauen (Start schon am 2026-08-01)
        self.data = L.new_data(date(2026, 8, 1))
        set_day(date(2026, 8, 1))
        hs = [L.add_habit(self.data, f"H{i}") for i in range(5)]
        months = [date(2026, 8, 1), date(2026, 9, 1), date(2026, 10, 1),
                  date(2026, 11, 1), date(2026, 12, 1)]
        for m in months:
            self.full_month(m, hs)
        self.day(date(2027, 1, 1))
        ranks = {o["month"]: o["rank_name"] for o in self.data["orders"]}
        # August: Aufbau, Sept: 100 % aber Vormonat zu niedrig
        self.assertEqual(ranks["2026-09"], "Major")
        self.assertEqual(ranks["2026-10"], "Colonel")
        self.assertEqual(ranks["2026-11"], "Brigadier General")
        self.assertEqual(ranks["2026-12"], "General")

    # Ein einziger Fehltag am Monatsende verhindert den ersten General
    def test_general_needs_every_day(self):
        self.data = L.new_data(date(2026, 8, 1))
        set_day(date(2026, 8, 1))
        hs = [L.add_habit(self.data, f"H{i}") for i in range(5)]
        for m in [date(2026, 8, 1), date(2026, 9, 1), date(2026, 10, 1), date(2026, 11, 1)]:
            self.full_month(m, hs)
        # Dezember: ein Habit am 31. verpasst
        self.full_month(date(2026, 12, 1), hs, skip=(30, hs[0]["id"]))
        self.day(date(2027, 1, 1))
        self.assertEqual(L.order_for(self.data, "2026-12")["rank_name"], "Brigadier General")

    # Viele Missionen allein reichen nicht: ohne Vormonat höchstens Major
    def test_many_habits_no_shortcut(self):
        # 10 Habits, ohne Vormonat: höchstens Major
        hs = [L.add_habit(self.data, f"H{i}") for i in range(10)]
        self.full_month(self.start, hs)
        self.day(date(2026, 10, 1))
        self.assertEqual(L.order_for(self.data, "2026-09")["rank_name"], "Major")


# === Rang-Prognose (Markov-Kette + dynamische Programmierung) ===
class TestForecast(Base):
    # Unabhängige Gegenprobe: 20.000 Monate zufällig durchspielen und zählen.
    # Die exakte Prognose muss fast dieselben Prozentwerte liefern.
    def monte_carlo(self, p, q, runs=20000, seed=1):
        """Unabhängige Kontrolle: Monat zufällig durchspielen."""
        import random, copy
        rnd = random.Random(seed)
        key = L.month_key(L.today())
        counts = [0] * len(L.RANKS)
        prev = L.order_for(self.data, L.prev_month_key(key))
        prev_rank = prev["rank"] if prev else -1
        for _ in range(runs):
            streaks = [h["streak"] for h in self.data["habits"]]
            xp = L.month_xp(self.data, key)
            days = L.days_in_month(key) - L.today().day + 1
            for _d in range(days):
                gain = sum(10 * L.multiplier_for(s + 1) for s in streaks)
                if rnd.random() < p:
                    xp += gain; streaks = [s + 1 for s in streaks]
                else:
                    xp += round(q * gain / 5) * 5; streaks = [0] * len(streaks)
            counts[L._rank_from_xp(xp, L.month_max_xp(key), prev_rank)] += 1
        return [c / runs for c in counts]

    # Ohne Missionen gibt es keine Prognose
    def test_no_habits(self):
        self.assertIsNone(L.forecast(self.data))

    # Alle Wahrscheinlichkeiten zusammen ergeben 100 %
    def test_sums_to_one(self):
        for i in range(4):
            L.add_habit(self.data, f"H{i}")
        f = L.forecast(self.data)
        self.assertAlmostEqual(sum(x["p"] for x in f["probabilities"]), 1.0, places=2)

    # Bei p = 100 % muss die Prognose genau mit dem echten Ergebnis übereinstimmen
    def test_certain_future(self):
        hs = [L.add_habit(self.data, f"H{i}") for i in range(5)]
        f = L.forecast(self.data, p=1.0, q=0.5)
        # 5 Habits, 30 Tage September ohne Fehltag: 6x10+7x15+16x20+1x30 = 515 je Habit
        self.assertEqual(f["expected_xp"], 5 * 515)
        self.assertEqual(f["likely"]["p"], 1.0)
        self.run_days(self.start, 30, hs)
        self.assertEqual(L.rank_for(self.data, "2026-09")[0], f["likely"]["index"])

    # Prognose und Zufallssimulation dürfen höchstens 1,5 Prozentpunkte abweichen
    def test_matches_monte_carlo(self):
        hs = [L.add_habit(self.data, f"H{i}") for i in range(4)]
        self.run_days(self.start, 6, hs)            # Stand: 7. September, Streak 6
        set_day(self.start + timedelta(days=6)); L.catch_up(self.data, self.start + timedelta(days=6))
        for p in (0.6, 0.85):
            exact = {x["index"]: x["p"] for x in L.forecast(self.data, p=p, q=0.5)["probabilities"]}
            mc = self.monte_carlo(p, 0.5)
            for i, v in enumerate(mc):
                self.assertAlmostEqual(exact.get(i, 0), v, delta=0.015)

    # Wahrscheinlichkeit für den ersten General = p hoch Anzahl der Tage
    def test_general_probability(self):
        self.data = L.new_data(date(2026, 8, 1))
        set_day(date(2026, 8, 1))
        hs = [L.add_habit(self.data, f"H{i}") for i in range(5)]
        for m in [date(2026, 8, 1), date(2026, 9, 1), date(2026, 10, 1), date(2026, 11, 1)]:
            self.run_days(m, L.days_in_month(L.month_key(m)), hs)
        self.day(date(2026, 12, 1))
        f = L.forecast(self.data, p=0.9, q=0.5)
        gen = {x["index"]: x["p"] for x in f["probabilities"]}[L.GENERAL]
        self.assertAlmostEqual(gen, 0.9 ** 31, places=4)

    # Schätzung von p aus dem Verlauf (9 von 10 Tagen geschafft)
    def test_estimate(self):
        a = L.add_habit(self.data, "A")
        self.run_days(self.start, 10, [a], skip=(4, a["id"]))   # 9 von 10 Tagen
        set_day(self.start + timedelta(days=10))
        p, q, full, days = L.estimate_behaviour(self.data, self.start + timedelta(days=10))
        self.assertEqual((full, days), (9, 10))
        self.assertAlmostEqual(p, (9 + 2) / (10 + 3))

    # Die Prognose muss schnell sein (unter 1 Sekunde)
    def test_runtime(self):
        import time
        set_day(date(2026, 10, 1))
        self.data = L.new_data(date(2026, 10, 1))
        for i in range(12):
            L.add_habit(self.data, f"H{i}")
        t = time.perf_counter(); L.forecast(self.data); dt = time.perf_counter() - t
        print(f"\nPrognose 12 Habits, 31 Tage: {dt*1000:.0f} ms")
        self.assertLess(dt, 1.0)


# === General während des Monats (nach dem ersten General-Orden) ===
class TestLiveGeneral(Base):
    # Hilfsfunktion: mehrere Monate perfekt durchspielen
    def history(self, habits, months):
        """Ab August durchspielen. Aug Aufbau, Sep Major, Okt Colonel, Nov BG, Dez erster General."""
        self.data = L.new_data(date(2026, 8, 1))
        set_day(date(2026, 8, 1))
        hs = [L.add_habit(self.data, f"H{i}") for i in range(habits)]
        for m in months:
            self.run_days(m, L.days_in_month(L.month_key(m)), hs)
        return hs

    AUG_NOV = [date(2026, 8, 1), date(2026, 9, 1), date(2026, 10, 1), date(2026, 11, 1)]
    AUG_DEC = AUG_NOV + [date(2026, 12, 1)]

    # Vor dem ersten General-Orden gibt es keinen General mitten im Monat
    def test_not_live_before_first_general(self):
        hs = self.history(7, self.AUG_NOV)
        self.run_days(date(2026, 12, 1), 28, hs)          # 100 % schon überschritten
        self.assertGreaterEqual(L.month_xp(self.data, "2026-12"), L.month_max_xp("2026-12"))
        self.assertEqual(L.rank_for(self.data, "2026-12")[0], 12)   # nur Brigadier General
        self.run_days(date(2026, 12, 29), 3, hs)
        self.day(date(2027, 1, 1))
        self.assertEqual(L.order_for(self.data, "2026-12")["rank_name"], "General")  # Orden am Monatsende

    # Danach: mit 7 Missionen wird man am 23. Tag General
    def test_live_general_mid_month(self):
        hs = self.history(7, self.AUG_DEC)
        promoted_on = None
        for i in range(31):                       # Jänner: 7 x 30 = 210 XP/Tag, 100 % = 4650
            d = date(2027, 1, 1) + timedelta(days=i)
            self.day(d)
            for h in hs:
                res = L.complete_habit(self.data, h["id"])
                if res["promoted"] and res["rank"] == L.GENERAL and promoted_on is None:
                    promoted_on = d.day
        self.assertEqual(promoted_on, 23)

    # Mit genau 5 Missionen klappt es erst am letzten Tag
    def test_five_habits_reach_general_on_last_day(self):
        hs = self.history(5, self.AUG_DEC)
        self.run_days(date(2027, 1, 1), 30, hs)
        self.assertEqual(L.rank_for(self.data, "2027-01")[0], 11)   # 4500/4650 = 96,8 % -> Colonel
        self.day(date(2027, 1, 31))
        for h in hs:
            L.complete_habit(self.data, h["id"])
        self.assertEqual(L.rank_for(self.data, "2027-01")[0], L.GENERAL)

    # Die Vormonatsbedingung gilt weiterhin
    def test_prev_month_still_required(self):
        hs = self.history(7, self.AUG_DEC)
        self.run_days(date(2027, 1, 1), 31, hs, skip=(0, hs[0]["id"]))   # Jänner: Fehltag am 1.
        self.day(date(2027, 2, 1))
        self.assertLess(L.order_for(self.data, "2027-01")["rank"], 12)
        self.run_days(date(2027, 2, 1), 28, hs)
        self.assertLess(L.rank_for(self.data, "2027-02")[0], L.GENERAL)

    # Die Prognose kennt den freigeschalteten General
    def test_forecast_counts_live_general(self):
        hs = self.history(7, self.AUG_DEC)
        self.day(date(2027, 1, 1))
        f = L.forecast(self.data, p=1.0, q=0.5)
        self.assertEqual(f["likely"]["name"], "General")
        st = L.state(self.data)
        self.assertTrue(st["general_unlocked"])
        self.assertEqual(st["ranks"][L.GENERAL]["pct"], 100)


# === Demo-Modus ===
class TestDemo(unittest.TestCase):
    def setUp(self):
        import demo
        self.demo = demo
        L.set_today(None)
        self.real = date(2026, 10, 8)

    # tearDown läuft automatisch NACH jedem Test: simuliertes Datum wieder abschalten
    def tearDown(self):
        L.set_today(None)

    # "+1 Tag · eine verpasst" setzt alle Streaks zurück
    def test_next_day_miss_resets_all(self):
        d = self.demo.build("multiplikatoren", self.real)
        res = self.demo.next_day(d, "miss")
        self.assertEqual((res["completed"], res["missed"], res["reset"]), (3, 1, True))
        self.assertTrue(all(h["streak"] == 0 for h in d["habits"]))
        self.assertEqual(d["demo_today"], "2026-10-09")

    # "+1 Tag · alles erledigt" erhöht jeden Streak um 1
    def test_next_day_all_keeps_streaks(self):
        d = self.demo.build("multiplikatoren", self.real)
        self.demo.next_day(d, "all")
        self.assertEqual([h["streak"] for h in d["habits"]], [3, 9, 16, 36])

    # "Knapp davor setzen" + einmal abhaken = Beförderung
    def test_set_rank_then_promote(self):
        d = self.demo.build("multiplikatoren", self.real)
        for rank in (3, 9, 11, 12, 13):
            d = self.demo.build("multiplikatoren", self.real)
            self.demo.set_rank(d, rank)
            self.assertEqual(L.rank_for(d, "2026-10")[0], rank - 1)
            res = L.complete_habit(d, d["habits"][0]["id"])
            self.assertTrue(res["promoted"])
            self.assertEqual(res["rank"], rank)

    # Szenario "Weg zum General" + "Monat abschließen" ergibt den General-Orden
    def test_general_scenario(self):
        d = self.demo.build("general", self.real)
        self.assertEqual(d["demo_today"], "2026-11-01")
        res = self.demo.end_month(d)
        self.assertEqual(res["days"], 30)
        self.assertEqual(res["new_orders"][0]["rank_name"], "General")

    # "Monat abschließen" springt in den nächsten Monat und verleiht einen Orden
    def test_end_month_gives_order(self):
        d = self.demo.build("start", self.real)
        res = self.demo.end_month(d)
        self.assertEqual(len(res["new_orders"]), 1)
        self.assertEqual(d["demo_today"], "2026-11-01")

    # WICHTIG: Der Demo-Modus darf data.json nicht verändern.
    # Prüfung über einen "Fingerabdruck" (MD5-Prüfsumme) vorher und nachher.
    def test_real_data_untouched(self):
        import app, hashlib, json as _json
        with tempfile.TemporaryDirectory() as tmp:
            real = os.path.join(tmp, "data.json")
            with open(real, "w") as f:
                _json.dump(L.new_data(date(2026, 10, 1)), f)
            before = hashlib.md5(open(real, "rb").read()).hexdigest()
            app.DATA_FILE, app.DEMO_FILE = real, os.path.join(tmp, "demo_data.json")
            app.with_data(lambda d: self.demo.next_day(d, "all"), True)
            app.with_data(lambda d: self.demo.end_month(d), True)
            app.with_data(lambda d: self.demo.set_rank(d, 5), True)
            self.assertEqual(hashlib.md5(open(real, "rb").read()).hexdigest(), before)
            self.assertIsNone(L._today_override)


# === Tutorial und Neustart (FR-33, FR-34) ===
class TestTutorialReset(Base):
    # Ein neuer Spielstand zeigt das Tutorial, danach nicht mehr
    def test_tutorial_flag(self):
        self.assertFalse(L.state(self.data)["tutorial_done"])
        L.finish_tutorial(self.data)
        self.assertTrue(L.state(self.data)["tutorial_done"])

    # Ältere data.json ohne Eintrag -> Tutorial wird einmal gezeigt
    def test_old_file_shows_tutorial(self):
        del self.data["tutorial_done"]
        self.assertFalse(L.state(self.data)["tutorial_done"])

    # Neustart: alles weg, Sicherungskopie mit dem alten Stand vorhanden
    def test_reset_with_backup(self):
        import json as _json
        a = L.add_habit(self.data, "A")
        self.run_days(self.start, 10, [a])
        L.finish_tutorial(self.data)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "data.json")
            res = L.reset_progress(self.data, path)
            self.assertEqual(self.data["habits"], [])
            self.assertEqual(self.data["completions"], [])
            self.assertFalse(self.data["tutorial_done"])          # Tutorial startet neu
            backup = _json.load(open(os.path.join(tmp, res["backup"]), encoding="utf-8"))
            self.assertEqual(backup["habits"][0]["name"], "A")       # alter Stand gesichert
            self.assertEqual(len(backup["completions"]), 10)

    # Neustart im Demo-Modus darf data.json nicht verändern
    def test_demo_reset_keeps_real_data(self):
        import app, hashlib, json as _json
        with tempfile.TemporaryDirectory() as tmp:
            real = os.path.join(tmp, "data.json")
            with open(real, "w") as f:
                _json.dump(L.new_data(date(2026, 10, 1)), f)
            before = hashlib.md5(open(real, "rb").read()).hexdigest()
            app.DATA_FILE, app.DEMO_FILE = real, os.path.join(tmp, "demo_data.json")
            import demo
            app.with_data(lambda d: demo.load_scenario(d, "start", date(2026, 10, 12)), True)
            self.assertEqual(hashlib.md5(open(real, "rb").read()).hexdigest(), before)
            self.assertFalse(os.path.exists(os.path.join(tmp, "backups")))
            L.set_today(None)


# === Online-Betrieb (z. B. Render) ===
class TestOnlineConfig(unittest.TestCase):
    # Lokal: nur eigener Rechner, Port 5050. Online (PORT gesetzt): offen für alle, Port vom Anbieter.
    def check(self, env, host, port, online):
        import subprocess, sys
        code = "import app; print(app.HOST, app.PORT, app.ONLINE)"
        e = {k: v for k, v in os.environ.items() if k not in ("PORT", "HABIT_PORT")}
        e.update(env)
        out = subprocess.run([sys.executable, "-c", code], env=e, capture_output=True, text=True,
                             cwd=os.path.dirname(os.path.abspath(__file__))).stdout.split()
        self.assertEqual(out, [host, str(port), str(online)])

    def test_local(self):
        self.check({}, "127.0.0.1", 5050, False)

    def test_online(self):
        self.check({"PORT": "10000"}, "0.0.0.0", 10000, True)


# === Speichern und Geschwindigkeit ===
class TestPersistence(unittest.TestCase):
    # Speichern und wieder Laden liefert dieselben Daten, keine Restdateien
    def test_roundtrip(self):
        set_day(date(2026, 10, 8))
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "data.json")
            data = L.load(p)
            L.add_habit(data, "Lesen")
            L.save(p, data)
            self.assertEqual(L.load(p)["habits"][0]["name"], "Lesen")
            self.assertEqual([f for f in os.listdir(d)], ["data.json"])

    # NFR-06: 100 Missionen x 365 Tage Verlauf in unter 2 Sekunden
    def test_performance(self):
        import time
        set_day(date(2026, 10, 8))
        data = L.new_data(date(2025, 10, 8))
        data["last_processed"] = "2026-10-07"
        for i in range(100):
            data["habits"].append({"id": f"h{i}", "name": f"H{i}", "goal": "",
                                   "created": "2025-10-08", "streak": 0, "reminder": None})
        d0 = date(2025, 10, 8)
        for k in range(365):
            day = (d0 + timedelta(days=k)).isoformat()
            for i in range(100):
                data["completions"].append({"habit_id": f"h{i}", "date": day, "time": "08:00:00",
                                            "streak": 1, "multiplier": 1.0, "xp": 10})
        t = time.perf_counter(); L.state(data); dt = time.perf_counter() - t
        print(f"\nstate() bei 100 Habits x 365 Tagen: {dt*1000:.0f} ms")
        self.assertLess(dt, 2.0)


# Startet alle Tests, wenn man "python3 test_logic.py" ausführt
if __name__ == "__main__":
    unittest.main(verbosity=2)
