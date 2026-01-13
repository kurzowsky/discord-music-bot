import os
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# 🍪 GENERATOR CIASTECZEK
# ==========================================
cookies_content = os.getenv('COOKIES_CONTENT')
if cookies_content:
    print("🍪 Config: Tworzę cookies.txt...")
    try:
        with open('cookies.txt', 'w') as f:
            f.write(cookies_content)
    except Exception as e:
        print(f"❌ Błąd cookies: {e}")

# ==========================================
# 🔐 SEKRETY
# ==========================================
TOKEN = os.getenv('DISCORD_TOKEN')
if not TOKEN:
    raise ValueError("❌ Brak DISCORD_TOKEN!")

# ==========================================
# ⚙️ KONFIGURACJA ID
# ==========================================
WELCOME_CHANNEL_ID = 1244337321608876042
MONITORED_ROLES = {1249508176722661416, 941320096452841572}

# ==========================================
# 🎵 USTAWIENIA AUDIO (TRYB DOWNLOAD)
# ==========================================

# Teraz pobieramy plik, zamiast go streamować.
# To eliminuje błędy 403 Forbidden i zacinanie.
YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'outtmpl': '%(id)s.%(ext)s', # Zapisz plik jako ID.rozszerzenie
    'noplaylist': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'cookiefile': 'cookies.txt',
    'force_ipv4': True,
    # Ważne: user agent
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
}

FFMPEG_OPTIONS = {
    'options': '-vn',
}