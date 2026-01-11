# 🤖 Discord Multi-Bot (Music & CS2)

Wielofunkcyjny bot na Discorda napisany w Pythonie, stworzony z myślą o prywatnych serwerach dla graczy. Łączy w sobie odtwarzacz muzyki, statystyki Faceit (CS2), narzędzia do zarządzania drużynami oraz funkcje administracyjne.

Projekt jest zoptymalizowany pod wdrożenie na **Railway** (wykorzystuje Docker do obsługi FFmpeg) i posiada system oszczędzania zasobów (auto-disconnect po 15 min).

## ✨ Główne Funkcje

### 🎵 Muzyka (YouTube)
* **Odtwarzanie:** Obsługa linków oraz wyszukiwania po tytule (`!play`).
* **Kolejkowanie:** System kolejki utworów (max 5).
* **Kontrola:** Pauzowanie, wznawianie, pomijanie i zatrzymywanie.
* **Auto-Disconnect:** Bot automatycznie opuszcza kanał głosowy po **15 minutach** bezczynności.

### 🎮 CS2 & Faceit
* **Statystyki:** Sprawdzanie poziomu, ELO, K/D, Winrate i historii ostatnich 10 meczów (`!faceit`).
* **Team Randomizer:** Losowanie dwóch drużyn z osób obecnych na kanale głosowym (`!teams`).
* **Auto-Move:** Inteligentne przenoszenie wylosowanej drużyny na inny, wolny kanał głosowy (`!mv`).

### 🛠️ Narzędzia i 4Fun
* **Snipe:** Odzyskiwanie ostatnio usuniętej wiadomości (obsługuje tekst i zdjęcia).
* **Troll-Ping:** Zabawne przerzucanie użytkownika między kanałami (`!ping`).
* **Decyzje:** Rzut wirtualną monetą i kostką.
* **Moderacja:** Czyszczenie czatu (`!usun`), blokowanie zmiany nicku, zmiana nicku.
* **Powitania:** Wykrywanie statusu Online znajomych (konfigurowalne role).

## 🚀 Instalacja i Uruchomienie (Lokalnie)

### Wymagania
* Python 3.10+
* FFmpeg (dodany do zmiennych środowiskowych systemu)

### 1. Klonowanie repozytorium
```bash
git clone https://github.com/kurzowsky/discord-music-bot
cd NAZWA_REPOZYTORIUM 
```

### 2. Instalacja zależności
```bash
pip install -r requirements.txt
```

### 3. Konfiguracja
Utwórz plik `.env` w głównym folderze projektu i dodaj swój token:
```env
DISCORD_TOKEN=twoj_tajny_token_bota
```


### 4. Uruchomienie
```bash
python main.py
```

## ☁️ Wdrożenie na Railway

Ten projekt zawiera plik `Dockerfile`, który automatycznie instaluje `Python`, `FFmpeg` oraz `libopus`, naprawiając typowe problemy z odtwarzaniem dźwięku na platformach chmurowych.

1. Wrzuć kod na swoje repozytorium GitHub.
2. Zaloguj się na [Railway.app](https://railway.app/).
3. Stwórz nowy projekt -> **Deploy from GitHub repo**.
4. W ustawieniach projektu (Variables) dodaj zmienną:
   * `DISCORD_TOKEN` = Twój token.
5. Bot zbuduje się i uruchomi automatycznie.

> **Wskazówka:** Aby nie przekroczyć darmowego limitu Railway, w ustawieniach *Service -> Resources* ustaw limit RAM na **512 MB**.

```markdown
## 📝 Lista Komend

| Kategoria | Komenda | Opis |
| :--- | :--- | :--- |
| **Muzyka** | `!play <tytuł/link>` | Włącza muzykę lub dodaje do kolejki |
| | `!skip` | Pomija obecny utwór |
| | `!pause` / `!resume` | Pauzuje lub wznawia odtwarzanie |
| | `!stop` | Zatrzymuje muzykę i wyrzuca bota |
| **CS2** | `!faceit <nick/link>` | Pokazuje statystyki gracza |
| | `!teams` | Losuje składy (Team A i Team B) |
| | `!mv <A/B>` | Przenosi Team A lub B na wolny kanał |
| **Admin** | `!usun <ilość>` | Usuwa X ostatnich wiadomości |
| | `!snipe` | Pokazuje ostatnio usuniętą wiadomość |
| | `!zmien_nick` | Zmienia nick użytkownika |
| | `!block_nickname` | Blokuje możliwość zmiany nicku |
| **Inne** | `!moneta` | Rzut monetą (Orzeł/Reszka) |
| | `!kostka` | Rzut kostką (1-6) |
| | `!ping <osoba>` | Trolluje użytkownika (wymaga roli `ping`) |
| | `!pomoc` | Wyświetla listę komend w Discordzie |
| | `!regulamin` | Wyświetla zasady serwera |
```
## 🤝 Autor
Projekt stworzony przez **Kurzowsky**.