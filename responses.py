from dotenv import load_dotenv
load_dotenv()
import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any

# Stats overall
def get_faceit_stats(player_name: str) -> Optional[Dict[str, Any]]:
    try:
        url = f"https://faceittracker.net/players/{player_name}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'} # Pełniejszy User-Agent
        response = requests.get(url, headers=headers)

        if response.status_code == 404:
            print(f"Player {player_name} not found!")
            return None
        elif response.status_code != 200:
            print(f"HTTP error: {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')

        # --- POPRAWIONA FUNKCJA WYCIĄGANIA DANYCH ---
        def get_stat_value(stat_title: str) -> str:
            # Szukamy nagłówka (np. "Winrate")
            # Używamy lambda, żeby ignorować ewentualne spacje w kodzie HTML
            title_tag = soup.find('div', class_='stats-card-title', string=lambda t: t and stat_title.strip() in t.strip())
            
            if title_tag:
                value_tag = title_tag.find_next('div', class_='stats-card-rate')
                if value_tag:
                    full_text = value_tag.text.strip()
                    # TU JEST NAPRAWA: Bierzemy tylko pierwszy element (np. "51%")
                    # Rozdzielamy tekst po spacjach i bierzemy element [0]
                    # To odcina śmieci typu "18% All-Time Matches"
                    if full_text:
                        return full_text.split()[0]
            return "N/A"

        # Pobieranie stats (Usunąłem zbędne spacje w kluczach)
        kd_ratio = get_stat_value("K/D Ratio")
        winrate = get_stat_value("Winrate")
        matches = get_stat_value("Matches") 
        headshots = get_stat_value("Headshots")
        elo = get_stat_value("Elo")

        # --- POPRAWIONE POBIERANIE POZIOMU ---
        # Stara metoda [-2] była ryzykowna. Ta jest pewniejsza.
        level = "N/A"
        level_tag = soup.find('h2', {'class': 'faceit-lvl'})
        if level_tag:
            level_text = level_tag.text.strip()
            # Jeśli tekst to "Level 10", split() da ["Level", "10"], bierzemy ostatni element
            parts = level_text.split()
            if parts:
                level = parts[-1]

        # Pobieranie ostatnich meczów
        match_cards = soup.find_all('div', class_='r-macthes-card')
        wins, losses, total_kills, total_deaths = 0, 0, 0, 0
        results_last_10_matches = ""

        # Zabezpieczenie, jeśli meczów jest mniej niż 10
        matches_to_check = match_cards[:10] if match_cards else []

        for i, match in enumerate(matches_to_check): 
            try:
                result_div = match.find('div', class_='result')
                if result_div:
                    result = result_div.text.strip()
                    if result == 'Win':
                        wins += 1
                        results_last_10_matches += "W"
                    elif result == 'Loss':
                        losses += 1
                        results_last_10_matches += "L"
                
                # Pobieranie K-A-D
                infos = match.find_all('div', class_='r-macthes-info')
                # Szukamy sekcji, która wygląda jak K - A - D (zazwyczaj trzecia, index 2)
                if len(infos) > 2:
                    kad_text = infos[2].find('span').text.strip()
                    # Zabezpieczenie przed błędami parsowania
                    try:
                        kills, assists, deaths = map(int, kad_text.split(' - '))
                        total_kills += kills
                        total_deaths += deaths
                    except ValueError:
                        pass # Ignorujemy, jeśli format jest inny
            except Exception as e:
                print(f"Błąd przetwarzania meczu {i}: {e}")

        # Obliczanie K/D ratio dla ostatnich 10 meczów
        overall_kd_ratio = round(total_kills / total_deaths, 2) if total_deaths > 0 else total_kills
        
        return {
            "kd_ratio": kd_ratio,
            "winrate": winrate,
            "matches": matches,
            "headshots": headshots,
            "elo": elo,
            "level": level,
            "k/d_ratio_last_10": overall_kd_ratio,
            "wins": wins,
            "losses": losses,
            "last_10_results": results_last_10_matches
        }

    except Exception as e:
        print(f"Unexpected error: {e}")
        return None
