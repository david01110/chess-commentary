import os
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import requests
import chess
import chess.pgn
import io
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Lade Umgebungsvariablen
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'default-secret-key')

# Datenbank-Konfiguration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///commentary.db')
if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Datenbankmodelle
class Game(db.Model):
    id = db.Column(db.String(100), primary_key=True)
    broadcast_id = db.Column(db.String(100))
    white = db.Column(db.String(100))
    black = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.String(100), db.ForeignKey('game.id'))
    move_number = db.Column(db.Integer)
    comment_text = db.Column(db.Text)
    evaluation = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

# Host-Authentifizierung
HOST_PASSWORD = os.getenv('HOST_PASSWORD', 'your-password-here')  # Ändern Sie dies in ein sicheres Passwort

def is_host():
    return session.get('is_host', False)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('password') == HOST_PASSWORD:
            session['is_host'] = True
            return redirect(url_for('index'))
        return 'Falsches Passwort', 401
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('is_host', None)
    return redirect(url_for('index'))

@app.route('/')
def index():
    return render_template('index.html', is_host=is_host())

@app.route('/host')
def host():
    if not is_host():
        return redirect(url_for('login'))
    return render_template('host.html')

# Globale Variable für den aktuellen Broadcast
current_broadcast = None

@app.route('/import-broadcast', methods=['POST'])
def import_broadcast():
    data = request.get_json()
    url = data.get('broadcast_round_id', '')
    
    # Nur Host darf neue Broadcasts importieren
    if not session.get('is_host', False) and not current_broadcast:
        return jsonify({'error': 'Nicht autorisiert'}), 403

    # Wenn kein Host, nur den aktuellen Broadcast laden
    if not session.get('is_host', False):
        url = current_broadcast
    
    # Extrahiere die Broadcast-IDs aus der URL
    selected_game_id = None
    if 'lichess.org/broadcast' in url:
        parts = url.split('/')
        tour_id = None
        round_id = None
        for i in range(len(parts)-1):
            if parts[i] == 'broadcast':
                for j in range(i+1, len(parts)):
                    if len(parts[j]) >= 8 and parts[j].isalnum():
                        if not tour_id:
                            tour_id = parts[j]
                        elif not round_id:
                            round_id = parts[j]
                        else:
                            selected_game_id = parts[j]
                            break
        if tour_id:
            broadcast_id = tour_id
            if round_id:
                broadcast_id = f"{tour_id}/{round_id}"
    else:
        broadcast_id = url
    
    if not broadcast_id:
        return jsonify({'error': 'Keine gültige Broadcast-URL oder ID'})
    
    try:
        # Versuche zuerst, die Runden-PGN zu laden
        response = requests.get(f'https://lichess.org/broadcast/-/-/{broadcast_id}.pgn')
        if response.status_code != 200:
            # Wenn das nicht funktioniert, versuche die Tour-PGN
            tour_id = broadcast_id.split('/')[0]
            response = requests.get(f'https://lichess.org/broadcast/-/-/{tour_id}.pgn')
            if response.status_code != 200:
                return jsonify({'error': f'Broadcast nicht gefunden (Status: {response.status_code})'})
        
        # Wenn Host, setze den aktuellen Broadcast
        if session.get('is_host', False):
            global current_broadcast
            current_broadcast = broadcast_id
        
        pgn_content = response.text
        print(f"Received PGN content: {pgn_content[:200]}...")
        games = []
        
        # Verarbeite jede Partie im PGN
        while pgn_content.strip():
            game_io = io.StringIO(pgn_content)
            game = chess.pgn.read_game(game_io)
            if game is None:
                break
                
            # Extrahiere Spielinformationen
            white = game.headers.get('White', 'Unknown')
            black = game.headers.get('Black', 'Unknown')
            result = game.headers.get('Result', '*')
            game_url = game.headers.get('Site', '')
            
            # Extrahiere Game-ID aus der URL
            game_id = game_url.split('/')[-1] if game_url else f"{broadcast_id}_{len(games)}"
            
            # Extrahiere Züge und Zeiten
            moves = []
            times = []
            board = game.board()
            for node in game.mainline():
                san = node.san()
                moves.append(san)
                # Extrahiere Zeit aus Kommentar wenn vorhanden
                comment = node.comment
                if '[%clk' in comment:
                    time = comment.split('[%clk ')[1].split(']')[0]
                    times.append(time)
                else:
                    times.append(None)
            
            # Speichere Partie in der Datenbank
            db_game = Game.query.get(game_id)
            if not db_game:
                db_game = Game(
                    id=game_id,
                    broadcast_id=broadcast_id,
                    white=white,
                    black=black
                )
                db.session.add(db_game)
            
            game_data = {
                'id': game_id,
                'white': white,
                'black': black,
                'result': result,
                'moves': moves,
                'times': times
            }
            games.append(game_data)
            
            # Wenn dies die gesuchte Partie ist, setze sie an den Anfang
            if selected_game_id and game_id == selected_game_id:
                games.insert(0, games.pop())
            
            # Aktualisiere PGN-Content für nächste Partie
            current_pos = game_io.tell()
            pgn_content = pgn_content[current_pos:].strip()
        
        if not games:
            return jsonify({'error': 'Keine Partien im Broadcast gefunden'})
        
        # Wenn eine spezifische Partie gesucht wurde aber nicht gefunden wurde
        if selected_game_id and games[0]['id'] != selected_game_id:
            return jsonify({'error': f'Partie {selected_game_id} nicht gefunden'})
            
        db.session.commit()
        return jsonify({
            'broadcast': {
                'games': games,
                'selectedGameId': selected_game_id
            }
        })
        
    except Exception as e:
        print(f"Error importing broadcast: {str(e)}")
        return jsonify({'error': str(e)})

@app.route('/get-current-broadcast')
def get_current_broadcast():
    return jsonify({'broadcast_id': current_broadcast})

@app.route('/check-host')
def check_host():
    return jsonify({'is_host': session.get('is_host', False)})

@app.route('/save-comment', methods=['POST'])
def save_comment():
    if not session.get('is_host', False):
        return jsonify({'error': 'Nur Hosts können Kommentare speichern'}), 403
        
    data = request.get_json()
    game_id = data.get('game_id')
    move_number = data.get('move_number')
    evaluation = data.get('evaluation')
    comment_text = data.get('comment')
    
    if not all([game_id, isinstance(move_number, int), move_number >= 0]):
        return jsonify({'error': 'Ungültige Eingabedaten'}), 400
        
    # Finde oder erstelle Kommentar
    comment = Comment.query.filter_by(
        game_id=game_id,
        move_number=move_number
    ).first()
    
    if comment:
        comment.evaluation = evaluation
        comment.comment_text = comment_text
    else:
        comment = Comment(
            game_id=game_id,
            move_number=move_number,
            evaluation=evaluation,
            comment_text=comment_text
        )
        db.session.add(comment)
    
    try:
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/get-comment')
def get_comment():
    game_id = request.args.get('game_id')
    move_number = request.args.get('move_number')
    
    if not game_id or not move_number:
        return jsonify({'error': 'Fehlende Parameter'}), 400
        
    try:
        move_number = int(move_number)
    except ValueError:
        return jsonify({'error': 'Ungültige Zugnummer'}), 400
        
    comment = Comment.query.filter_by(
        game_id=game_id,
        move_number=move_number
    ).first()
    
    if comment:
        return jsonify({
            'comment': {
                'evaluation': comment.evaluation,
                'text': comment.comment_text
            }
        })
    else:
        return jsonify({'comment': None})

@app.route('/get-comments/<game_id>')
def get_comments(game_id):
    comments = Comment.query.filter_by(game_id=game_id).all()
    return jsonify({
        comment.move_number: {
            'comment': comment.comment_text,
            'evaluation': comment.evaluation
        }
        for comment in comments
    })

if __name__ == '__main__':
    app.run(debug=False)
