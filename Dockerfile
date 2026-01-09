# Używamy lekkiej wersji Pythona na Linuxie
FROM python:3.11-slim

# Aktualizujemy system i instalujemy FFmpeg oraz Opus "na sztywno"
RUN apt-get update && \
    apt-get install -y ffmpeg libopus0 && \
    rm -rf /var/lib/apt/lists/*

# Ustawiamy folder roboczy
WORKDIR /app

# Kopiujemy plik z bibliotekami i instalujemy je
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopiujemy resztę plików bota
COPY . .

# Komenda startowa
CMD ["python", "main.py"]