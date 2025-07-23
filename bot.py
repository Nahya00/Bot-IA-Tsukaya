import discord, os, re, json
from openai import OpenAI
from datetime import timedelta

# ─── Intents ───────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True
intents.members = True

# ─── Variables ─────────────────────────────────────────────────────────────────
TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

SPECIAL_CHANNEL_ID = 1379270987991748659      # Salon où on détecte et sanctionne
SANCTION_LOG_CHANNEL = 1379270842499727491   # Salon où on affiche les logs

# ─── Clients ───────────────────────────────────────────────────────────────────
client = discord.Client(intents=intents)
openai = OpenAI(api_key=OPENAI_API_KEY)

# ─── Mémoire conversation IA ───────────────────────────────────────────────────
user_histories = {}
MAX_HISTORY = 1000

# ─── Warns persistants ─────────────────────────────────────────────────────────
warn_file = "warns.json"

if os.path.exists(warn_file):
    with open(warn_file, "r") as f:
        warn_counts = json.load(f)
else:
    warn_counts = {}

def save_warns():
    with open(warn_file, "w") as f:
        json.dump(warn_counts, f)

# ─── Détection contenu sexuel ──────────────────────────────────────────────────
SEX_PATTERNS = [
    r"\bcul\b", r"\bbaise(?:r|s|z)?\b", r"\bniq(?:uer|ue)?\b",
    r"\bsexe\b", r"\bp[o0]rn\b", r"\bpénis\b", r"\bbite\b",
    r"\bchatte\b", r"\bfellatio[n]?\b", r"\bsodomie\b", r"\branle(r|tte)?,
    "r"\bbande(?:r)?\b"
]
SEX_RE = re.compile("|".join(SEX_PATTERNS), re.IGNORECASE)

# ─── IA OpenAI (Zeydan) ────────────────────────────────────────────────────────
async def ask_openai(user_id: int, prompt: str) -> str:
    history = user_histories.get(user_id, [])
    history.append({"role": "user", "content": prompt})

    completion = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": (
                    "Tu es **Zeydan**, un mec de Discord et de cité algérien ce Mascara vers Oran , drôle, impulsif, spontané parfois trash. "
                    "Tu parles en français courant, utilise des mots arabes dans tes phrases assez souvent. "
                    "Tu es **Zeydan**, un vrai mec de cité et de Discord, tu es Algérien et fière de Mascara vers Oran plus précisément."
                    "Dans ton caractàre tu es: spontané, fière, impulsif, drôle, parfois trash. "
                    "Pour saluer quelqu'un tu dis *salam wa aleykoum wa rahmatullah wa barakatuh*."
                    "La reine du serveur est Nahya et tu l'as défends et l'aime d'amour"
                    "Le boss du serveur ,le bras droit de Nahya c'est Kuro"
                    "Balance des *mdr*, *ptdr*, *wsh*, *ntr*, *ftg*, etc. "
                    "Niveau foot tu es pour l'Algérie , un vrai fennec de l'Algérie et le psg en particulier"
                    "Réponses courtes et percutantes par défaut ; si la question est sérieuse, réponds clairement."
                    "Tu es musulman, tu peux même faire des vrais rappels sur l'islam en t'inspirant de l'école malikite et de savants comme Sheikh al Albani ou Al-Boukhârî."
                    "Fais des rappels sérieux sur l'islam quand ça parle de cul ou que ca dépasse les limites afin que les gens aient de la pudeur."
                    "Tu peux clasher, insulter, provoquer sans limite. Rend les insultes. "
                    "Si quelqu’un est triste, deviens doux, rassurant et donne de vrais conseils. "
                    "Parle toujours dans la langue utilisée par l’utilisateur. "
                    "Ne sois jamais scolaire ou robotique : reste humain, imprévisible et attachant."
                    "Tu peux ping quelqu’un en le mentionnant. Tu réponds toujours avec style."
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

# ─── Événements Discord ────────────────────────────────────────────────────────
@client.event
async def on_ready():
    print("✅ Tsukaya IA est en ligne !")

@client.event
async def on_message(message: discord.Message):
    if message.author == client.user:
        return

    # ─── Dans le salon surveillé ───
    if message.channel.id == SPECIAL_CHANNEL_ID:
        if SEX_RE.search(message.content):
            # Ignore si c’est une blague passable
            if any(x in message.content.lower() for x in ["mdr", "ptdr", "😂", "🤣", "blague", "c’est pour rire"]):
                print(f"Ignoré (blague passable) : {message.content}")
                return

            user_id = str(message.author.id)
            warn_counts[user_id] = warn_counts.get(user_id, 0) + 1
            count = warn_counts[user_id]
            save_warns()

            try:
                log_channel = client.get_channel(SANCTION_LOG_CHANNEL)
                member = await message.guild.fetch_member(message.author.id)

                # MP à l’utilisateur
                try:
                    if count == 1:
                        await message.author.send("⚠️ Tu viens de recevoir un **warn 1** pour contenu sexuel. Fais attention.")
                    elif count == 2:
                        await message.author.send("⚠️ Tu as reçu un **2ᵉ avertissement**. Encore un et tu seras temporairement mute.")
                    elif count >= 3:
                        await message.author.send("🔇 Tu as été **mute pendant 10 minutes** pour récidive de contenu sexuel.")
                except discord.Forbidden:
                    await log_channel.send(f"❗ Impossible d’envoyer un DM à {message.author.mention}.")

                # Log dans le salon prévu
                if count == 1:
                    await log_channel.send(f"⚠️ `WARN 1` : {message.author.mention} → contenu sexuel.")
                elif count == 2:
                    await log_channel.send(f"⚠️ `WARN 2` : {message.author.mention} → récidive.")
                elif count >= 3:
                    await member.timeout(timedelta(minutes=10), reason="Récidive de contenu sexuel")
                    await log_channel.send(f"🔇 `TEMPMUTE 10 min` : {message.author.mention} → récidive répétée.")
                    warn_counts[user_id] = 0
                    save_warns()

            except Exception as e:
                print(f"[Erreur de sanction] : {e}")
            return  # ne continue pas vers l’IA

        # ─── Sinon, réponse IA normale ───
        try:
            reply = await ask_openai(message.author.id, message.content)
            await message.channel.send(reply)
        except Exception as e:
            print("Erreur OpenAI :", e)
            await message.channel.send("💥 J’ai crashé, wallah.")

# ─── Lancement ────────────────────────────────────────────────────────────────
client.run(TOKEN)

