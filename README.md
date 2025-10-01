# Carrefour Ingredient Shopper Agent (Lexia)

An AI agent that, given a dish name (e.g., "tortilla de patata"), will:

1. Extract the core ingredients using an LLM
2. Save them to `/tmp/ingredients.txt`
3. Search each ingredient on Carrefour (`site:carrefour.es`) via Serper
4. Stream back one Carrefour link per ingredient

It streams every step (processing, ingredients, file save, searches, links) and replies in the user's language.

## ✨ Features

- **Clean Architecture**: Well-structured, maintainable code with clear separation of concerns
- **Memory Management**: Built-in conversation history and thread management
- **Ingredient Extraction**: Uses OpenAI to extract ingredients for a user-given dish
- **Carrefour Search**: Uses Serper to find Carrefour links for each ingredient (`site:carrefour.es`)
- **Streaming Responses**: Streams progress and results in real time (ingredients, saving, per-ingredient links)
- **Language-Aware**: Detects user language (ES/EN heuristic) and responds accordingly
- **File Output**: Saves ingredients to `/tmp/ingredients.txt`
- **Variables Helper**: Modern Variables class for clean API key and configuration management
- **Error Handling**: Robust error handling and logging throughout
- **Standard Endpoints**: Inherited endpoints from Lexia package for consistency

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- OpenAI API key (`OPENAI_API_KEY`)
- Serper API key (`SERPER_API_KEY`)
- Access to Lexia platform

### Installation

#### Option 1: Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/Xalantico/lexia-starter-kit-python-v1
   cd lexia-starter-kit-python-v1
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the agent**
   ```bash
   python main.py
   ```

#### Option 2: Docker Deployment

1. **Clone the repository**
   ```bash
   git clone https://github.com/Xalantico/lexia-starter-kit-python-v1
   cd lexia-starter-kit-python-v1
   ```

2. **Deploy with Docker**
   ```bash
   # Quick deployment
   ./deploy.sh
   
   # Or manually
   docker-compose up -d
   ```

3. **Check service status**
   ```bash
   docker-compose ps
   docker-compose logs -f
   ```

The server will start on `http://localhost:8002`

## 📚 API & Endpoints

Once running, you can access:

- Health Check: `http://localhost:8002/api/v1/health`
- Chat Endpoint: `http://localhost:8002/api/v1/send_message`
- Docs: `http://localhost:8002/docs`

Request body (example):

```json
{
  "thread_id": "test",
  "message": "I want to make tortilla de patata",
  "model": "gpt-4o-mini"
}
```

## 🏗️ Architecture

### Core Components

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Lexia         │───▶│  Starter Kit     │───▶│   OpenAI        │
│  Platform       │    │                  │    │     API         │
└─────────────────┘    └──────────────────┘    └─────────────────┘
       ▲                        │                        │
       │                        ▼                        │
       │               ┌──────────────────┐               │
       │               │  Memory          │               │
       │               │  Manager        │               │
       │               └──────────────────┘               │
       │                        │                        │
       └────────────────────────┼────────────────────────┘
                                │
                       ┌──────────────────┐
                       │  Response        │
                       │  Handler        │
                       └──────────────────┘
```

### Key Modules

- **`main.py`**: Main application entry point with the ingredient → Carrefour streaming workflow
- **`memory/`**: Conversation history and thread management
- **`agent_utils.py`**: Utility functions for OpenAI integration
- **`search_handler.py`**: Serper utilities (e.g., `serper_first_link`) and optional Google search helpers

## 🍳 How It Works

1. User sends a dish name (e.g., "tortilla de patata").
2. The agent asks OpenAI for a JSON array of core ingredients (in the user's language).
3. The agent streams the detected ingredients and saves them to `/tmp/ingredients.txt`.
4. For each ingredient, the agent streams a Carrefour search line and the first result link from Serper (or "Not found").
5. A final completion message is sent when done.

Notes:
- Language is auto-detected with a small heuristic; messages are localized to ES/EN.
- Make sure `OPENAI_API_KEY` and `SERPER_API_KEY` are configured in the agent variables.

## 🔧 Customization

### Modify AI Behavior

Edit the `process_message()` function in `main.py` to customize:

- System prompts and context
- Model parameters (temperature, max_tokens, etc.)
- Response processing logic
- Error handling strategies

### Add New Capabilities

Extend `process_message()` to add behaviors, or expand `search_handler.py` with more search helpers (e.g., different retailers, price filters).

### Memory Management

Customize conversation storage in the `memory/` module:

- Adjust `max_history` for conversation length
- Implement persistent storage (database, files)
- Add conversation analytics and insights

## 📁 Files Produced

- `/tmp/ingredients.txt`: One ingredient per line (overwritten each run)

## 🔑 Configuration

### Variables Helper Class

The starter kit uses the modern Variables helper class from the Lexia package for clean configuration management:

```python
from lexia import Variables

# Initialize variables helper
vars = Variables(data.variables)

# Get API keys and configuration
openai_key = vars.get("OPENAI_API_KEY")
custom_config = vars.get("CUSTOM_CONFIG")
database_url = vars.get("DATABASE_URL")

# Convenience methods
openai_key = vars.get_openai_key()
anthropic_key = vars.get_anthropic_key()
groq_key = vars.get_groq_key()
```

### Required Variables

- `OPENAI_API_KEY`: OpenAI API key
- `SERPER_API_KEY`: Serper.dev API key

### Benefits of Variables Helper

- **Clean API**: Object-oriented approach instead of utility functions
- **Better Performance**: Built-in caching for faster lookups
- **Flexible**: Easy to change variable names without code changes
- **Consistent**: Same pattern across all Lexia integrations

## 🔍 Serper Carrefour Search

We use Serper's web search to fetch Carrefour results with `site:carrefour.es`.

Setup:
- Get an API key from `https://serper.dev`
- Set `SERPER_API_KEY` in agent variables

The helper `serper_first_link(query, variables)` returns the first organic result link.

## 🧪 Testing

### 1. Setup ngrok for External Access

To test your agent from the Lexia platform, you'll need to expose your local server to the internet using ngrok:

1. **Install ngrok**
   ```bash
   # On macOS with Homebrew
   brew install ngrok
   
   # Or download from https://ngrok.com/download
   ```

2. **Start your local server**
   ```bash
   python main.py
   ```

3. **Expose your server with ngrok**
   ```bash
   ngrok http 8002
   ```

4. **Copy the ngrok URL**
   ngrok will display a URL like: `https://abc123.ngrok-free.app`

### 2. Configure Agent in Lexia Platform

1. Go to the [Lexia Platform](https://app.lexiaplatform.com)
2. Navigate to **Agents** → **Create New Agent**
3. In the **Agent Configuration** section:
   - Set **Agent Type** to "Custom Agent"
   - Set **Message Endpoint** to `https://abc123.ngrok-free.app/api/v1/send_message`
4. Save your agent configuration

### 3. Test Your Agent

Once configured, test your setup by sending a message through the Lexia platform or directly via curl:

```bash
curl -X POST "https://your-ngrok-url.ngrok-free.app/api/v1/send_message" \
     -H "Content-Type: application/json" \
     -d '{
       "thread_id": "test_thread",
       "message": "I want to make tortilla de patata",
       "model": "gpt-4o-mini"
     }'
```

**Note**: Replace `your-ngrok-url` with your actual ngrok URL. The ngrok URL will change each time you restart ngrok unless you have a paid account.

## 🐛 Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed correctly
2. **API Key Issues**: The starter kit now provides helpful error messages when the OpenAI API key is missing:
   - "Sorry, the OpenAI API key is missing or empty. From menu right go to admin mode, then agents and edit the agent in last section you can set the openai key."
   - This guides users to the correct location in the Lexia platform to configure their API key
3. **Port Conflicts**: Change the port in `main.py` if 8002 is already in use
4. **No Links Found**: Ensure `SERPER_API_KEY` is set and the query includes `site:carrefour.es`
4. **Variables Not Found**: Use the Variables helper class to access configuration values from Lexia requests

### Debug Mode

Enable detailed logging by modifying the log level in `main.py`:

```python
logging.basicConfig(level=logging.DEBUG)
```

## 📖 Code Structure

```
project/
├── main.py                 # Main application entry point
├── requirements.txt        # Python dependencies
├── README.md              # This file
├── .gitignore             # Git ignore patterns
├── Dockerfile             # Docker configuration
├── docker-compose.yml     # Docker Compose configuration
├── .dockerignore          # Docker ignore patterns
├── deploy.sh              # Deployment script
├── memory/                # Memory management module
│   ├── __init__.py
│   └── conversation_manager.py
├── agent_utils.py         # AI agent utilities
└── search_handler.py      # Serper helpers (e.g., first link on Carrefour)
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This starter kit is provided as-is for development and educational purposes.

## 🆘 Support

For issues and questions:

1. Check the logs for detailed error messages
2. Review the Lexia platform documentation
3. Open an issue in this repository

---

**Happy coding! 🚀**
