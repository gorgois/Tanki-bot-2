import os
import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp
import asyncio
from flask import Flask
import threading

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

app = Flask("")

@app.route("/")
def home():
    return "OK"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

threading.Thread(target=run_flask).start()

ydl_opts = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'extract_flat': False,
}

async def connect_to_voice(interaction: discord.Interaction):
    if interaction.user.voice is None or interaction.user.voice.channel is None:
        await interaction.response.send_message("You are not in a voice channel!", ephemeral=True)
        return None
    voice_channel = interaction.user.voice.channel
    if interaction.guild.voice_client is None:
        vc = await voice_channel.connect()
    else:
        vc = interaction.guild.voice_client
        if vc.channel != voice_channel:
            await vc.move_to(voice_channel)
    return vc

@tree.command(name="join", description="Join your voice channel")
async def join(interaction: discord.Interaction):
    vc = await connect_to_voice(interaction)
    if vc:
        await interaction.response.send_message(f"Joined {vc.channel}", ephemeral=False)

@tree.command(name="leave", description="Leave the voice channel")
async def leave(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc:
        await vc.disconnect()
        await interaction.response.send_message("Disconnected.", ephemeral=False)
    else:
        await interaction.response.send_message("I'm not in a voice channel.", ephemeral=True)

@tree.command(name="play", description="Play audio from a YouTube link")
@app_commands.describe(url="YouTube video URL")
async def play(interaction: discord.Interaction, url: str):
    vc = await connect_to_voice(interaction)
    if vc is None:
        return

    await interaction.response.defer()

    loop = asyncio.get_event_loop()

    def extract_info():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)

    try:
        info = await loop.run_in_executor(None, extract_info)
    except Exception as e:
        await interaction.followup.send(f"Error extracting info: {e}", ephemeral=True)
        return

    audio_url = info['url']
    title = info.get('title', 'Unknown title')

    if vc.is_playing():
        vc.stop()

    source = await discord.FFmpegOpusAudio.from_probe(audio_url)
    vc.play(source)

    await interaction.followup.send(f"🎶 Now playing: **{title}**", ephemeral=False)

@tree.command(name="stop", description="Stop playing music")
async def stop(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc and vc.is_playing():
        vc.stop()
        await interaction.response.send_message("Stopped the music.", ephemeral=False)
    else:
        await interaction.response.send_message("No music is playing.", ephemeral=True)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("Error: DISCORD_TOKEN environment variable not set.")
    else:
        bot.run(token)