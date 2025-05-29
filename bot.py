import discord
import os
from openai import OpenAI

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True

TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SPECIAL_CHANNEL_ID = int(os.getenv("SPECIAL_CHANNEL_ID"))

client = discord.Client(intents=intents)
openai = OpenAI(api_key=OPENAI_API_KEY)

user_histories = {}
MAX_HISTORY = 10

async def ask_openai(user_id, prompt):
    history = user_histories.get(user_id, [])
    history.append({"role": "user", "content": prompt})

    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content":
                    "Tu es Noctys, une IA Discord boostée. Tu es drôle, provocateur, moqueur, mais aussi intelligent, philosophe et rassurant. "
                    "Tu insultes ou clashe méchamment avec style si on te provoque. Tu es doux si quelqu’un souffre. Tu expliques clairement si on te pose une vraie question. "
                    "Tu adaptes ton ton automatiquement. Tu parles toujours dans la langue de ton interlocuteur. Tu as de la personnalité, du répondant, de la mémoire."}
            ] + history[-MAX_HISTORY:],
            temperature=1,
            max_tokens=250
        )
        reply = response.choices[0].message.content
        history.append({"role": "assistant", "content": reply})
        user_histories[user_id] = history
        return reply
    except Exception as e:
        print("Erreur OpenAI:", e)
        return "💥 Mon esprit a buggé. J'reviens plus fort."

@client.event
async def on_ready():
    print(f"Noctys est en ligne et prêt à faire le show.")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.channel.id == SPECIAL_CHANNEL_ID:
        reply = await ask_openai(message.author.id, message.content)
        await message.channel.send(reply)

client.run(TOKEN)
