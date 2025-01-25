# AI Security Challenge

An interactive educational tool for learning about AI security through hands-on challenges. Users interact with an AI Professor while being guided by Saige, an AI security mentor.

## Features

- Interactive chat-based learning environment
- Progressive security challenges
- Real-time security analysis with Straiker SDK
- Progress tracking and persistence
- Streaming AI responses
- Colorized terminal output
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

Run the application:
```bash
python orchestrator.py
```

Follow the prompts to:
1. Enter your name and email
2. Complete security challenges
3. Learn about AI security concepts

Use these commands while running:
- Type 'hint' for help with current challenge
- Type 'exit' to quit and save progress

Your progress is automatically saved and can be resumed by using the same email address when you return.

## Project Structure

- `orchestrator.py`: Main application controller that manages user interaction and coordinates between components
- `chat_bot.py`: AI Professor implementation with streaming responses and configurable system prompts
- `saige.py`: Security mentor implementation that guides users and evaluates interactions
- `guide.json`: Challenge configuration including prompts, success criteria, and rewards
- `progress/`: Directory containing saved user progress (automatically created)

## Technical Details

- Uses Langchain for LLM interactions
- Implements streaming responses for natural conversation flow
- Integrates with Straiker SDK for security analysis
- Maintains conversation history for context
- Supports ANSI color formatting for terminal output
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
