"""
Habit Corps – Startpunkt der Anwendung.

Start:  python3 app.py
Danach öffnet sich der Browser unter http://localhost:5050

Nur Python-Standardbibliothek, keine Installation nötig.
Alle Daten liegen in data.json im selben Ordner.
"""

import json
import os
import sys
import threading
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import logic

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE, "data.json")
STATIC = os.path.join(BASE, "static")
PORT = int(os.environ.get("HABIT_PORT", 5050))

LOCK = threading.Lock()   # nur ein Schreibzugriff auf data.json gleichzeitig


def with_data(action):
    """Lädt die Daten, wertet vergangene Tage aus, führt die Aktion aus
    und speichert sofort (NFR-04)."""
    with LOCK:
        data = logic.load(DATA_FILE)
        changed = logic.catch_up(data)
        result = action(data)
        if changed or result is not None:
            logic.save(DATA_FILE, data)
        return result, logic.state(data)


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC, **kwargs)

    def log_message(self, fmt, *args):     # Konsole ruhig halten
        pass

    # ---- Hilfsfunktionen ----
    def send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def handle_api(self, method):
        parts = self.path.split("?")[0].strip("/").split("/")
        try:
            if parts == ["api", "state"] and method == "GET":
                _, st = with_data(lambda d: None)
                return self.send_json(st)

            if parts == ["api", "habits"] and method == "POST":
                body = self.read_json()
                habit, st = with_data(lambda d: logic.add_habit(
                    d, body.get("name"), body.get("goal"), body.get("reminder")))
                return self.send_json({"habit": habit, "state": st})

            if len(parts) == 4 and parts[:2] == ["api", "habits"]:
                hid, action = parts[2], parts[3]
                if action == "done" and method == "POST":
                    res, st = with_data(lambda d: logic.complete_habit(d, hid))
                    return self.send_json({"result": res, "state": st})
                if action == "reminder" and method == "POST":
                    body = self.read_json()
                    _, st = with_data(lambda d: logic.set_reminder(
                        d, hid, body.get("reminder")) or True)
                    return self.send_json({"state": st})
                if action == "delete" and method == "POST":
                    _, st = with_data(lambda d: logic.delete_habit(d, hid) or True)
                    return self.send_json({"state": st})

            return self.send_json({"error": "Unbekannte Anfrage."}, 404)
        except logic.ValidationError as e:
            return self.send_json({"error": str(e)}, 400)

    # ---- HTTP-Methoden ----
    def do_GET(self):
        if self.path.startswith("/api/"):
            return self.handle_api("GET")
        return super().do_GET()

    def do_POST(self):
        return self.handle_api("POST")


def main():
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://localhost:{PORT}"
    print(f"Habit Corps läuft auf {url}  (Beenden mit Strg+C)")
    if "--no-browser" not in sys.argv:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nWeggetreten!")


if __name__ == "__main__":
    main()
