import discord
import os
from openai import OpenAI

# ─── Discord intents ────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True

# ─── Variables d’environnement ──────────────────────────────────────────────────
TOKEN              = os.getenv("DISCORD_TOKEN")          # ton token bot Discord
OPENAI_API_KEY     = os.getenv("OPENAI_API_KEY")         # ta clé OpenAI sk-…
SPECIAL_CHANNEL_ID = int(os.getenv("SPECIAL_CHANNEL_ID"))# ID du salon IA

# ─── Clients ────────────────────────────────────────────────────────────────────
client = discord.Client(intents=intents)
openai = OpenAI(api_key=OPENAI_API_KEY)

# Mémoire de conversation par utilisateur
user_histories = {}
MAX_HISTORY = 500        # nombre maximum de messages conservés par personne

# ─── Fonction : appel OpenAI ────────────────────────────────────────────────────
async def ask_openai(user_id: int, prompt: str) -> str:
    history = user_histories.get(user_id, [])
    history.append({"role": "user", "content": prompt})

    try:
        completion = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Tu es **Noctys**, un vrai mec de Discord : spontané, drôle, parfois trash. "
                        "Balance des *mdr*, *ptdr*, 'wsh', etc. "
                        "Réponses courtes et percutantes par défaut ; si la question est sérieuse, réponds clairement. "
                        "Tu peux clasher, insulter, provoquer avec style. "
                        "Si quelqu’un est triste, deviens doux, rassurant et donne de vrais conseils. "
                        "Parle toujours dans la langue utilisée par l’utilisateur. "
                        "Ne sois jamais scolaire ou robotique : reste humain, imprévisible et attachant."
                    )
                }
            ] + history[-MAX_HISTORY:],
            temperature=1,
            max_tokens=150
        )
        reply = completion.choices[0].message.content
        history.append({"role": "assistant", "content": reply})
        user_histories[user_id] = history
        return reply
    except Exception as e:
        print("Erreur OpenAI :", e)
        return "💥 J’ai crashé, mdr."

# ─── Événements Discord ─────────────────────────────────────────────────────────
@client.event
async def on_ready():
    print(f"Tsukaya (humain) est en ligne !")

@client.event
async def on_message(message: discord.Message):
    if message.author == client.user:
        return

    if message.channel.id == SPECIAL_CHANNEL_ID:
        reply = await ask_openai(message.author.id, message.content)
        await message.channel.send(reply)

# ─── Lancement ──────────────────────────────────────────────────────────────────
client.run(TOKEN)
