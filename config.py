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

# config.py - podmień dolną część pliku

# ==========================================
# 🎵 USTAWIENIA AUDIO (STREAMING MODE 2.0)
# ==========================================

YDL_OPTIONS = {
    # Wymuszamy format m4a/opus przez HTTP. Unikamy 'm3u8' (HLS), które powodują błędy 403.
    'format': 'bestaudio[protocol^=http]', 
    'noplaylist': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'cookiefile': 'cookies.txt', # Ciasteczka są kluczowe
    'force_ipv4': True,          # Wymuszamy IPv4 (stabilniejsze na Railway)
    'quiet': True,
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
}

FFMPEG_OPTIONS = {
    # reconnect: wznawia połączenie w razie zerwania (ważne przy streamowaniu)
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    # cookies: przekazujemy ciasteczka również do odtwarzacza!
    'options': '-vn -cookies "cookies.txt" -user_agent "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"',
}