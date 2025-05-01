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

async def ask_openai(prompt):
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Tu es un bot Discord drôle, insolent, moqueur avec des réponses courtes. "
                        "Tu trolles les utilisateurs avec humour, tu les provoques, et tu fais rire. "
                        "Mais si quelqu’un est triste ou inquiet, tu deviens bienveillant, rassurant et tu donnes de vrais conseils. "
                        "Réponds toujours dans la langue du message (français ou anglais)."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.9,
            max_tokens=100
        )
        return response.choices[0].message.content
    except Exception as e:
        print("Erreur OpenAI:", e)
        return "💥 Oups, bug avec mon cerveau OpenAI..."

@client.event
async def on_ready():
    print(f'{client.user} est prêt à clasher, soutenir et répondre dans le salon désigné.')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    try:
        if message.channel.id == SPECIAL_CHANNEL_ID:
            response = await ask_openai(message.content)
            await message.channel.send(response)
    except Exception as e:
        await message.channel.send("💢 Une erreur est survenue, désolé !")
        print("Exception:", e)

client.run(TOKEN)
