# Import monkey patch first
import monkey

from flask import Flask, render_template, request, jsonify, send_from_directory, session
from flask_socketio import SocketIO, emit, join_room
import secrets
from io_handler import WebIO
from orchestrator import Orchestrator
from saige import Saige
from chat_bot import ChatBot
import gevent
import json
from pathlib import Path

app = Flask(__name__, static_url_path='/static')
app.secret_key = secrets.token_hex(16)
socketio = SocketIO(app, async_mode='gevent', manage_session=False, cors_allowed_origins="*")

# Store active games and their IO handlers
active_games = {}

# Store command line arguments
start_chapter = 0
start_challenge = 0

def init_app(chapter: int = 0, challenge: int = 0):
    """Initialize the app with starting chapter and challenge"""
    global start_chapter, start_challenge
    start_chapter = chapter
    start_challenge = challenge

# Load guide data once at startup
with open('guide.json', 'r') as f:
    GUIDE_DATA = json.load(f)

@app.route('/')
def index():
    game_id = session.get('game_id')
    if not game_id:
        game_id = secrets.token_hex(8)
        session['game_id'] = game_id
    
    # Get current progress from active game if it exists
    current_chapter = 0
    current_challenge = 0
    if game_id in active_games:
        orchestrator = active_games[game_id]['orchestrator']
        saige = orchestrator.saige
        current_chapter = saige.current_chapter
        current_challenge = saige.current_challenge
    
    return render_template('terminal.html', 
                         game_id=game_id, 
                         title='AI Security Challenge',
                         guide=GUIDE_DATA,
                         current_chapter=current_chapter,
                         current_challenge=current_challenge)

def update_title(game_id: str, title: str):
    """Update the title for a specific game session"""
    if game_id in active_games:
        socketio.emit('update_title', {'title': title}, room=game_id, namespace='/terminal')

def update_progress(game_id: str, chapter: int, challenge: int):
    """Update the progress indicators for a specific game session"""
    if game_id in active_games:
        socketio.emit('update_progress', {
            'current_chapter': chapter,
            'current_challenge': challenge
        }, room=game_id, namespace='/terminal')

@socketio.on('connect', namespace='/terminal')
def handle_connect():
    game_id = session.get('game_id')
    if not game_id:
        game_id = request.args.get('session')
        if game_id:
            session['game_id'] = game_id
        else:
            return False  # Reject connection if no game_id
    
    join_room(game_id)
    
    if game_id not in active_games:
        try:
            web_io = WebIO(socketio)
            web_io.set_session(game_id)
            
            # Use the global start_chapter and start_challenge values
            orchestrator = Orchestrator(web_io, start_chapter=start_chapter, start_challenge=start_challenge)
            
            def run_game():
                try:
                    print(f"Starting game for session {game_id}")
                    orchestrator.run()
                except Exception as e:
                    print(f"Game error in session {game_id}: {e}")
                    raise  # Re-raise to see the full error
                finally:
                    socketio.emit('game_ended', room=game_id)
                    if game_id in active_games:
                        print(f"Cleaning up session {game_id}")
                        del active_games[game_id]
            
            active_games[game_id] = {
                'orchestrator': orchestrator,
                'io': web_io
            }
            
            # Use gevent for the game thread
            gevent.spawn(run_game)
            
            return True  # Connection accepted
        except Exception as e:
            print(f"Error initializing game: {e}")
            return False  # Reject connection if initialization fails
    
    return True  # Connection accepted for existing game

@socketio.on('input', namespace='/terminal')
def handle_input(data):
    game_id = session.get('game_id')
    if not game_id:
        return
        
    if game_id in active_games:
        try:
            web_io = active_games[game_id]['io']
            current_session = web_io.current_session
            web_io.input_queue.put(data['text'])
        except Exception as e:
            print(f"DEBUG Socket: Error processing input: {e}")
            raise
    else:
        socketio.emit('game_ended')

@socketio.on('disconnect')
def handle_disconnect():
    game_id = session.get('game_id')
    if game_id in active_games:
        del active_games[game_id]

@socketio.on('register', namespace='/terminal')
def handle_register(data):
    session_id = data.get('session')
    if session_id:
        join_room(session_id)  # Join the room with session ID

@socketio.on('heartbeat_response')
def handle_heartbeat_response(data):
    session_id = data.get('session')

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path) 