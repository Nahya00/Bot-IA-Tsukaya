import discord, os, re
from openai import OpenAI
from collections import defaultdict

# ─── Intents ───────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True

# ─── Variables d’environnement ──────────────────────────────────────────────────
TOKEN                  = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY         = os.getenv("OPENAI_API_KEY")
SPECIAL_CHANNEL_ID     = int(os.getenv("SPECIAL_CHANNEL_ID"))     # salon IA
SANCTION_LOG_CHANNEL   = 1379270842499727491                       # logs sanctions

# ─── Clients ────────────────────────────────────────────────────────────────────
client = discord.Client(intents=intents)
openai = OpenAI(api_key=OPENAI_API_KEY)

# Mémoire conversation
user_histories = {}
MAX_HISTORY = 1000

# Mémoire sanctions : user_id → compteur de messages sexuels
warn_counts = defaultdict(int)

# ─── Liste de mots sexuels interdits ────────────────────────────────────────────
SEX_PATTERNS = [
    r"\bcul\b", r"\bbaise(?:r|s|z)?\b", r"\bniq(?:uer|ue|)\b",
    r"\bsexe\b", r"\bp[o0]rn\b", r"\bpénis\b", r"\bbite\b",
    r"\bchatte\b", r"\bfellatio[n]?\b", r"\bsodomie\b", r"\branle(r|tte)?"
]
SEX_RE = re.compile("|".join(SEX_PATTERNS), re.IGNORECASE)

# ─── IA OpenAI ──────────────────────────────────────────────────────────────────
async def ask_openai(user_id: int, prompt: str) -> str:
    history = user_histories.get(user_id, [])
    history.append({"role": "user", "content": prompt})

    completion = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": (
                        "Tu es **Zeydan**, un vrai mec de cité et de Discord, tu es Algérien et fière de Mascara vers Oran plus précisément."
                        "Tu insères quelques mots arabes quand tu parles."
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

# ─── Discord Events ─────────────────────────────────────────────────────────────
@client.event
async def on_ready():
    print("Tsukaya (humain) est en ligne !")

@client.event
async def on_message(message: discord.Message):
    if message.author == client.user:
        return

    if message.channel.id == SPECIAL_CHANNEL_ID:
        # ── Vérifie contenu sexuel ──
        if SEX_RE.search(message.content):
            user_id = message.author.id
            warn_counts[user_id] += 1
            count = warn_counts[user_id]

            try:
                sanction_channel = client.get_channel(SANCTION_LOG_CHANNEL) or \
                                   await client.fetch_channel(SANCTION_LOG_CHANNEL)

                if count == 1:
                    await sanction_channel.send(
                        f"+warn {message.author.mention} raison: contenu sexuel inapproprié dans le salon IA"
                    )
                elif count == 2:
                    await sanction_channel.send(
                        f"+warn {message.author.mention} raison: récidive contenu sexuel dans le salon IA"
                    )
                elif count >= 3:
                    await sanction_channel.send(
                        f"+tempmute {message.author.mention} 10m raison: récidive répétée contenu sexuel"
                    )
                    warn_counts[user_id] = 0  # reset après sanction

            except Exception as e:
                print(f"[Sanctions] Erreur d'envoi de la commande Crow : {e}")
            return  # on ne laisse pas l’IA répondre à ce genre de message

        # ── Sinon, réponse IA normale ──
        try:
            reply = await ask_openai(message.author.id, message.content)
            await message.channel.send(reply)
        except Exception as e:
            print("Erreur OpenAI :", e)
            await message.channel.send("💥 J’ai crashé, mdr.")

# ─── Lancement ──────────────────────────────────────────────────────────────────
client.run(TOKEN)
