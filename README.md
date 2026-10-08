# Habit Corps

Habit-Tracker im Duolingo-Stil mit Rängen der US Army.
Gruppenprojekt Einführung in Software Engineering – Musa und Patrick.

## Starten

```
python3 app.py
```

Der Browser öffnet sich automatisch unter http://localhost:5050.
Beenden mit Strg+C im Terminal. Es muss nichts installiert werden (nur Python 3.9+).

## Dateien

| Datei | Inhalt |
|---|---|
| `app.py` | lokaler Webserver und API |
| `logic.py` | Spielregeln: Streak, Multiplikator, XP, Ränge, Orden, Speichern |
| `data.json` | alle Daten (wird automatisch befüllt) |
| `static/` | Oberfläche: HTML, CSS, JavaScript, Grafiken |
| `test_logic.py` | automatische Tests: `python3 test_logic.py` |

## Datum simulieren (für Tests und Präsentation)

```
HABIT_TODAY=2026-11-01 python3 app.py
```

Damit lassen sich Tageswechsel, Streak-Reset und Monats-Orden vorführen.
Am besten vorher eine Kopie von `data.json` anlegen.
