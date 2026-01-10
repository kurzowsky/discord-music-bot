from typing import Final
from dotenv import load_dotenv
import os
import discord
from discord import Intents, Member
from discord.ext import commands
from responses import get_faceit_stats
import asyncio
import random
import yt_dlp


# Zastosowanie poprawki dla kompatybilności asyncio w środowiskach takich jak Jupyter


# Załadowanie zmiennych środowiskowych z pliku .env
load_dotenv()

TOKEN: Final[str] = os.getenv('DISCORD_TOKEN')

# Definicja intentów dla bota
intents: Intents = Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

# Inicjalizacja bota z intentami i prefiksem komendy
bot = commands.Bot(command_prefix='!', intents=intents)

# --- KONFIGURACJA YOUTUBE I FFMPEG ---
YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    # 'quiet': True, # Możesz zakomentować na chwilę, żeby widzieć więcej logów w razie błędów
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    # Usunęliśmy sekcję 'extractor_args' z wymuszaniem iOS/Android, 
    # bo to ona powoduje błędy o "PO Token" na serwerach.
    # Pozwalamy yt-dlp samemu wybrać najlepszego klienta (zazwyczaj web/android-creator).
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

# --- POPRAWIONA FUNKCJA PLAY ---

@bot.command()
async def play(ctx, *, query):
    """Odtwarza muzykę z YouTube (obsługuje linki i tytuły)."""
    
    if not ctx.author.voice:
        await ctx.send("❌ Musisz być na kanale głosowym!")
        return

    voice_channel = ctx.author.voice.channel
    if ctx.voice_client is None:
        await voice_channel.connect()
    elif ctx.voice_client.channel != voice_channel:
        await ctx.voice_client.move_to(voice_channel)

    voice_client = ctx.voice_client
    if voice_client.is_playing():
        voice_client.stop()

    await ctx.send(f"🔎 Przetwarzam: **{query}**...")

    try:
        loop = asyncio.get_event_loop()
        
        # Sprytne rozpoznawanie: czy to link (http) czy tytuł?
        if query.startswith("http"):
            # Jeśli link -> pobierz bezpośrednio
            search_query = query
            noplaylist = True
        else:
            # Jeśli tytuł -> wyszukaj
            search_query = f"ytsearch:{query}"
            noplaylist = True

        # Pobieranie danych (w tle, żeby nie zacinać bota)
        # Zaktualizowana lambda z obsługą błędów extract_info
        data = await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(YDL_OPTIONS).extract_info(search_query, download=False))

        info = None
        
        # Logika wyciągania poprawnego wpisu
        if 'entries' in data:
            # To jest wynik wyszukiwania lub playlista
            if len(data['entries']) > 0:
                info = data['entries'][0]
            else:
                await ctx.send("❌ Nie znaleziono wyników.")
                return
        else:
            # To jest bezpośredni link do wideo
            info = data

        if not info:
             await ctx.send("❌ Błąd: Nie udało się pobrać informacji o wideo.")
             return

        url = info['url']
        title = info.get('title', 'Nieznany utwór')
        
        # Uruchomienie odtwarzania
        source = discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS)
        voice_client.play(source, after=lambda e: print(f'Koniec: {e}') if e else None)
        
        await ctx.send(f"🎵 Gram: **{title}**")
            
    except Exception as e:
        # Ignoruj błędy związane z zamykaniem procesu ffmpeg
        print(f"Szczegóły błędu: {e}")
        await ctx.send("❌ Wystąpił błąd przy próbie odtworzenia. Sprawdź konsolę.")

@bot.command()
async def stop(ctx):
    """Zatrzymuje muzykę i wyrzuca bota z kanału."""
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("🛑 Zatrzymano muzykę i rozłączono.")
    else:
        await ctx.send("Nie jestem połączony z żadnym kanałem.")

@bot.command()
async def pause(ctx):
    """Pauzuje muzykę."""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("⏸️ Muzyka zapauzowana.")

@bot.command()
async def resume(ctx):
    """Wznawia muzykę."""
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("▶️ Muzyka wznowiona.")


@bot.command()
@commands.cooldown(rate=1, per=60, type=commands.BucketType.user)
@commands.has_role("ping")
async def ping(ctx, member: discord.Member):
    guild = ctx.guild

    if not member.voice or not member.voice.channel:
        await ctx.send(f"{member.display_name} nie jest aktualnie na kanale głosowym.")
        return

    original_channel = member.voice.channel

    voice_channels = [c for c in guild.voice_channels if c != original_channel]

    if len(voice_channels) < 2:
        await ctx.send("Potrzebne są przynajmniej 3 kanały głosowe, żeby to działało.")
        return

    channels = random.sample(voice_channels, 2)

    await ctx.send(f"Przerzucanie {member.mention}...")

    try:
        for i in range(5):
            await member.move_to(channels[i % 2])
            await asyncio.sleep(1)

        await member.move_to(original_channel)
        await ctx.send(f"{member.display_name} wrócił(a) na swój kanał.")
    except discord.Forbidden:
        await ctx.send("Nie mam uprawnień do przenoszenia tego użytkownika.")
    except Exception as e:
        await ctx.send(f"Wystąpił błąd: {e}")

@ping.error
async def ping_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"Poczekaj {int(error.retry_after)} sekundy przed ponownym użyciem tej komendy.")
    elif isinstance(error, commands.MissingRole):
        await ctx.send("Brak uprawnień. Potrzebujesz roli `ping`, aby użyć tej komendy.")


# Komenda: Wyświetlenie regulaminu
@bot.command()
async def regulamin(ctx):
    embed = discord.Embed(
        title="📜 Regulamin Serwera Discord",
        description="Poniżej znajdziesz zasady, które obowiązują na naszym serwerze. Prosimy o ich przestrzeganie dla zachowania przyjaznej atmosfery.",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="1️⃣ Postanowienia Ogólne",
        value=(
            "1. Korzystanie z serwera oznacza akceptację niniejszego regulaminu.\n"
            "2. Administracja zastrzega sobie prawo do modyfikacji regulaminu.\n"
            "3. Nieznajomość regulaminu nie zwalnia użytkownika z jego przestrzegania."
        ),
        inline=False
    )
    
    embed.add_field(
        name="2️⃣ Zasady Ogólne",
        value=(
            "1. Szanuj innych użytkowników – zakaz obrażania, grożenia oraz dyskryminacji.\n"
            "2. Zabrania się spamu, floodingu i wysyłania niechcianych linków.\n"
            "3. Publikowanie nieodpowiednich treści (np. mowy nienawiści, brutalnych obrazów) jest zabronione."
        ),
        inline=False
    )
    
    embed.add_field(
        name="3️⃣ Zasady Dotyczące Nicków i Avatarów",
        value=(
            "1. Nicki i awatary nie mogą zawierać treści obraźliwych ani wulgarnych.\n"
            "2. Administracja może wymagać zmiany nicku lub awatara, jeśli są one nieodpowiednie."
        ),
        inline=False
    )
    
    embed.add_field(
        name="4️⃣ Zasady Reklamy",
        value=(
            "1. Reklamowanie serwerów, produktów lub usług jest dozwolone tylko za zgodą administracji.\n"
            "2. Zakaz wysyłania reklam w prywatnych wiadomościach do innych użytkowników."
        ),
        inline=False
    )
    
    embed.add_field(
        name="5️⃣ Administracja i Moderacja",
        value=(
            "1. Decyzje administracji są ostateczne.\n"
            "2. W razie problemów kontaktuj się z administracją przez kanał 'Pomoc' lub prywatną wiadomość.\n"
            "3. Nadużywanie funkcji „pingowania” administracji jest zabronione."
        ),
        inline=False
    )
    
    embed.add_field(
        name="6️⃣ Sankcje",
        value=(
            "1. Łamanie regulaminu może skutkować ostrzeżeniem, wyciszeniem, wyrzuceniem lub banem.\n"
            "2. Administracja ma prawo indywidualnie rozpatrywać każdy przypadek naruszenia zasad."
        ),
        inline=False
    )
    
    embed.add_field(
        name="7️⃣ Prywatność",
        value=(
            "1. Zabrania się udostępniania prywatnych informacji innych użytkowników bez ich zgody.\n"
            "2. Serwer nie gromadzi danych osobowych poza tymi wymaganymi przez Discord."
        ),
        inline=False
    )
    
    embed.set_footer(text="Dziękujemy za przestrzeganie zasad i życzymy miłego pobytu na serwerze! 😊")

    await ctx.send(embed=embed)



# Komenda: Sprawdzenia statystyk Faceit
@bot.command()
async def faceit(ctx, *, profile_url: str):
    """Wpisz !faceit <link do profilu FACEIT>, aby sprawdzić statystyki."""
    try:
        if "faceit.com" in profile_url or "faceittracker.net" in profile_url:
            player_name = profile_url.split("/")[-1]
        else:
            player_name = str(profile_url)

        stats = get_faceit_stats(player_name)
        if not stats:
            await ctx.send("Nie udało się pobrać statystyki dla tego gracza. Sprawdź, czy nick jest poprawny.")
            return

        embed = discord.Embed(title=f"**Statystyki FACEIT dla {player_name}**", color=0x00ff00)
        embed.add_field(name="Poziom", value=stats["level"], inline=True)
        embed.add_field(name="ELO", value=stats["elo"], inline=True)
        embed.add_field(name="Rozegrane mecze", value=stats["matches"], inline=True)
        embed.add_field(name="Win Rate", value=f"{stats['winrate']}", inline=True)
        embed.add_field(name="Headshot Rate", value=f"{stats['headshots']}", inline=True)
        embed.add_field(name="K/D Ratio", value=f"{stats['kd_ratio']}", inline=True)
        embed.add_field(name="**LAST 10 MATCHES**", value="", inline=False)
        embed.add_field(name="K/D Ratio", value=f"{stats['k/d_ratio_last_10']}", inline=True)
        embed.add_field(name="Wins", value=f"{stats['wins']}", inline=True)
        embed.add_field(name="Losses", value=f"{stats['losses']}", inline=True)
        embed.add_field(name="Results", value=f"{stats['last_10_results']}", inline=True)

        embed.set_footer(text="Statystyki dostarczone przez FaceitTracker.net")
        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send("Wystąpił błąd podczas przetwarzania żądania.")
        print(e)

# Wydarzenie, które jest wywoływane, gdy bot jest gotowy
@bot.event
async def on_ready() -> None:
    print(f'{bot.user} jest online')
    activity = discord.CustomActivity(name='Owner: kurzowskyy')
    await bot.change_presence(activity=activity)
    channel = bot.get_channel(1244337321608876042)
    if channel:
        await channel.send('Jestem online')

# Wydarzenie, które jest wywoływane, gdy status użytkownika zmienia się na online
@bot.event
async def on_presence_update(before: discord.Member, after: discord.Member):
    # ID ról, które chcemy monitorować
    monitored_roles = {1249508176722661416, 941320096452841572}

    # Sprawdzenie, czy użytkownik przeszedł ze statusu offline na online
    if before.status == discord.Status.offline and after.status != discord.Status.offline:
        # Sprawdzanie, czy użytkownik ma jedną z wymaganych ról
        if any(role.id in monitored_roles for role in after.roles):
            # Pobieramy kanał, do którego wysyłamy wiadomość
            channel = after.guild.get_channel(1244337321608876042)
            if channel:
                await channel.send(f'{after.display_name} jest teraz online!')

# Komenda do zmiany pseudonimu użytkownika (wymaga uprawnień)
@bot.command(name='zmien_nick')
@commands.has_permissions(manage_nicknames=True)
async def change_nick(ctx, member: Member, *, new_nickname: str):
    try:
        old_nickname = member.display_name
        await member.edit(nick=new_nickname)
        await ctx.send(f'Pseudonim użytkownika {old_nickname} został zmieniony na {new_nickname}')
    except discord.Forbidden:
        await ctx.send('Nie mam uprawnień do zmiany pseudonimu tego użytkownika.')
    except discord.HTTPException as e:
        await ctx.send(f'Wystąpił błąd podczas zmiany pseudonimu: {e}')

blocked_nicknames = {}  # Słownik do przechowywania blokowanych pseudonimów {user_id: nick_to_block}

@bot.command()
@commands.has_permissions(administrator=True)
async def block_nickname(ctx, member: Member, nick: str):
    """Blokuje lub odblokowuje możliwość zmiany pseudonimu dla konkretnego użytkownika."""
    if member.id in blocked_nicknames:
        del blocked_nicknames[member.id]
        await ctx.send(f'Odblokowano zmianę pseudonimu dla użytkownika {member.display_name}.')
    else:
        blocked_nicknames[member.id] = nick
        await ctx.send(f'Zablokowano zmianę pseudonimu dla użytkownika {member.display_name}. '
                       f'Pseudonim zostanie zmieniony na "{nick}" w przypadku próby edycji.')

# Wydarzenie wywoływane podczas zmiany pseudonimu użytkownika
@bot.event
async def on_member_update(before: Member, after: Member):
    """Zapobiega zmianie pseudonimu dla użytkowników znajdujących się na liście blokowanych."""
    if after.id in blocked_nicknames:
        blocked_nick = blocked_nicknames[after.id]
        if before.nick != after.nick:
            try:
                await after.edit(nick=blocked_nick)
                print(f'Zmieniono pseudonim użytkownika {after.display_name} na "{blocked_nick}".')
            except discord.Forbidden:
                print(f'Bot nie ma uprawnień do zmiany pseudonimu użytkownika {after.display_name}.')
            except discord.HTTPException as e:
                print(f'Wystąpił błąd podczas zmiany pseudonimu użytkownika {after.display_name}: {e}')

# Uruchomienie bota z tokenem
def main() -> None:
    bot.run(token=TOKEN)

if __name__ == '__main__':
    main()

