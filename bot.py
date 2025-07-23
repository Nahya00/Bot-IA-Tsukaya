import discord, os, re, json
from openai import OpenAI
from collections import defaultdict

# ─── Intents ───────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True
intents.members = True

# ─── Variables d’environnement ──────────────────────────────────────────────────
TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

SPECIAL_CHANNEL_ID = 1379270842499727491       # salon IA surveillé
SANCTION_LOG_CHANNEL = 1379415848338591745     # salon log sanctions

# ─── Clients ────────────────────────────────────────────────────────────────────
client = discord.Client(intents=intents)
openai = OpenAI(api_key=OPENAI_API_KEY)

# ─── Mémoire conversationnelle ──────────────────────────────────────────────────
user_histories = {}
MAX_HISTORY = 1000

# ─── Base de warns persistante ──────────────────────────────────────────────────
warn_file = "warns.json"

if os.path.exists(warn_file):
    with open(warn_file, "r") as f:
        warn_counts = json.load(f)
else:
    warn_counts = {}

def save_warns():
    with open(warn_file, "w") as f:
        json.dump(warn_counts, f)

# ─── Liste de mots sexuels interdits ────────────────────────────────────────────
SEX_PATTERNS = [
    r"\bcul\b", r"\bbaise(?:r|s|z)?\b", r"\bniq(?:uer|ue|)\b",
    r"\bsexe\b", r"\bp[o0]rn\b", r"\bpénis\b", r"\bbite\b",
    r"\bchatte\b", r"\bfellatio[n]?\b", r"\bsodomie\b", r"\branle(r|tte)?"
]
SEX_RE = re.compile("|".join(SEX_PATTERNS), re.IGNORECASE)

# ─── OpenAI IA Zeydan ───────────────────────────────────────────────────────────
async def ask_openai(user_id: int, prompt: str) -> str:
    history = user_histories.get(user_id, [])
    history.append({"role": "user", "content": prompt})

    completion = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": (
                    "Tu es **Zeydan**, un mec de cité algérien, drôle, spontané, impulsif, parfois trash. "
                    "Tu insères des mots en arabe, tu soutiens Nahya la reine du serveur et Kuro le boss son bras droit. "
                    "Pour saluer quelqu'un tu dis *salam wa aleykoum wa rahmatullah wa barakatuh*."
                    "Balance des *mdr*, *ptdr*, *wsh*, *ntr*, *ftg*, etc. "
                    "Tu peux mentionner des gens avec leur pseudo Discord."
                    "Niveau foot tu es pour l'Algérie , un vrai fennec de l'Algérie et le psg en particulier"
                    "Réponses courtes et percutantes par défaut ; si la question est sérieuse, réponds clairement avec tes connaissances."
                    "Tu es musulman, tu peux même faire des vrais rappels sur l'islam en t'inspirant de l'école malikite et de savants comme Sheikh al Albani ou Al-Boukhârî."
                    "Fais des rappels sérieux sur l'islam quand ça parle de cul ou que ca dépasse les limites afin que les gens aient de la pudeur."
                    "Tu peux clasher, insulter, provoquer sans aucune limite. Rend les insultes. "
                    "Si quelqu’un est triste, deviens doux, rassurant et donne de vrais conseils. "
                    "Parle toujours dans la langue utilisée par l’utilisateur. "
                    "Ne sois jamais scolaire ou robotique : reste humain, imprévisible et attachant."
                    "Lorsqu'il s'agit de rappel ou de sujet sérieux tu peux écrire des longs messages si nécessaire."
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

# ─── Events Discord ─────────────────────────────────────────────────────────────
@client.event
async def on_ready():
    print("Tsukaya IA est connectée 🧠🔥")

@client.event
async def on_message(message: discord.Message):
    if message.author == client.user:
        return

    if message.channel.id == SPECIAL_CHANNEL_ID:
        if SEX_RE.search(message.content):
            # 🧠 Ignore les blagues
            if any(x in message.content.lower() for x in ["blague", "mdr", "ptdr", "😂", "🤣", "haha", "c’était pour rire"]):
                print(f"Ignoré (blague) : {message.content}")
                return

            user_id = str(message.author.id)
            warn_counts[user_id] = warn_counts.get(user_id, 0) + 1
            count = warn_counts[user_id]
            save_warns()

            try:
                member = await message.guild.fetch_member(message.author.id)
                log_channel = client.get_channel(SANCTION_LOG_CHANNEL)

                # 📨 MP
                try:
                    if count == 1:
                        await message.author.send("⚠️ Tu as reçu un **warn 1** pour contenu sexuel dans le salon IA.")
                    elif count == 2:
                        await message.author.send("⚠️ Deuxième **warn** reçu. Un troisième = mute.")
                    elif count >= 3:
                        await message.author.send("🔇 Tu as été **mute 10 minutes** pour récidive de contenu sexuel.")
                except discord.Forbidden:
                    await log_channel.send(f"⚠️ Impossible d’envoyer un MP à {message.author.mention}.")

                # 📜 Logs
                if count == 1:
                    await log_channel.send(f"⚠️ `WARN 1` : {message.author.mention} → contenu sexuel.")
                elif count == 2:
                    await log_channel.send(f"⚠️ `WARN 2` : {message.author.mention} → récidive.")
                elif count >= 3:
                    await member.timeout(600, reason="Récidive de contenu sexuel")
                    await log_channel.send(f"🔇 `TEMPMUTE 10min` : {message.author.mention} → récidive répétée.")
                    warn_counts[user_id] = 0
                    save_warns()

            except Exception as e:
                print(f"[Sanctions] Erreur : {e}")
            return  # n’envoie pas la réponse IA dans ce cas

        # 🤖 Réponse normale IA
        try:
            reply = await ask_openai(message.author.id, message.content)
            await message.channel.send(reply)
        except Exception as e:
            print("Erreur OpenAI :", e)
            await message.channel.send("💥 J’ai crashé, wsh.")

# ─── Lancement ──────────────────────────────────────────────────────────────────
client.run(TOKEN)
