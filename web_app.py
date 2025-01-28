# Import monkey patch first
import monkey

from flask import Flask, render_template, request, jsonify, send_from_directory, session
from flask_socketio import SocketIO, emit, join_room
import secrets
from io_handler import WebIO
from orchestrator import Orchestrator
import gevent

app = Flask(__name__, static_url_path='/static')
app.secret_key = secrets.token_hex(16)
socketio = SocketIO(app, async_mode='gevent', manage_session=False, cors_allowed_origins="*")

# Store active games and their IO handlers
active_games = {}

@app.route('/')
def index():
    game_id = session.get('game_id')
    if not game_id:
        game_id = secrets.token_hex(8)
        session['game_id'] = game_id
    return render_template('terminal.html', game_id=game_id, title='AI Security Challenge')

def update_title(game_id: str, title: str):
    """Update the title for a specific game session"""
    if game_id in active_games:
        socketio.emit('update_title', {'title': title}, room=game_id, namespace='/terminal')

@socketio.on('connect', namespace='/terminal')
def handle_connect():
    game_id = session.get('game_id')
    if not game_id:
        print("DEBUG Socket: No session ID in Flask session")
        game_id = request.args.get('session')
        if game_id:
            session['game_id'] = game_id
            print(f"DEBUG Socket: Retrieved game_id from socket query: {game_id}")
        else:
            print("DEBUG Socket: No session ID found in socket query")
            return
    
    print(f"DEBUG Socket: New connection for session {game_id}")
    join_room(game_id)
    
    if game_id not in active_games:
        web_io = WebIO(socketio)
        web_io.set_session(game_id)
        print(f"DEBUG Socket: Created WebIO for session {game_id}")
        
        orchestrator = Orchestrator(web_io)
        
        def run_game():
            try:
                print(f"Starting game for session {game_id}")
                orchestrator.run()
            except Exception as e:
                print(f"Game error in session {game_id}: {e}")
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

@socketio.on('input', namespace='/terminal')
def handle_input(data):
    game_id = session.get('game_id')
    if not game_id:
        print("DEBUG Socket: No session ID found for input")
        return
        
    print(f"DEBUG Socket: Processing input for game {game_id}")
    if game_id in active_games:
        try:
            web_io = active_games[game_id]['io']
            current_session = web_io.current_session
            print(f"DEBUG Socket: Input received for session {game_id} (WebIO: {current_session})")
            web_io.input_queue.put(data['text'])
            print(f"DEBUG Socket: Input queued for session {game_id}")
        except Exception as e:
            print(f"DEBUG Socket: Error processing input: {e}")
            raise
    else:
        print(f"DEBUG Socket: Input received for inactive session {game_id}")
        socketio.emit('game_ended')

@socketio.on('disconnect')
def handle_disconnect():
    game_id = session.get('game_id')
    print(f"DEBUG Socket: Client disconnected, session {game_id}")
    if game_id in active_games:
        print(f"DEBUG Socket: Cleaning up session {game_id}")
        del active_games[game_id]

@socketio.on('register', namespace='/terminal')
def handle_register(data):
    session_id = data.get('session')
    if session_id:
        print(f"DEBUG Socket: Client registered for session {session_id}")
        join_room(session_id)  # Join the room with session ID

@socketio.on('heartbeat_response')
def handle_heartbeat_response(data):
    session_id = data.get('session')
    print(f"DEBUG Socket: Heartbeat response from session {session_id}")

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path) 