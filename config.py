import os
from dotenv import load_dotenv

# Ładujemy zmienne z pliku .env (tylko lokalnie, na Railway są wstrzyknięte automatycznie)
load_dotenv()

# ==========================================
# 🔐 SEKRETY (Zmienne środowiskowe)
# ==========================================

# Token pobieramy z systemu (bezpieczeństwo)
TOKEN = os.getenv('DISCORD_TOKEN')

if not TOKEN:
    # To rzuci błąd w konsoli, jeśli zapomnisz dodać tokena
    raise ValueError("❌ Błąd: Brak DISCORD_TOKEN! Dodaj go w .env lub Variables na Railway.")

# ==========================================
# 🍪 MAGICZNY KOD DO CIASTECZEK
# ==========================================
# Sprawdzamy, czy w zmiennych na Railway jest treść ciasteczek
cookies_env = os.getenv('COOKIES_CONTENT')

if cookies_env:
    # Jeśli jest, to tworzymy plik cookies.txt na serwerze
    print("🍪 Znaleziono ciasteczka w zmiennych! Tworzę plik cookies.txt...")
    with open('cookies.txt', 'w') as f:
        f.write(cookies_env)
else:
    print("⚠️ Ostrzeżenie: Nie znaleziono zmiennej COOKIES_CONTENT.")

# ==========================================
# ⚙️ KONFIGURACJA ID (Edytuj tutaj)
# ==========================================

# ID kanału powitań (Gdzie bot pisze "X jest online")
# Wpisz 0 lub None, jeśli chcesz wyłączyć tę funkcję
WELCOME_CHANNEL_ID = 1244337321608876042

# Lista ID ról, które bot ma śledzić
# Możesz tu łatwo dodawać nowe role po przecinku
MONITORED_ROLES = {
    1249508176722661416,
    941320096452841572
}


# ==========================================
# 🎵 USTAWIENIA AUDIO (Zaawansowane)
# ==========================================

# Opcje pobierania z YouTube
YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'cookiefile': 'cookies.txt',
    'force_ipv4': True,
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
}

# Opcje przetwarzania dźwięku (FFmpeg)
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}