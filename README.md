# Whisper Telegram Bot

The bot transcribes Telegram audio messages, voice messages, and forwarded audio
documents with OpenAI Whisper, then replies with the recognized text.

## Setup

1. Create a bot with Telegram's [@BotFather](https://t.me/BotFather) and copy its
   token.
2. Install the dependencies in a Python virtual environment:

   ```bash
   python -m pip install -r requirements.txt
   ```

3. Put the token in a `.env` file in the project directory:

   ```bash
   TELEGRAM_BOT_TOKEN=your-bot-token
   ```

4. Start the bot:

   ```bash
   python main.py
   ```

The bot loads `.env` from the project directory. Existing shell environment
variables take precedence over values in `.env`. The default Whisper model is
`turbo`; set `WHISPER_MODEL` in `.env` or the environment to use another model.
Whisper downloads the model the first time it runs.

The host must have `ffmpeg` installed so Whisper can decode Telegram audio
formats.
