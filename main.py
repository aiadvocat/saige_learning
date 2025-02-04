#!/usr/bin/env python3
import monkey
import sys
import argparse
from orchestrator import Orchestrator
from io_handler import TerminalIO
from web_app import app, socketio, init_app

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Start Saige AI Security Learning System')
    parser.add_argument('--web', type=int, default=5000, help='Run in web mode with specific port (5000 default)')
    parser.add_argument('--chapter', type=int, default=0, help='Starting chapter number')
    parser.add_argument('--challenge', type=int, default=0, help='Starting challenge number')
    args = parser.parse_args()

    # Check if running in web mode
    if args.web:
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 5000
        print(f"Starting web server on port {port}")
        # Initialize web app with chapter and challenge
        init_app(chapter=args.chapter-1, challenge=args.challenge-1)
        socketio.run(app, port=port, debug=True)
    else:
        io_handler = TerminalIO()
        orchestrator = Orchestrator(io_handler, start_chapter=args.chapter-1, start_challenge=args.challenge-1)
        orchestrator.run()

if __name__ == "__main__":
    main() 