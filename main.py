import asyncio
import random
import datetime
import discord
from discord import Intents, Member
from discord.ext import commands, tasks
import yt_dlp
import os

# Importy własne
from responses import get_faceit_stats
import config  # Importujemy ustawienia z config.py

# ==========================================
# INICJALIZACJA BOTA
# ==========================================

intents: Intents = Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

bot = commands.Bot(command_prefix='!', intents=intents)
bot.remove_command('help')

# ==========================================
# GLOBALNE ZMIENNE
# ==========================================

queue = []
last_deleted_msg = {}
ostatnie_druzyny = {"A": [], "B": []}
blocked_nicknames = {}
voice_inactivity_timer = {}
last_music_channel = {}

# ==========================================
# 🎵 SYSTEM MUZYCZNY
# ==========================================

def check_queue(ctx):
    """Sprawdza kolejkę po zakończeniu utworu i puszcza następny."""
    if queue:
        next_query = queue.pop(0)
        bot = ctx.bot
        coro = play_audio(ctx, next_query)
        fut = asyncio.run_coroutine_threadsafe(coro, bot.loop)
        try:
            fut.result()
        except Exception as e:
            print(f"Błąd w check_queue: {e}")
    else:
        print("Kolejka pusta.")

def cleanup_file(filename):
    """Funkcja pomocnicza: Usuwa plik z dysku, żeby nie zapchać serwera."""
    try:
        if filename and os.path.exists(filename):
            os.remove(filename)
            print(f"🗑️ Usunięto plik: {filename}")
    except Exception as e:
        print(f"❌ Błąd usuwania pliku: {e}")

# main.py - podmień tylko funkcję play_audio

async def play_audio(ctx, query):
    """Tryb Szybki: Streamowanie z ciasteczkami (Low Latency)."""
    voice_client = ctx.voice_client
    
    try:
        loop = asyncio.get_running_loop()
        search_query = query if query.startswith("http") else f"ytsearch:{query}"
        
        # 1. POBIERANIE LINKU (download=False = Szybkość)
        # Pobieramy tylko URL, nie cały plik. To trwa ułamki sekund.
        data = await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(config.YDL_OPTIONS).extract_info(search_query, download=False))

        info = data['entries'][0] if 'entries' in data else data
        if not info:
            await ctx.send("❌ Nie znaleziono wyników.")
            return check_queue(ctx)

        url = info['url'] # To jest link bezpośredni do audio
        title = info.get('title', 'Nieznany')
        duration = info.get('duration', 0)
        thumbnail = info.get('thumbnail', None)

        # 2. ODTWARZANIE (STREAM)
        # FFmpeg łączy się bezpośrednio z YouTube, używając ciasteczek z configu
        source = discord.FFmpegPCMAudio(url, **config.FFMPEG_OPTIONS)
        
        voice_client.play(source, after=lambda e: check_queue(ctx))
        
        # Embed
        embed = discord.Embed(title="🎵 Teraz gram", description=f"[{title}]({info.get('webpage_url','')})", color=discord.Color.blurple())
        if thumbnail: embed.set_thumbnail(url=thumbnail)
        embed.add_field(name="Czas", value=str(datetime.timedelta(seconds=duration)), inline=True)
        embed.add_field(name="Dodał", value=ctx.author.display_name, inline=True)
        await ctx.send(embed=embed)

    except Exception as e:
        print(f"Play Error: {e}")
        await ctx.send("❌ Błąd odtwarzania.")
        check_queue(ctx)

# ==========================================
# 🎵 KOMENDY MUZYCZNE
# ==========================================

@bot.command()
async def play(ctx, *, query):
    """Odtwarza muzykę z YouTube."""
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
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭️ **Pominięto utwór!**")
    else:
        await ctx.send("❌ Nic teraz nie gra.")

@bot.command()
async def stop(ctx):
    """Zatrzymuje muzykę i wyrzuca bota."""
    if ctx.voice_client:
        queue.clear()
        await ctx.voice_client.disconnect()
        await ctx.send("🛑 Zatrzymano muzykę i rozłączono.")

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
# ⏰ SYSTEM AUTO-ROZŁĄCZANIA
# ==========================================

@tasks.loop(minutes=1.0)
async def check_inactivity():
    """Sprawdza aktywność co minutę."""
    for voice_client in bot.voice_clients:
        guild_id = voice_client.guild.id
        
        # Jeśli gra lub pauza lub są ludzie na kanale -> reset licznika
        if voice_client.is_playing() or voice_client.is_paused() or len(voice_client.channel.members) > 1:
            voice_inactivity_timer[guild_id] = 0
        else:
            voice_inactivity_timer[guild_id] = voice_inactivity_timer.get(guild_id, 0) + 1
            
            if voice_inactivity_timer[guild_id] >= 15:
                await voice_client.disconnect()
                voice_inactivity_timer[guild_id] = 0
                if guild_id in last_music_channel:
                    try:
                        await last_music_channel[guild_id].send("💤 **Brak aktywności przez 15 minut.** Wychodzę z kanału. Pa! 👋")
                    except:
                        pass

# ==========================================
# 🎮 CS2 & FACEIT
# ==========================================

@bot.command()
async def faceit(ctx, *, profile_url: str):
    """Sprawdza statystyki gracza Faceit."""
    msg = await ctx.send("🔍 Pobieram dane z Faceit...")
    
    try:
        if "faceit.com" in profile_url or "faceittracker.net" in profile_url:
            player_name = profile_url.split("/")[-1]
        else:
            player_name = str(profile_url)

        # Uruchamiamy funkcję w tle, żeby nie blokować bota
        loop = asyncio.get_running_loop()
        stats = await loop.run_in_executor(None, get_faceit_stats, player_name)

        if not stats:
            await msg.edit(content="Nie udało się pobrać statystyki. Sprawdź poprawność nicku.")
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
        await msg.delete()
        await ctx.send(embed=embed)

    except Exception as e:
        await msg.edit(content="Wystąpił błąd podczas przetwarzania.")
        print(e)

@bot.command()
async def teams(ctx):
    """Losuje dwie drużyny."""
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
    """Przenosi Team na wolny kanał."""
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

    # Szukanie pustych kanałów
    available_channels = [
        ch for ch in guild.voice_channels 
        if ch != current_channel and len(ch.members) == 0
    ]
    
    # Jeśli nie ma pustych, weź jakikolwiek inny
    if not available_channels:
        available_channels = [ch for ch in guild.voice_channels if ch != current_channel]

    if not available_channels:
        await ctx.send("❌ Nie znalazłem wolnego kanału.")
        return

    target_channel = available_channels[0]
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
# 🎲 4FUN I INNE
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
# 🛡️ ADMINISTRACJA
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
        try:
            await member.edit(nick=nick)
        except:
            pass
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
    """Menu pomocy - Twoja oryginalna wersja."""
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
    """Wyświetla regulamin - Twoja oryginalna wersja."""
    embed = discord.Embed(title="📜 Regulamin", description="1. Szanuj innych.\n2. Bez spamu.\n3. Admin ma zawsze rację.", color=discord.Color.blue())
    await ctx.send(embed=embed)

# ==========================================
# 🔔 EVENTY
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
    if before.status == discord.Status.offline and after.status != discord.Status.offline:
        # Sprawdzamy, czy użytkownik ma jedną z ról z config.py
        user_roles = {r.id for r in after.roles}
        if not config.MONITORED_ROLES.isdisjoint(user_roles):
            if config.WELCOME_CHANNEL_ID:
                channel = after.guild.get_channel(config.WELCOME_CHANNEL_ID)
                if channel:
                    await channel.send(f'👋 {after.display_name} jest teraz online!')

@bot.event
async def on_ready() -> None:
    print(f'{bot.user} jest online')
    
    if not check_inactivity.is_running():
        check_inactivity.start()
        
    activity = discord.CustomActivity(name='🤖 !pomoc | kurzowsky 👑')
    await bot.change_presence(activity=activity)
    
    if config.WELCOME_CHANNEL_ID:
        channel = bot.get_channel(config.WELCOME_CHANNEL_ID)
        if channel:
            await channel.send(embed=discord.Embed(title="🚨 Jestem online 🚨", color=discord.Color.green()))

if __name__ == '__main__':
    bot.run(token=config.TOKEN)