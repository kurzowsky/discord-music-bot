from dotenv import load_dotenv
load_dotenv()
import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any


#stats overal
def get_faceit_stats(player_name: str) -> Optional[Dict[str, Any]]:
    try:
        url = f"https://faceittracker.net/players/{player_name}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)


        if response.status_code == 404:
            print(f"Player {player_name} not found!")
            return None
        elif response.status_code != 200:
            print(f"HTTP error: {response.status_code}")
            return None
        

        soup = BeautifulSoup(response.text, 'html.parser')

        def get_stat_value(stat_title: str) -> str:
            title_tag = soup.find('div', class_='stats-card-title', string=stat_title)
            if title_tag:
                value_tag = title_tag.find_next('div', class_='stats-card-rate')
                return value_tag.text.strip() if value_tag else "N/A"
            return "N/A"

        # Pobieranie stats
        kd_ratio = get_stat_value("K/D Ratio")
        winrate = get_stat_value("Winrate")
        matches = get_stat_value("Matches")
        headshots = get_stat_value("Headshots")
        elo = get_stat_value("Elo")

        #LVL
        level_tag = soup.find('h2', {'class': 'faceit-lvl'})
        level_string = level_tag.text.strip() if level_tag else "N/A"
        #print(level_string)
        if level_string[-2] == " ":
            level = level_string[-1:]
        else:
            level = level_string[-2:]

        
        match_cards = soup.find_all('div', class_='r-macthes-card')
        wins, losses, total_kills, total_deaths = 0, 0, 0, 0
        results_last_10_matches = ""

        for i, match in enumerate(match_cards[:10]):  # Przetwarzamy ostatnie 10 meczów
            try:
                result = match.find('div', class_='result').text.strip()
                if result == 'Win':
                    wins += 1
                    results_last_10_matches += "W"
                elif result == 'Loss':
                    losses += 1
                    results_last_10_matches += "L"
                else:
                    print(f"Nieoczekiwany wynik meczu w meczu {i}: {result}")

                kad_section = match.find_all('div', class_='r-macthes-info')[2]
                if kad_section:
                    kad_text = kad_section.find('span').text.strip()
                    kills, assists, deaths = map(int, kad_text.split(' - '))
                    total_kills += kills
                    total_deaths += deaths
                else:
                    print(f"Nie znaleziono sekcji K-A-D w meczu {i}")
            except Exception as e:
                print(f"Błąd przetwarzania meczu {i}: {e}")

        # Obliczanie K/D ratio
        overall_kd_ratio = round(total_kills / total_deaths, 2) if total_deaths > 0 else total_kills
        
        # wyniki w formie słownika
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
            "last_10_results": results_last_10_matches[:18]
        }

    except Exception as e:
        print(f"Unexpected error: {e}")
        return None