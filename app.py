"""
Habit Corps – Startpunkt der Anwendung.

Start:  python3 app.py
Danach öffnet sich der Browser unter http://localhost:5050

Nur Python-Standardbibliothek, keine Installation nötig.
Alle Daten liegen in data.json im selben Ordner.

Kurz erklärt, was diese Datei macht:
  Sie startet einen kleinen Webserver auf dem eigenen Computer. Der Browser
  zeigt die Oberfläche (Ordner "static") an und fragt bei jeder Aktion
  (z. B. "Mission abhaken") beim Server nach. Der Server ruft dann die
  Spielregeln in logic.py auf, speichert alles in data.json und schickt
  den neuen Zustand als JSON (ein Textformat für Daten) zurück.

Python-Grundlagen, die hier vorkommen:
  - Zeilen, die mit # beginnen, sind Kommentare und werden nicht ausgeführt.
  - Text zwischen drei Anführungszeichen (wie dieser hier) ist ein
    "Docstring": eine Beschreibung, die ebenfalls nicht ausgeführt wird.
  - "def name(...):" definiert eine Funktion, also einen benannten Ablauf,
    den man später aufrufen kann.
  - Python erkennt anhand der Einrückung (Leerzeichen am Zeilenanfang),
    welche Zeilen zusammengehören.
"""

# ---------------------------------------------------------------------------
# Importe: fertige Bausteine laden, die Python schon mitbringt
# ---------------------------------------------------------------------------
import json            # Daten in JSON-Text umwandeln und zurück
import os              # mit Dateien und Ordnern arbeiten
import sys             # Zugriff auf die Startparameter des Programms
import threading       # mehrere Dinge gleichzeitig erledigen
import webbrowser      # den Browser automatisch öffnen
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer   # der Webserver

from datetime import date   # Datumsangaben (Tag, Monat, Jahr)

# Unsere eigenen Dateien: demo.py (Demo-Modus) und logic.py (Spielregeln)
import demo
import logic

# ---------------------------------------------------------------------------
# Einstellungen (in GROSSBUCHSTABEN geschrieben = sollen sich nicht ändern)
# ---------------------------------------------------------------------------
# BASE ist der Ordner, in dem diese Datei liegt. Alle anderen Pfade bauen darauf auf.
BASE = os.path.dirname(os.path.abspath(__file__))
# Pfad zur Datei mit den echten Daten
DATA_FILE = os.path.join(BASE, "data.json")
DEMO_FILE = os.path.join(BASE, "demo_data.json")   # Demo-Modus, getrennt von data.json
# Ordner mit der Oberfläche (HTML, CSS, JavaScript)
STATIC = os.path.join(BASE, "static")
# Port = "Hausnummer" des Servers. Standard ist 5050, kann über eine
# Umgebungsvariable HABIT_PORT geändert werden. int(...) macht aus Text eine Zahl.
PORT = int(os.environ.get("HABIT_PORT", 5050))

# Ein "Lock" ist wie ein Schlüssel: Nur wer ihn hat, darf auf die Datei
# zugreifen. So schreiben nie zwei Anfragen gleichzeitig in data.json.
LOCK = threading.Lock()   # nur ein Schreibzugriff auf data.json gleichzeitig


def with_data(action, is_demo=False):
    """Lädt die Daten, wertet vergangene Tage aus, führt die Aktion aus
    und speichert sofort (NFR-04). Im Demo-Modus wird ausschließlich
    demo_data.json mit simuliertem Datum verwendet.

    "action" ist selbst eine Funktion, die übergeben wird – also das,
    was gerade passieren soll (z. B. eine Mission abhaken).
    Rückgabe: das Ergebnis der Aktion und der neue Gesamtzustand.
    """
    # "with LOCK:" = Schlüssel nehmen; am Ende des Blocks wird er automatisch zurückgegeben
    with LOCK:
        # Je nach Modus die echte Datei oder die Demo-Datei verwenden
        path = DEMO_FILE if is_demo else DATA_FILE
        # try/finally: Der finally-Teil läuft IMMER, auch wenn vorher ein Fehler passiert
        try:
            if is_demo:
                # Demo: Demo-Datei laden und das simulierte Datum aktivieren
                data = demo.load(path, date.today())
                logic.set_today(date.fromisoformat(data["demo_today"]))
            else:
                # Echtbetrieb: echtes Datum verwenden und data.json laden
                logic.set_today(None)
                data = logic.load(path)
            # Alle Tage seit dem letzten Aufruf auswerten (Streak-Reset, Monatsorden)
            changed = logic.catch_up(data)
            # Die eigentliche Aktion ausführen
            result = action(data)
            # Nur speichern, wenn sich wirklich etwas geändert hat
            if changed or result is not None:
                logic.save(path, data)
            # Den Zustand für die Oberfläche zusammenstellen
            st = logic.state(data)
            st["demo"] = demo.info(data) if is_demo else None
            return result, st
        finally:
            # Simuliertes Datum wieder abschalten, damit nichts "hängen bleibt"
            logic.set_today(None)


class Handler(SimpleHTTPRequestHandler):
    """Beantwortet die Anfragen des Browsers.

    Eine "class" ist ein Bauplan, der Daten und Funktionen bündelt.
    Diese Klasse übernimmt (erbt) alles vom fertigen SimpleHTTPRequestHandler,
    der schon Dateien ausliefern kann, und ergänzt unsere eigenen Befehle.
    """

    def __init__(self, *args, **kwargs):
        # Beim Erzeugen festlegen, dass Dateien aus dem Ordner "static" kommen
        super().__init__(*args, directory=STATIC, **kwargs)

    def log_message(self, fmt, *args):     # Konsole ruhig halten
        # Normalerweise schreibt der Server jede Anfrage ins Terminal.
        # "pass" bedeutet: nichts tun – so bleibt das Terminal übersichtlich.
        pass

    # ---- Hilfsfunktionen ----
    def send_json(self, payload, status=200):
        """Schickt Daten als JSON an den Browser.
        status 200 = alles ok, 400 = Eingabefehler, 404 = nicht gefunden."""
        # Python-Daten -> JSON-Text -> Bytes (so wird es übers Netz geschickt)
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        # Kopfzeilen: was geschickt wird, nicht zwischenspeichern, wie lang es ist
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        # Den eigentlichen Inhalt abschicken
        self.wfile.write(body)

    def read_json(self):
        """Liest die Daten, die der Browser mitgeschickt hat (z. B. den Namen einer neuen Mission)."""
        # Wie viele Bytes hat der Browser geschickt? Kein Wert -> 0
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}   # nichts geschickt -> leeres Wörterbuch
        # Bytes lesen -> Text -> Python-Daten
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def handle_api(self, method):
        """Verteilt eine Anfrage an die passende Aktion ("Routing").

        Beispiel: Der Browser ruft /api/habits/ab12cd34/done auf.
        Daraus wird die Liste ["api", "habits", "ab12cd34", "done"]
        und wir wissen: Mission ab12cd34 soll abgehakt werden.
        """
        # Adresse in Teile zerlegen (alles nach "?" wird ignoriert)
        parts = self.path.split("?")[0].strip("/").split("/")
        # Der Browser schickt im Demo-Modus die Kopfzeile "X-Demo: 1" mit
        is_demo = self.headers.get("X-Demo") == "1"

        # Kleine Hilfsfunktion, damit wir is_demo nicht überall wiederholen müssen
        def run(action):
            return with_data(action, is_demo)

        # try/except: Falls eine Regel verletzt wird (z. B. leerer Name),
        # wird der Fehler unten abgefangen und als Meldung an den Browser geschickt.
        try:
            # Gesamtzustand abfragen (beim Laden der Seite und regelmäßig)
            if parts == ["api", "state"] and method == "GET":
                # "lambda d: None" ist eine Mini-Funktion, die nichts verändert
                _, st = run(lambda d: None)
                return self.send_json(st)

            # Neue Mission anlegen
            if parts == ["api", "habits"] and method == "POST":
                body = self.read_json()
                habit, st = run(lambda d: logic.add_habit(
                    d, body.get("name"), body.get("goal"), body.get("reminder")))
                return self.send_json({"habit": habit, "state": st})

            # Aktionen auf eine bestimmte Mission: /api/habits/<id>/<aktion>
            if len(parts) == 4 and parts[:2] == ["api", "habits"]:
                hid, action = parts[2], parts[3]   # hid = ID der Mission
                # Mission abhaken
                if action == "done" and method == "POST":
                    res, st = run(lambda d: logic.complete_habit(d, hid))
                    return self.send_json({"result": res, "state": st})
                # Erinnerungszeit setzen oder entfernen
                if action == "reminder" and method == "POST":
                    body = self.read_json()
                    # "or True" sorgt dafür, dass gespeichert wird (Ergebnis ist nicht None)
                    _, st = run(lambda d: logic.set_reminder(
                        d, hid, body.get("reminder")) or True)
                    return self.send_json({"state": st})
                # Mission löschen
                if action == "delete" and method == "POST":
                    _, st = run(lambda d: logic.delete_habit(d, hid) or True)
                    return self.send_json({"state": st})

            # Tutorial abgeschlossen oder übersprungen (FR-33)
            if parts == ["api", "tutorial", "done"] and method == "POST":
                _, st = run(lambda d: logic.finish_tutorial(d))
                return self.send_json({"state": st})

            # Fortschritt zurücksetzen (FR-34).
            # Im Demo-Modus wird nur die Demo neu aufgesetzt, sonst die echten
            # Daten – vorher wird eine Sicherungskopie im Ordner "backups" angelegt.
            if parts == ["api", "reset"] and method == "POST":
                if is_demo:
                    res, st = run(lambda d: demo.load_scenario(d, "start", date.today()))
                else:
                    res, st = run(lambda d: logic.reset_progress(d, DATA_FILE))
                return self.send_json({"result": res, "state": st})

            # ---- Demo-Steuerung (nur mit Demo-Header erlaubt)
            if len(parts) == 3 and parts[:2] == ["api", "demo"] and method == "POST":
                # Schutz: Demo-Befehle dürfen nie die echten Daten treffen
                if not is_demo:
                    return self.send_json({"error": "Nur im Demo-Modus verfügbar."}, 400)
                body = self.read_json()
                action = parts[2]
                if action == "scenario":          # Szenario laden
                    res, st = run(lambda d: demo.load_scenario(d, body.get("name"), date.today()))
                elif action == "next-day":        # einen Tag vorspulen
                    res, st = run(lambda d: demo.next_day(d, body.get("mode", "all")))
                elif action == "end-month":       # bis Monatsende vorspulen
                    res, st = run(lambda d: demo.end_month(d))
                elif action == "rank":            # knapp vor einen Rang setzen
                    res, st = run(lambda d: demo.set_rank(d, int(body.get("rank", 0))))
                else:
                    return self.send_json({"error": "Unbekannte Demo-Aktion."}, 404)
                return self.send_json({"result": res, "state": st})

            # Keine Regel hat gepasst -> "nicht gefunden"
            return self.send_json({"error": "Unbekannte Anfrage."}, 404)
        except logic.ValidationError as e:
            # Regelverletzung: Fehlermeldung (z. B. "Die Mission braucht einen Namen.") zurückschicken
            return self.send_json({"error": str(e)}, 400)

    # ---- HTTP-Methoden ----
    # GET = "gib mir etwas", POST = "hier sind Daten, mach etwas damit"
    def do_GET(self):
        # Adressen mit /api/ sind Befehle an unseren Server ...
        if self.path.startswith("/api/"):
            return self.handle_api("GET")
        # ... alles andere sind Dateien (HTML, CSS, JS) aus dem Ordner "static"
        return super().do_GET()

    def do_POST(self):
        return self.handle_api("POST")


def main():
    """Startet den Server und öffnet den Browser."""
    # Server nur auf dem eigenen Rechner (127.0.0.1) starten, nicht im Netzwerk
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://localhost:{PORT}"   # f"..." setzt Werte in geschweiften Klammern in den Text ein
    print(f"Habit Corps läuft auf {url}  (Beenden mit Strg+C)")
    # Browser nach 0,8 Sekunden öffnen – außer man startet mit --no-browser
    if "--no-browser" not in sys.argv:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        # Läuft endlos und beantwortet Anfragen, bis man Strg+C drückt
        server.serve_forever()
    except KeyboardInterrupt:
        # Strg+C wurde gedrückt -> freundlich verabschieden
        print("\nWeggetreten!")


# Dieser Block läuft nur, wenn man die Datei direkt startet (python3 app.py),
# nicht wenn eine andere Datei sie importiert (z. B. die Tests).
if __name__ == "__main__":
    main()
