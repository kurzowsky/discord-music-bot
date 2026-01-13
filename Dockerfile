# Używamy specjalnego obrazu, który ma już zainstalowanego Pythona ORAZ Node.js
# To gwarantuje, że yt-dlp będzie miał środowisko do działania
FROM nikolaik/python-nodejs:python3.11-nodejs20

# Instalujemy tylko FFmpeg i Opus (Node.js już jest!)
RUN apt-get update && \
    apt-get install -y ffmpeg libopus0 && \
    rm -rf /var/lib/apt/lists/*

# Ustawiamy folder roboczy
WORKDIR /app

# Kopiujemy i instalujemy biblioteki Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Kopiujemy resztę plików
COPY . .

# Startujemy
CMD ["python", "main.py"]