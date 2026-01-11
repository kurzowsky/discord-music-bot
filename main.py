import os
import asyncio
import random
from typing import Final
from itertools import cycle

# Importy bibliotek zewnętrznych
import discord
from discord import Intents, Member
from discord.ext import commands, tasks
from dotenv import load_dotenv
import yt_dlp

# Importy własne
from responses import get_faceit_stats

# ==========================================
# KONFIGURACJA I ZMIENNE ŚRODOWISKOWE
# ==========================================

load_dotenv()
TOKEN: Final[str] = os.getenv('DISCORD_TOKEN')

# Definicja intentów (uprawnień) dla bota
intents: Intents = Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

bot = commands.Bot(command_prefix='!', intents=intents)
bot.remove_command('help') # Usuwamy domyślną komendę help, bo mamy własną

# Konfiguracja Youtube (yt-dlp)
YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    # 'quiet': True, # Można odkomentować, żeby zmniejszyć ilość logów
}

# Konfiguracja FFmpeg (przetwarzanie dźwięku)
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

# ==========================================
# GLOBALNE ZMIENNE I PAMIĘĆ BOTA
# ==========================================

queue = [] # Kolejka utworów
last_deleted_msg = {} # Pamięć usuniętych wiadomości (Snipe)
ostatnie_druzyny = {"A": [], "B": []} # Pamięć losowania drużyn
blocked_nicknames = {} # Zablokowane nicki

# Zmienne do Auto-Rozłączania (15 min)
voice_inactivity_timer = {}  # {guild_id: minuty_bezczynnosci}
last_music_channel = {}      # {guild_id: kanal_tekstowy_do_pozegnania}

# ==========================================
# 🎵 SYSTEM MUZYCZNY (LOGIKA)
# ==========================================

def check_queue(ctx):
    """Sprawdza kolejkę po zakończeniu utworu i puszcza następny."""
    if queue:
        next_query = queue.pop(0)
        print(f"Pobieram z kolejki: {next_query}")
        
        # Wywołanie asynchronicznej funkcji z poziomu synchronicznego callbacka
        bot = ctx.bot
        coro = play_audio(ctx, next_query)
        fut = asyncio.run_coroutine_threadsafe(coro, bot.loop)
        try:
            fut.result()
        except Exception as e:
            print(f"Błąd w check_queue: {e}")
    else:
        print("Kolejka pusta.")

async def play_audio(ctx, query):
    """Główna funkcja pobierająca i odtwarzająca dźwięk."""
    voice_client = ctx.voice_client

    try:
        loop = asyncio.get_event_loop()
        
        # Rozpoznawanie czy to link czy wyszukiwanie
        search_query = query if query.startswith("http") else f"ytsearch:{query}"

        # Pobieranie informacji o utworze (bez pobierania pliku na dysk)
        data = await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(YDL_OPTIONS).extract_info(search_query, download=False))

        info = None
        if 'entries' in data:
            if len(data['entries']) > 0:
                info = data['entries'][0]
            else:
                await ctx.send("❌ Nie znaleziono wyników.")
                return check_queue(ctx)
        else:
            info = data

        url = info['url']
        title = info.get('title', 'Nieznany utwór')

        # Odtwarzanie
        # Używamy systemowego ffmpeg (ważne dla Docker/Railway)
        source = discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS)
        voice_client.play(source, after=lambda e: check_queue(ctx))
        
        await ctx.send(f"🎵 Gram: **{title}**")

    except Exception as e:
        print(f"Błąd odtwarzania: {e}")
        await ctx.send("❌ Wystąpił błąd. Przechodzę do następnego utworu.")
        check_queue(ctx)

# ==========================================
# 🎵 KOMENDY MUZYCZNE
# ==========================================

@bot.command()
async def play(ctx, *, query):
    """Odtwarza muzykę z YouTube (obsługuje linki i tytuły)."""
    
    # Aktualizacja zmiennych do Auto-Rozłączania
    last_music_channel[ctx.guild.id] = ctx.channel 
    voice_inactivity_timer[ctx.guild.id] = 0
    
    if not ctx.author.voice:
        await ctx.send("❌ Musisz być na kanale głosowym!")
        return

    voice_channel = ctx.author.voice.channel
    if ctx.voice_client is None:
        await voice_channel.connect()
    elif ctx.voice_client.channel != voice_channel:
        await ctx.voice_client.move_to(voice_channel)

    voice_client = ctx.voice_client

    # Logika kolejki
    if voice_client.is_playing():
        if len(queue) >= 5:
            await ctx.send("❌ Kolejka jest pełna! (Limit: 5 utworów)")
            return
        queue.append(query)
        await ctx.send(f"➕ Dodano do kolejki: **{query}** (pozycja: {len(queue)})")
    else:
        await play_audio(ctx, query)

@bot.command()
async def skip(ctx):
    """Pomija obecny utwór."""
    voice_client = ctx.voice_client
    if voice_client and voice_client.is_playing():
        voice_client.stop() # To wywoła 'after' -> check_queue
        await ctx.send("⏭️ **Pominięto utwór!**")
    else:
        await ctx.send("❌ Nic teraz nie gra.")

@bot.command()
async def stop(ctx):
    """Zatrzymuje muzykę i wyrzuca bota."""
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

# ==========================================
# ⏰ SYSTEM AUTO-ROZŁĄCZANIA (TASK)
# ==========================================

@tasks.loop(minutes=1.0)
async def check_inactivity():
    """Sprawdza co minutę aktywność bota na kanałach głosowych."""
    for voice_client in bot.voice_clients:
        guild_id = voice_client.guild.id

        # Jeśli gra lub pauza -> reset licznika
        if voice_client.is_playing() or voice_client.is_paused():
            voice_inactivity_timer[guild_id] = 0
        else:
            # Cisza -> zwiększamy licznik
            timer = voice_inactivity_timer.get(guild_id, 0)
            voice_inactivity_timer[guild_id] = timer + 1
            print(f"Licznik bezczynności dla serwera {guild_id}: {timer + 1} min")

            # Po 15 minutach rozłączamy
            if voice_inactivity_timer[guild_id] >= 15:
                await voice_client.disconnect()
                voice_inactivity_timer[guild_id] = 0
                
                # Wiadomość pożegnalna
                if guild_id in last_music_channel:
                    channel = last_music_channel[guild_id]
                    try:
                        await channel.send("💤 **Brak aktywności przez 15 minut.** Wychodzę z kanału. Pa! 👋")
                    except Exception:
                        pass

# ==========================================
# 🎮 CS2, FACEIT I ORGANIZACJA GRY
# ==========================================

@bot.command()
async def faceit(ctx, *, profile_url: str):
    """Sprawdza statystyki gracza Faceit."""
    try:
        # Obsługa linku lub samego nicku
        if "faceit.com" in profile_url or "faceittracker.net" in profile_url:
            player_name = profile_url.split("/")[-1]
        else:
            player_name = str(profile_url)

        stats = get_faceit_stats(player_name)
        if not stats:
            await ctx.send("Nie udało się pobrać statystyki. Sprawdź poprawność nicku.")
            return

        embed = discord.Embed(title=f"**Statystyki FACEIT dla {player_name}**", color=0x00ff00)
        embed.add_field(name="Poziom", value=stats["level"], inline=True)
        embed.add_field(name="ELO", value=stats["elo"], inline=True)
        embed.add_field(name="Mecze", value=stats["matches"], inline=True)
        embed.add_field(name="Win Rate", value=f"{stats['winrate']}", inline=True)
        embed.add_field(name="Headshot %", value=f"{stats['headshots']}", inline=True)
        embed.add_field(name="K/D", value=f"{stats['kd_ratio']}", inline=True)
        
        embed.add_field(name="**OSTATNIE 10 MECZÓW**", value="----------------", inline=False)
        embed.add_field(name="K/D (Last 10)", value=f"{stats['k/d_ratio_last_10']}", inline=True)
        embed.add_field(name="Bilans", value=f"W: {stats['wins']} / L: {stats['losses']}", inline=True)
        embed.add_field(name="Wyniki", value=f"`{stats['last_10_results']}`", inline=True)

        embed.set_footer(text="Dane z FaceitTracker.net")
        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send("Wystąpił błąd podczas przetwarzania.")
        print(e)

@bot.command()
async def teams(ctx):
    """Losuje dwie drużyny z osób na kanale głosowym."""
    global ostatnie_druzyny

    if not ctx.author.voice:
        await ctx.send("❌ Musisz być na kanale głosowym!")
        return

    members = ctx.author.voice.channel.members
    players = [member for member in members if not member.bot]

    if len(players) < 2:
        await ctx.send("❌ Za mało osób (minimum 2).")
        return

    random.shuffle(players)
    mid = len(players) // 2
    team_a = players[:mid]
    team_b = players[mid:]

    ostatnie_druzyny["A"] = team_a
    ostatnie_druzyny["B"] = team_b

    team_a_names = [p.display_name for p in team_a]
    team_b_names = [p.display_name for p in team_b]

    embed = discord.Embed(title="⚔️ Wylosowane Drużyny", description="Użyj `!mv A` lub `!mv B` aby przenieść.", color=discord.Color.gold())
    embed.add_field(name="🔴 Team A", value="\n".join(team_a_names), inline=True)
    embed.add_field(name="🔵 Team B", value="\n".join(team_b_names), inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def mv(ctx, team_letter: str):
    """Automatycznie przenosi wybrany Team na wolny kanał."""
    team_letter = team_letter.upper()

    if team_letter not in ["A", "B"]:
        await ctx.send("❌ Wybierz drużynę A lub B.")
        return

    if not ostatnie_druzyny[team_letter]:
        await ctx.send("❌ Brak zapisanej drużyny. Użyj najpierw `!teams`.")
        return

    if not ctx.author.voice:
        await ctx.send("❌ Musisz być na kanale głosowym.")
        return

    current_channel = ctx.author.voice.channel
    guild = ctx.guild

    # Szukanie dostępnych kanałów
    available_channels = [
        ch for ch in guild.voice_channels 
        if ch != current_channel and ch.permissions_for(guild.me).move_members
    ]

    if not available_channels:
        await ctx.send("❌ Nie znalazłem wolnego kanału.")
        return

    # Priorytet dla pustych kanałów
    empty_channels = [ch for ch in available_channels if len(ch.members) == 0]
    target_channel = empty_channels[0] if empty_channels else available_channels[0]

    count = 0
    await ctx.send(f"🚀 Przenoszę **Team {team_letter}** na kanał **{target_channel.name}**...")

    try:
        for member in ostatnie_druzyny[team_letter]:
            if member.voice:
                await member.move_to(target_channel)
                count += 1
                await asyncio.sleep(0.5)
        
        await ctx.send(f"✅ Przeniesiono {count} graczy.")

    except Exception as e:
        await ctx.send(f"❌ Błąd: {e}")

# ==========================================
# 🎲 4FUN I UŻYTECZNE
# ==========================================

@bot.command()
async def moneta(ctx):
    await ctx.send(f"Wypadło: **{random.choice(['🪙 Orzeł', '🪙 Reszka'])}**")

@bot.command()
async def kostka(ctx):
    await ctx.send(f"🎲 Wyrzuciłeś: **{random.randint(1, 6)}**")

@bot.command()
@commands.cooldown(rate=1, per=60, type=commands.BucketType.user)
@commands.has_role("ping")
async def ping(ctx, member: discord.Member):
    """Troll-ping: przerzuca użytkownika po kanałach."""
    guild = ctx.guild
    if not member.voice:
        await ctx.send("Ten użytkownik nie jest na kanale głosowym.")
        return

    original_channel = member.voice.channel
    voice_channels = [c for c in guild.voice_channels if c != original_channel]

    if len(voice_channels) < 2:
        await ctx.send("Za mało kanałów do zabawy.")
        return

    channels = random.sample(voice_channels, 2)
    await ctx.send(f"😈 Przerzucanie {member.mention}...")

    try:
        for i in range(5):
            await member.move_to(channels[i % 2])
            await asyncio.sleep(1)
        await member.move_to(original_channel)
        await ctx.send(f"Uff, {member.display_name} wrócił.")
    except Exception as e:
        await ctx.send(f"Błąd: {e}")

@ping.error
async def ping_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ Cooldown! Poczekaj {int(error.retry_after)}s.")
    elif isinstance(error, commands.MissingRole):
        await ctx.send("❌ Potrzebujesz roli `ping`.")

# ==========================================
# 🛡️ ADMINISTRACJA I MODERACJA
# ==========================================

@bot.command()
@commands.has_permissions(manage_messages=True)
async def usun(ctx, ilosc: int = 5):
    """Czyści wiadomości."""
    await ctx.channel.purge(limit=ilosc + 1)
    await ctx.send(f"🗑️ Usunięto {ilosc} wiadomości.", delete_after=3)

@bot.command(name='zmien_nick')
@commands.has_permissions(manage_nicknames=True)
async def change_nick(ctx, member: Member, *, new_nickname: str):
    """Zmienia nick użytkownika."""
    try:
        await member.edit(nick=new_nickname)
        await ctx.send(f'✅ Zmieniono nick na {new_nickname}')
    except Exception as e:
        await ctx.send(f'❌ Błąd: {e}')

@bot.command()
@commands.has_permissions(administrator=True)
async def block_nickname(ctx, member: Member, nick: str):
    """Blokuje zmianę nicku."""
    if member.id in blocked_nicknames:
        del blocked_nicknames[member.id]
        await ctx.send(f'🔓 Odblokowano nick dla {member.display_name}.')
    else:
        blocked_nicknames[member.id] = nick
        await ctx.send(f'🔒 Zablokowano nick "{nick}" dla {member.display_name}.')

@bot.command()
async def snipe(ctx):
    """Pokazuje ostatnią usuniętą wiadomość."""
    channel_id = ctx.channel.id
    
    if channel_id not in last_deleted_msg:
        await ctx.send("❌ Brak usuniętych wiadomości w pamięci.")
        return
    
    saved = last_deleted_msg[channel_id]
    description = saved["content"] if saved["content"] else "*[Samo zdjęcie]*"

    embed = discord.Embed(description=description, color=discord.Color.red(), timestamp=saved["time"])
    embed.set_author(name=f"{saved['author'].display_name} usunął:", icon_url=saved['author'].display_avatar.url)
    
    if saved["image"]:
        embed.set_image(url=saved["image"])

    embed.set_footer(text="Złapano w 4K 📸")
    await ctx.send(embed=embed)

@bot.command()
async def pomoc(ctx):
    """Menu pomocy."""
    embed = discord.Embed(
        title="🤖 Centrum Pomocy",
        description="Oto lista komend. Użyj `!` przed każdą.",
        color=discord.Color.from_rgb(0, 153, 255)
    )
    
    embed.add_field(name="🎵 Muzyka", value="`!play`, `!stop`, `!skip`, `!pause`, `!resume`", inline=False)
    embed.add_field(name="🎮 CS2", value="`!faceit`, `!teams`, `!mv`", inline=False)
    embed.add_field(name="🎲 4Fun", value="`!moneta`, `!kostka`, `!ping`", inline=False)
    embed.add_field(name="🛡️ Admin", value="`!usun`, `!zmien_nick`, `!block_nickname`, `!snipe`, `!regulamin`", inline=False)
    
    embed.set_thumbnail(url=bot.user.avatar.url if bot.user.avatar else None)
    await ctx.send(embed=embed)

@bot.command()
async def regulamin(ctx):
    """Wyświetla regulamin."""
    # (Tutaj skróciłem treść dla czytelności kodu, ale wklej swoją pełną treść jeśli chcesz)
    embed = discord.Embed(title="📜 Regulamin", description="1. Szanuj innych.\n2. Bez spamu.\n3. Admin ma zawsze rację.", color=discord.Color.blue())
    await ctx.send(embed=embed)

# ==========================================
# 🔔 EVENTY (ZDARZENIA)
# ==========================================

@bot.event
async def on_message_delete(message):
    if message.author.bot: return
    image_url = message.attachments[0].proxy_url if message.attachments else None
    last_deleted_msg[message.channel.id] = {
        "content": message.content,
        "author": message.author,
        "time": discord.utils.utcnow(),
        "image": image_url
    }

@bot.event
async def on_member_update(before: Member, after: Member):
    if after.id in blocked_nicknames:
        required_nick = blocked_nicknames[after.id]
        if after.nick != required_nick:
            try:
                await after.edit(nick=required_nick)
            except:
                pass

@bot.event
async def on_presence_update(before: discord.Member, after: discord.Member):
    monitored_roles = {1249508176722661416, 941320096452841572}
    if before.status == discord.Status.offline and after.status != discord.Status.offline:
        if any(role.id in monitored_roles for role in after.roles):
            channel = after.guild.get_channel(1244337321608876042)
            if channel:
                await channel.send(f'👋 {after.display_name} jest teraz online!')

@bot.event
async def on_ready() -> None:
    print(f'{bot.user} jest online')
    
    # Uruchomienie pętli sprawdzającej bezczynność (15 min)
    if not check_inactivity.is_running():
        check_inactivity.start()
        
    activity = discord.CustomActivity(name='🤖 !pomoc | kurzowsky 👑')
    await bot.change_presence(activity=activity)
    
    # Wiadomość startowa (opcjonalnie)
    channel = bot.get_channel(1244337321608876042)
    if channel:
        await channel.send(embed=discord.Embed(title="🚨 Jestem online 🚨", color=discord.Color.green()))

# ==========================================
# START BOTA
# ==========================================

if __name__ == '__main__':
    bot.run(token=TOKEN)
