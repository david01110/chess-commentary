# Schach Kommentator

Eine Webanwendung zum Importieren und Kommentieren von Lichess-Schachpartien.

## Features

- Import von Lichess-Partien über die Spiel-ID
- Interaktives Schachbrett mit Navigationsmöglichkeiten
- Kommentare und Stellungsbewertungen für jeden Zug
- Zugliste mit Klick-Navigation
- Responsive Design

## Installation

1. Klonen Sie das Repository
2. Installieren Sie die Abhängigkeiten:
```bash
pip install -r requirements.txt
```

## Verwendung

1. Starten Sie den Server:
```bash
python app.py
```

2. Öffnen Sie einen Webbrowser und navigieren Sie zu `http://localhost:5000`

3. Geben Sie eine Lichess-Spiel-ID ein (z.B. "Rf7GBwac")

4. Navigieren Sie durch die Züge und fügen Sie Kommentare hinzu

## Technische Details

- Backend: Flask (Python)
- Frontend: HTML, JavaScript, Bootstrap
- Schachlogik: chess.js
- Schachbrett: chessboard.js
- API: Lichess API für Spielimport
