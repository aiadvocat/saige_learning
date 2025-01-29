# AI Security Challenge

An interactive educational tool for learning about AI security through hands-on challenges. Users interact with an AI Professor while being guided by Saige, an AI security mentor.

![Saige Web Interface](saige.gif)

## Features

- Interactive chat-based learning environment
- Modern web interface with terminal emulation
- Progressive security challenges
- Real-time security analysis with Straiker SDK
- Progress tracking and persistence
- Streaming AI responses
- Colorized output
- Save and resume functionality

## Prerequisites

- Python 3.8+
- [Ollama](https://ollama.ai/) installed and running locally
- Straiker SDK API key

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/ai-security-challenge.git
   cd ai-security-challenge
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Set up environment variables:
   ```bash
   # On Unix/macOS:
   export STRAIKER_API_KEY='your-api-key-here'
   
   # On Windows:
   set STRAIKER_API_KEY=your-api-key-here
   ```

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Start Ollama and pull required models:
   ```bash
   ollama pull llama3
   ollama pull mistral
   ```

## Usage

Start the application:
```bash
python main.py  # For terminal interface
```

Or start the web interface with an optional port (default is 5000):
```bash
python main.py --web  # Uses default port 5000
python main.py --web 8080  # Uses port 8080
```

Then open your browser to the appropriate URL (e.g., `http://localhost:5000` or `http://localhost:8080`) to access the web interface.

Follow the prompts to:
1. Enter your name and email
2. Complete security challenges
3. Learn about AI security concepts

Use these commands while running:
- Type 'hint' for help with current challenge
- Type 'exit' to quit and save progress

Your progress is automatically saved and can be resumed by using the same email address when you return.

## Project Structure

- `web_app.py`: Flask web application that serves the web interface
- `templates/`: HTML templates for the web interface
- `static/`: Static assets including CSS and JavaScript
- `orchestrator.py`: Main application controller that manages user interaction
- `chat_bot.py`: AI Professor implementation with streaming responses
- `saige.py`: Security mentor implementation that guides users
- `guide.json`: Challenge configuration including prompts and success criteria
- `progress/`: Directory containing saved user progress

## Technical Details

- Flask web application with WebSocket support for real-time communication
- Terminal emulation using Xterm.js for authentic terminal experience
- Uses Langchain for LLM interactions
- Implements streaming responses for natural conversation flow
- Integrates with Straiker SDK for security analysis
- Maintains conversation history for context
- Supports ANSI color formatting for both web and terminal output
- Implements save/load functionality for progress persistence

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes:

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Ollama team for providing local LLM capabilities
- Straiker SDK for security analysis features
- Langchain for LLM interaction framework

## Environment Variables

The application requires the following environment variables to be set:

| Variable | Description |
|----------|-------------|
| STRAIKER_API_KEY | API key for Straiker SDK security analysis |

You can set these permanently in your shell profile or use a `.env` file:

```bash
# .env file example
STRAIKER_API_KEY=your-api-key-here
```

Note: Never commit your `.env` file or actual API keys to version control.
