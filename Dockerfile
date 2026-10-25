FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    XDG_CACHE_HOME=/home/bot/.cache

RUN apt-get update \
    && apt-get install --no-install-recommends -y ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system bot \
    && useradd --system --gid bot --create-home bot \
    && mkdir -p /home/bot/.cache/whisper \
    && chown -R bot:bot /home/bot/.cache

WORKDIR /app

COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY main.py .

USER bot

CMD ["python", "main.py"]
