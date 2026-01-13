# Używamy lekkiej wersji Pythona na Linuxie
FROM python:3.11-slim

# --- CACHE BUSTER ---
# Zmiana tej daty wymusi na Railway ponowną instalację pakietów
ENV REFRESH_DATE=2026-01-13_v2

# Aktualizujemy system i instalujemy FFmpeg, Opus ORAZ Node.js
# Node.js jest wymagany do działania yt-dlp (Signature solving)
RUN apt-get update && \
    apt-get install -y ffmpeg libopus0 nodejs && \
    rm -rf /var/lib/apt/lists/*

# Ustawiamy folder roboczy
WORKDIR /app

# Kopiujemy plik z bibliotekami i instalujemy je
COPY requirements.txt .
# Dodajemy --upgrade, żeby upewnić się, że yt-dlp jest najnowszy
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Kopiujemy resztę plików bota
COPY . .

# Komenda startowa
CMD ["python", "main.py"]