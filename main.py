# Import monkey patch first
import monkey

import sys
from orchestrator import Orchestrator
from io_handler import TerminalIO
from web_app import app, socketio

def main():
    # Check if running in web mode
    if len(sys.argv) > 1 and sys.argv[1] == '--web':
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 5000
        print(f"Starting web server on port {port}")
        socketio.run(app, port=port, debug=True)
    else:
        io_handler = TerminalIO()
        orchestrator = Orchestrator(io_handler)
        orchestrator.run()

if __name__ == "__main__":
    main() 