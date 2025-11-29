import os
import discord
from collections import Counter
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()
TOKEN: str = os.getenv("GOURGANDIN_TOKEN")
GUILD_ID: int = int(os.getenv("GUILD_ID"))
NSFW_BOT_CHANNEL: str = "nsfw-manuel"


def report_bars_percent(counter, top_n=20, charset="unicode"):
    total = sum(counter.values())
    bars = []
    for word, count in counter.most_common(top_n):
        pct = count / total * 100
        bar_len = int(pct / 0.3)
        bar_char = "█" if charset == "unicode" else "-"
        bars.append(f"{word:<12} | {bar_char * bar_len:<12} {pct:5.1f}% ({count:>6})")
    return "\n".join(bars)


async def analyze_channel(client: discord.Client):
    guild = client.get_guild(GUILD_ID)
    nsfw_channel = discord.utils.get(guild.text_channels, name=NSFW_BOT_CHANNEL)

    first_words = []
    async for msg in nsfw_channel.history(limit=None):
        for embed in msg.embeds:
            if embed.title:
                word = embed.title.split()[0]
                first_words.append(word)

    counter = Counter(first_words)

    exclusions = {
        "Amateur", "Ass", "Big", "Cute",
        "Boobs", "Photographer", "Photographer:",
        "[Mature", "Mature",
        "Beautiful"
    }
    for word in exclusions:
        counter.pop(word, None)

    print("Clés restantes:", list(counter.keys())[:20])

    print("Top premiers mots d'embed :")
    for word, count in counter.most_common(20):
        print(f"{word} → {count} fois")

    print("```")
    print(report_bars_percent(counter, top_n=20, charset="unicode"))
    print("```")

# --- point d’entrée ---
if __name__ == "__main__":
    intents = discord.Intents.default()
    intents.messages = True
    intents.guilds = True
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f"Connecté en tant que {client.user}")
        await analyze_channel(client)
        await client.close()

    client.run(TOKEN)
