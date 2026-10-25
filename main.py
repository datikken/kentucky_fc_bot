import asyncio
import logging
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
import whisper
from telegram import Message, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BotConfig:
    token: str
    whisper_model: str = "turbo"

    @classmethod
    def from_environment(cls) -> "BotConfig":
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            raise RuntimeError("Set the TELEGRAM_BOT_TOKEN environment variable.")
        return cls(
            token=token,
            whisper_model=os.getenv("WHISPER_MODEL", "turbo"),
        )


class WhisperTranscriber:
    def __init__(self, model_name: str) -> None:
        self._model = whisper.load_model(model_name)

    def transcribe(self, audio_path: Path) -> str:
        result = self._model.transcribe(str(audio_path))
        return result["text"].strip()


class TelegramWhisperBot:
    _AUDIO_EXTENSIONS = {
        ".aac",
        ".flac",
        ".m4a",
        ".mp4",
        ".mp3",
        ".ogg",
        ".oga",
        ".opus",
        ".wav",
        ".webm",
        ".wma",
    }
    _TELEGRAM_MESSAGE_LIMIT = 4096

    def __init__(self, config: BotConfig) -> None:
        self._transcriber = WhisperTranscriber(config.whisper_model)
        self._application = Application.builder().token(config.token).build()
        self._application.add_handler(CommandHandler("start", self.start))
        self._application.add_handler(
            MessageHandler(
                filters.AUDIO | filters.VOICE | filters.Document.ALL,
                self.handle_audio,
            )
        )

    async def start(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        del context
        message = update.effective_message
        if message is not None:
            await message.reply_text(
                "Forward or send me an audio message and I will transcribe it."
            )

    async def handle_audio(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        message = update.effective_message
        if message is None:
            return

        attachment = self._get_audio_attachment(message)
        if attachment is None:
            await message.reply_text("Please send an audio file or voice message.")
            return

        file_id, file_name = attachment
        try:
            telegram_file = await context.bot.get_file(file_id)
            suffix = Path(file_name or telegram_file.file_path or "").suffix
            with tempfile.TemporaryDirectory(prefix="whisper-bot-") as directory:
                audio_path = Path(directory) / f"audio{suffix}"
                await telegram_file.download_to_drive(custom_path=audio_path)
                transcript = await asyncio.to_thread(
                    self._transcriber.transcribe, audio_path
                )
        except Exception:
            logger.exception("Failed to transcribe an audio message")
            await message.reply_text(
                "Sorry, I couldn't transcribe that audio. Please try again."
            )
            return

        if not transcript:
            await message.reply_text("I couldn't detect any speech in that audio.")
            return

        for chunk in self._split_message(transcript):
            await message.reply_text(chunk)

    @classmethod
    def _get_audio_attachment(cls, message: Message) -> tuple[str, str | None] | None:
        if message.audio is not None:
            return message.audio.file_id, message.audio.file_name
        if message.voice is not None:
            return message.voice.file_id, None
        if message.document is not None:
            document = message.document
            file_name = document.file_name
            is_audio = (
                (document.mime_type is not None and document.mime_type.startswith("audio/"))
                or (
                    file_name is not None
                    and Path(file_name).suffix.lower() in cls._AUDIO_EXTENSIONS
                )
            )
            if is_audio:
                return document.file_id, file_name
        return None

    @classmethod
    def _split_message(cls, text: str) -> list[str]:
        chunks: list[str] = []
        while len(text) > cls._TELEGRAM_MESSAGE_LIMIT:
            split_at = text.rfind(" ", 0, cls._TELEGRAM_MESSAGE_LIMIT + 1)
            if split_at <= 0:
                split_at = cls._TELEGRAM_MESSAGE_LIMIT
                chunks.append(text[:split_at])
                text = text[split_at:]
            else:
                chunks.append(text[: split_at + 1])
                text = text[split_at + 1 :]
        if text:
            chunks.append(text)
        return chunks

    def run(self) -> None:
        self._application.run_polling()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    load_dotenv(Path(__file__).resolve().with_name(".env"))
    config = BotConfig.from_environment()
    TelegramWhisperBot(config).run()


if __name__ == "__main__":
    main()
