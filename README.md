# Habit Corps

Habit-Tracker im Duolingo-Stil mit Rängen der US Army.
Gruppenprojekt Einführung in Software Engineering – Musa und Patrick.

## Starten

```
python3 app.py
```

Der Browser öffnet sich automatisch unter http://localhost:5050.
Beenden mit Strg+C im Terminal. Es muss nichts installiert werden (nur Python 3.9+).

## Tutorial und Neustart

- Beim **ersten Öffnen** führt Kuno in 12 Schritten durch alle Funktionen und gibt am Ende
  einen Einsatzplan, wie man den Tracker am besten nutzt. Überspringen ist jederzeit möglich.
  Erneut ansehen: **❔ Hilfe** oben rechts oder „Tutorial mit Kuno ansehen“ in der Karte *Kommando*.
- **Fortschritt zurücksetzen** (Karte *Kommando*) löscht nach einer Sicherheitsabfrage alle
  Missionen, XP und Orden. Vorher wird der alte Stand als Kopie in `backups/` gespeichert.
  Rückgängig machen: App beenden, die gewünschte Datei aus `backups/` nach `data.json` kopieren.
  Im Demo-Modus setzt der Knopf nur die Demo zurück.

## Demo-Modus: alles ausprobieren

Oben rechts auf **🧪 Demo** klicken. Die App arbeitet dann mit einer eigenen Datei
`demo_data.json` und einem simulierten Datum, eure echte `data.json` wird nicht angefasst.
Ein gelb-schwarzes Band zeigt, dass der Demo-Modus aktiv ist.

| Steuerung | Was passiert |
|---|---|
| Szenario laden | *Alle Multiplikatoren*, *Frischer Start* oder *Weg zum General* |
| +1 Tag · alles erledigt / eine verpasst / nichts | Tageswechsel, Streak-Reset, trauriger Kuno |
| Monat abschließen | spult bis Monatsende vor und verleiht den Orden |
| Knapp davor setzen | XP 5 unter dem gewählten Rang, nächste Mission befördert |
| Erinnerung testen | löst sofort eine Erinnerung aus |
| Alle Kunos ansehen | alle 14 Ränge, normal / salutierend / traurig |

Zurück zu den echten Daten mit **Demo beenden**.

## Dateien

| Datei | Inhalt |
|---|---|
| `app.py` | lokaler Webserver und API |
| `logic.py` | Spielregeln: Streak, Multiplikator, XP, Ränge, Orden, Speichern |
| `data.json` | alle Daten (wird automatisch befüllt) |
| `static/` | Oberfläche: HTML, CSS, JavaScript, Grafiken |
| `demo.py` | Demo-Modus: Szenarien, Zeit vorspulen, Rang setzen |
| `demo_data.json` | Daten des Demo-Modus (entsteht automatisch) |
| `backups/` | Sicherungskopien vor jedem Neustart (entsteht automatisch) |
| `test_logic.py` | automatische Tests: `python3 test_logic.py` |

## Datum simulieren (für Tests und Präsentation)

```
HABIT_TODAY=2026-11-01 python3 app.py
```

Damit lassen sich Tageswechsel, Streak-Reset und Monats-Orden vorführen.
Am besten vorher eine Kopie von `data.json` anlegen.

## Algorithmus: Rang-Prognose (Markov-Kette + dynamische Programmierung)

Die Karte „Prognose zum Monatsende“ berechnet für jeden Rang die Wahrscheinlichkeit,
ihn am Monatsende zu halten.

1. **Verhalten schätzen:** Aus den letzten 60 Tagen zählt `estimate_behaviour()`, an wie vielen
   Tagen *alle* Missionen erledigt wurden. Mit einer Startannahme (Beta-Prior 2:1) ergibt das
   die Tageswahrscheinlichkeit **p**. Zusätzlich wird geschätzt, welcher Anteil **q** an
   Fehltagen trotzdem erledigt wird.
2. **Markov-Kette:** Jeder restliche Tag ist ein Zufallsschritt. Mit Wahrscheinlichkeit p steigen
   alle Streaks um 1 (volle XP), mit 1 − p gibt es nur q der XP und alle Streaks fallen auf 0.
   Der Zustand ist (Streak-Zustand, bisherige XP).
3. **Dynamische Programmierung:** `forecast()` rechnet die exakte Wahrscheinlichkeitsverteilung
   Tag für Tag weiter, statt zufällig zu simulieren. XP werden in 5er-Einheiten als ganze Zahlen
   geführt.
4. **Ränge:** Jede Endverteilung wird mit den Rangschwellen und der Vormonatsbedingung
   ausgewertet. Der erste General verlangt, dass jeder Tag mit mindestens 5 Missionen ×3,0 gelingt;
   danach zählt General wie ein normaler Rang ab 100 % von M – auch mitten im Monat.

Prüfung in `test_logic.py`: Die exakte Rechnung stimmt mit 20.000 zufällig simulierten Monaten
(Monte-Carlo) auf ±1,5 Prozentpunkte überein. Laufzeit bei 12 Missionen: rund 20 ms.
