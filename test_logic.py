"""Tests der Spiellogik. Start: python3 test_logic.py"""
import os, tempfile, unittest
from datetime import date, timedelta
import logic as L


def set_day(d):
    os.environ["HABIT_TODAY"] = d.isoformat()


class Base(unittest.TestCase):
    def setUp(self):
        self.start = date(2026, 9, 1)
        set_day(self.start)
        self.data = L.new_data(self.start)

    def day(self, d):
        set_day(d)
        L.catch_up(self.data, d)

    def run_days(self, start, n, habits, skip=None):
        """Erledigt n Tage lang alle Habits; skip=(tag_index, habit) lässt einen aus."""
        for i in range(n):
            d = start + timedelta(days=i)
            self.day(d)
            for h in habits:
                if skip and skip == (i, h["id"]):
                    continue
                L.complete_habit(self.data, h["id"])


class TestRules(Base):
    def test_validation(self):
        with self.assertRaises(L.ValidationError):
            L.add_habit(self.data, "   ")
        with self.assertRaises(L.ValidationError):
            L.add_habit(self.data, "x" * 51)
        with self.assertRaises(L.ValidationError):
            L.add_habit(self.data, "ok", "y" * 201)
        h = L.add_habit(self.data, "x" * 50, "y" * 200, "07:30")
        self.assertEqual(h["reminder"], "07:30")

    def test_once_per_day(self):
        h = L.add_habit(self.data, "Laufen")
        L.complete_habit(self.data, h["id"])
        with self.assertRaises(L.ValidationError):
            L.complete_habit(self.data, h["id"])

    def test_streak_and_multiplier(self):
        h = L.add_habit(self.data, "Laufen")
        self.run_days(self.start, 7, [h])
        self.assertEqual(h["streak"], 7)
        last = self.data["completions"][-1]
        self.assertEqual(last["multiplier"], 1.5)
        self.assertEqual(last["xp"], 15)
        self.assertEqual(L.month_xp(self.data, "2026-09"), 6 * 10 + 15)

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

    def test_new_habit_due_from_creation(self):
        a = L.add_habit(self.data, "A")
        self.run_days(self.start, 3, [a])
        set_day(self.start + timedelta(days=3))
        b = L.add_habit(self.data, "B")           # neu, heute fällig
        L.complete_habit(self.data, a["id"])
        self.day(self.start + timedelta(days=4))
        self.assertEqual(a["streak"], 0)          # B verpasst -> Reset

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

    def test_promotion_flag(self):
        hs = [L.add_habit(self.data, f"H{i}") for i in range(5)]
        res = [L.complete_habit(self.data, h["id"]) for h in hs]
        # 50 XP < 5 % von 4500 (=225) -> keine Beförderung am ersten Tag
        self.assertFalse(any(r["promoted"] for r in res))
        self.run_days(self.start + timedelta(days=1), 4, hs)
        promos = [c for c in self.data["completions"]]
        self.assertEqual(L.rank_for(self.data, "2026-09")[0], 1)   # 250 XP -> PFC

    def test_month_max(self):
        self.assertEqual(L.month_max_xp("2026-10"), 4650)
        self.assertEqual(L.month_max_xp("2026-02"), 4200)


class TestTopRanks(Base):
    def full_month(self, start, habits, skip=None):
        days = L.days_in_month(L.month_key(start))
        self.run_days(start, days, habits, skip)

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

    def test_many_habits_no_shortcut(self):
        # 10 Habits, ohne Vormonat: höchstens Major
        hs = [L.add_habit(self.data, f"H{i}") for i in range(10)]
        self.full_month(self.start, hs)
        self.day(date(2026, 10, 1))
        self.assertEqual(L.order_for(self.data, "2026-09")["rank_name"], "Major")


class TestPersistence(unittest.TestCase):
    def test_roundtrip(self):
        set_day(date(2026, 10, 8))
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "data.json")
            data = L.load(p)
            L.add_habit(data, "Lesen")
            L.save(p, data)
            self.assertEqual(L.load(p)["habits"][0]["name"], "Lesen")
            self.assertEqual([f for f in os.listdir(d)], ["data.json"])

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
