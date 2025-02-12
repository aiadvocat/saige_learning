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
from queue import Empty

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
    
    # Get current progress
    current_chapter = 0
    current_challenge = 0
    
    # If we have user info in session, load their progress
    user_name = session.get('user_name')
    user_email = session.get('user_email')
    if user_name and user_email:
        # Create temporary Saige instance to load progress
        temp_saige = Saige(None, None)
        temp_saige.set_user_info(user_name, user_email)
        if temp_saige.load_progress():
            current_chapter = temp_saige.current_chapter
            current_challenge = temp_saige.current_challenge
    
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
    
    try:
        # If we have an existing game instance, just update its socket connection
        if game_id in active_games:
            print(f"Reusing existing game for session {game_id} (browser refresh)")
            existing_game = active_games[game_id]
            existing_game['io'].socketio = socketio
            existing_game['io'].set_session(game_id)
            existing_game['ready'] = False  # Reset ready flag for new thread
            
            def resume_game():
                try:
                    # Wait for ready flag
                    while game_id in active_games and not active_games[game_id]['ready']:
                        gevent.sleep(0.1)
                    
                    if game_id not in active_games:
                        return
                        
                    orchestrator = existing_game['orchestrator']
                    # Update progress indicators
                    update_progress(game_id, orchestrator.saige.current_chapter, orchestrator.saige.current_challenge)
                    # Give socket time to establish
                    gevent.sleep(0.5)
                    # Clear screen and show welcome back
                    orchestrator.io.clear()
                    # Send messages with small delays to ensure order
                    orchestrator.io.output("\nWelcome back to the AI Security Challenge!")
                    gevent.sleep(0.1)
                    orchestrator.io.output("\nType 'exit' to quit, 'hint' for help, 'learn' to report incorrect evaluation.\n")
                    gevent.sleep(0.1)
                    # Introduce current challenge
                    intro = orchestrator.saige.introduce_current_state()
                    orchestrator.saige.display_message(intro)
                    # Start the main game loop
                    orchestrator._run_game_loop()
                except Exception as e:
                    print(f"Game error in session {game_id}: {e}")
                    raise
                finally:
                    if game_id in active_games:
                        print(f"Cleaning up session {game_id}")
                        del active_games[game_id]
                    socketio.emit('game_ended', room=game_id)
            
            # Spawn new thread for resumed game
            game_thread = gevent.spawn(resume_game)
            existing_game['ready'] = True
            return True

        # Only create new game instance if one doesn't exist
        web_io = WebIO(socketio)
        web_io.set_session(game_id)
        
        # Get user info from session
        user_name = session.get('user_name')
        user_email = session.get('user_email')
        
        # Use the global start_chapter and start_challenge values
        orchestrator = Orchestrator(web_io, start_chapter=start_chapter, start_challenge=start_challenge)
        
        # Store game instance first
        active_games[game_id] = {
            'orchestrator': orchestrator,
            'io': web_io,
            'ready': False,  # Add ready flag
            'session_data': {  # Store session data
                'user_name': user_name,
                'user_email': user_email
            }
        }
        
        def run_game():
            try:
                print(f"Starting game for session {game_id}")
                # Wait for ready flag
                while game_id in active_games and not active_games[game_id]['ready']:
                    gevent.sleep(0.1)
                
                if game_id not in active_games:
                    return
                    
                # Get session data
                session_data = active_games[game_id]['session_data']
                user_name = session_data.get('user_name')
                user_email = session_data.get('user_email')
                
                if user_name and user_email:
                    # Set user info in orchestrator
                    orchestrator.set_user_info(user_name, user_email)
                    # Store in Flask session after successful set
                    name, email = orchestrator.get_user_info()
                    session['user_name'] = name
                    session['user_email'] = email
                    # Update progress indicators after loading state
                    update_progress(game_id, orchestrator.saige.current_chapter, orchestrator.saige.current_challenge)
                    # Give socket time to establish
                    gevent.sleep(0.5)
                    # Clear screen and show welcome back
                    orchestrator.io.clear()
                    # Send messages with small delays to ensure order
                    orchestrator.io.output("\nWelcome back to the AI Security Challenge!")
                    gevent.sleep(0.1)
                    orchestrator.io.output(f"Glad to see you again, {user_name}!")
                    gevent.sleep(0.1)
                    orchestrator.io.output("\nType 'exit' to quit, 'hint' for help, 'learn' to report incorrect evaluation.\n")
                    gevent.sleep(0.1)
                    # Introduce current challenge
                    intro = orchestrator.saige.introduce_current_state()
                    orchestrator.saige.display_message(intro)
                    # Start the main game loop
                    orchestrator._run_game_loop()
                else:
                    # Run normal flow with user info collection
                    orchestrator.run()
            except Exception as e:
                print(f"Game error in session {game_id}: {e}")
                raise  # Re-raise to see the full error
            finally:
                if game_id in active_games:
                    print(f"Cleaning up session {game_id}")
                    del active_games[game_id]
                socketio.emit('game_ended', room=game_id)
        
        # Use gevent for the game thread
        game_thread = gevent.spawn(run_game)
        
        # Set ready flag after spawning thread
        active_games[game_id]['ready'] = True
        
        return True  # Connection accepted
    except Exception as e:
        print(f"Error initializing game: {e}")
        if game_id in active_games:
            del active_games[game_id]
        return False  # Reject connection if initialization fails

@socketio.on('input', namespace='/terminal')
def handle_input(data):
    game_id = session.get('game_id')
    print(f"DEBUG: Received input for game {game_id}: {data['text']}")
    if not game_id:
        print("DEBUG: No game_id found in session")
        return
        
    if game_id in active_games:
        try:
            web_io = active_games[game_id]['io']
            print(f"DEBUG: Found web_io for game {game_id}")
            # Clear any old items in the queue
            items_cleared = 0
            while not web_io.input_queue.empty():
                try:
                    old_item = web_io.input_queue.get_nowait()
                    items_cleared += 1
                    print(f"DEBUG: Cleared old item from queue: {old_item}")
                except Empty:
                    break
            if items_cleared > 0:
                print(f"DEBUG: Cleared {items_cleared} old items from queue")
            # Put the new input
            web_io.input_queue.put(data['text'])
            print(f"DEBUG: Put new input in queue: {data['text']}")
        except Exception as e:
            print(f"DEBUG Socket: Error processing input: {e}")
            raise
    else:
        print(f"DEBUG: Game {game_id} not found in active_games")
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