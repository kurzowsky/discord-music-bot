FROM python:3.11-slim

# Zmienna wymuszająca przebudowę (zmień datę/godzinę jak znowu się zatnie)
ENV REFRESH_BUILD=2026-01-13_HOUR_16_20

# Instalujemy git (potrzebny do pobrania yt-dlp ze źródła), ffmpeg i nodejs
RUN apt-get update && \
    apt-get install -y git ffmpeg libopus0 nodejs && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
# --force-reinstall wymusza ponowne pobranie bibliotek
RUN pip install --no-cache-dir --force-reinstall -r requirements.txt

COPY . .

CMD ["python", "main.py"]