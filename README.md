# Telegram Task Management Bot

This is a Telegram bot designed to help users manage their tasks through natural language interaction. It integrates with a NestJS backend for task storage and uses the Gemini API for natural language understanding and speech-to-text capabilities.

## Features

-   **User Authentication:** Secure login/logout with email and password.
-   **Task Creation:** Create new tasks by simply telling the bot what you need to do.
-   **Task Management:** Mark tasks as completed or in progress.
-   **Task Listing:** View your active tasks (pending or in progress).
-   **Task Deletion:** Delete tasks you no longer need.
-   **Voice Input:** Interact with the bot using voice messages, which are transcribed and processed.
-   **Secure Input:** Email and password messages are automatically deleted from the chat for privacy.
-   **Natural Language Understanding:** Powered by Google's Gemini API to understand your task-related commands.

## Setup

To get this bot up and running, follow these steps:

### 1. Prerequisites

-   Python 3.9+
-   `pip` (Python package installer)
-   A Telegram Bot Token (from BotFather)
-   A Google Gemini API Key
-   A running NestJS backend for task management (configured at `http://localhost:3000/api` by default).

### 2. Clone the Repository

```bash
git clone <your-repository-url>
cd bot_python
```

### 3. Create a Virtual Environment (Recommended)

```bash
python -m venv venv
.env/Scripts/activate  # On Windows
source venv/bin/activate  # On macOS/Linux
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

If `requirements.txt` is not present, you will need to install the following libraries:

```bash
pip install python-telegram-bot python-dotenv google-generativeai requests pydub SpeechRecognition fuzzywuzzy
```

### 5. Environment Variables

Create a `.env` file in the root directory of the project and add the following:

```
BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"
GEMINI_API_KEY="YOUR_GOOGLE_GEMINI_API_KEY"
# NESTJS_API_BASE_URL is set to http://localhost:3000/api by default in config.py
# If your backend is elsewhere, you might need to adjust config.py directly.
```

Replace `YOUR_TELEGRAM_BOT_TOKEN` and `YOUR_GOOGLE_GEMINI_API_KEY` with your actual tokens/keys.

### 6. Run the Bot

```bash
python run.py
```

The bot should now be running and listening for messages in Telegram.

## Usage

-   **Start the bot:** Send `/start` to your bot in Telegram.
-   **Login:** If not authenticated, the bot will prompt you for your email and password.
-   **Logout:** Send `/logout` to log out from the bot.
-   **Create a task:** "Create a task to buy groceries"
-   **Complete a task:** "Complete the task to call mom"
-   **Mark task in progress:** "Mark the task to wash the car as in progress"
-   **List tasks:** "What are my tasks?" or "List my tasks"
-   **Delete a task:** "Delete the task to clean the room"
-   **Voice commands:** Send a voice message with your command.

## Project Structure

```
.env
config.py
main.py
run.py
__pycache__/
modules/
    __init__.py
    auth.py
    gemini.py
    speech.py
    state.py
    tasks.py
    __pycache__/
```

## Contributing

Feel free to fork the repository and contribute. Pull requests are welcome!
