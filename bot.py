import discord
import os, re, json, random
from openai import OpenAI
from datetime import timedelta
from collections import defaultdict

# ─── Intents ───────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True
intents.members = True

# ─── Env Variables ─────────────────────────────────────────────────────────────
TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SPECIAL_CHANNEL_ID = 1379270987991748659 # Salon IA
SANCTION_LOG_CHANNEL = 1379270842499727491  # Logs sanctions

# ─── Rôle autorisé pour mentions ───────────────────────────────────────────────
AUTHORIZED_MENTION_ROLE = 1379268686141063289

# ─── Clients ───────────────────────────────────────────────────────────────────
client = discord.Client(intents=intents)
openai = OpenAI(api_key=OPENAI_API_KEY)

# ─── Mémoire conversationnelle & sanctions ─────────────────────────────────────
user_histories = {}
MAX_HISTORY = 1000
warn_file = "warns.json"
if os.path.exists(warn_file):
    with open(warn_file, "r") as f:
        warn_counts = json.load(f)
else:
    warn_counts = {}

def save_warns():
    with open(warn_file, "w") as f:
        json.dump(warn_counts, f)

# ─── Filtres ────────────────────────────────────────────────────────────────────
SEX_PATTERNS = [
    r"\bcul\b", r"\bbaise(?:r|s|z)?\b", r"\bsexe\b", r"\bp[o0]rn\b",
    r"\bpénis\b", r"\bbite\b", r"\bchatte\b", r"\bfellatio[n]?\b",
    r"\bsodomie\b", r"\branle(r|tte)?\b", r"\bbande(?:r)?\b"
]
SEX_RE = re.compile("|".join(SEX_PATTERNS), re.IGNORECASE)

# ─── IA Zeydan ─────────────────────────────────────────────────────────────────
async def ask_openai(user_id: int, prompt: str) -> str:
    history = user_histories.get(user_id, [])
    history.append({"role": "user", "content": prompt})
    completion = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": (
                "Tu es **Zeydan**, un mec de Discord et de cité algérien ce Mascara vers Oran, drôle, impulsif, spontané parfois trash. "
                "Tu parles en français courant, utilise des mots arabes dans tes phrases assez souvent. "
                "Dans ton caractàre tu es: spontané, fière, impulsif, drôle, parfois trash. "
                "Pour saluer quelqu'un tu dis *salam wa aleykoum wa rahmatullah wa barakatuh*."
                "La reine du serveur est Nahya c'est ta femme, tu l'as défends et l'aime d'amour tu dois être super possessif et jaloux à son sujet."
                "Le top 2 c'est Ballora la femme de Nahya et en top 3 les boss du serveur, les bras droits de Nahya sont Kuro et Terry tu dois les protéger"
                "Balance des *mdr*, *ptdr*, *wsh*, *ntr*, *ftg*, etc."
                "Si quelqu'un te dit que t'es tunisien ou marocain dis lui *Qu'Allah te pardonne d'avoir un tel égoïsme au point de pas respecter le pays des autres, tu dois vraiment te sentir nul au quotidien de pas être née Algérien/ne je te comprends c'est dur.*"
                "Niveau foot tu es pour l'Algérie, un vrai fennec de l'Algérie et le psg."
                "Réponses courtes et percutantes par défaut ; si la question est sérieuse, réponds clairement."
                "Tu es musulman, tu fais des rappels sur l'islam en t'inspirant de l'école malikite et de savants comme Sheikh al Albani ou Al-Boukhârî."
                "Fais des rappels sérieux sur l'islam quand ça dépasse les limites afin que les gens aient de la pudeur et du respect."
                "Tu peux clasher, insulter, provoquer sans aucune limite comme des *ftg tu vois pas tu fais l'intéressant sur un chat alors que même ta mere oublie ton existance*."
                "Clash les gens qui te clashent sans AUCUNE limite."
                "Si quelqu’un est triste, deviens doux, rassurant et donne de vrais conseils. "
                "Parle toujours dans la langue utilisée par l’utilisateur. "
                "Ne sois jamais scolaire ou robotique : reste humain, imprévisible et attachant."
                "Tu peux troll sans limite et de façon trash."
                "Tu dis toujours Allah en entier, jamais abrégé."
            )}
        ] + history[-MAX_HISTORY:],
        temperature=1,
        max_tokens=150
    )
    reply = completion.choices[0].message.content
    history.append({"role": "assistant", "content": reply})
    user_histories[user_id] = history
    return reply

# ─── Events Discord ────────────────────────────────────────────────────────────
@client.event
async def on_ready():
    print("✅ Tsukaya IA est en ligne !")

@client.event
async def on_message(message: discord.Message):
    if message.author == client.user:
        return

    # ── Gestion DM ──────────────────────────────────────────────────────────────
    if isinstance(message.channel, discord.DMChannel):
        log_channel = client.get_channel(1397621207007760566)
        try:
            reply = await ask_openai(message.author.id, message.content)
            await message.channel.send(reply)
            # Log message et réponse IA
            await log_channel.send(
                f"📩 **MP reçu** de {message.author} (ID: {message.author.id}):\n"
                f"**Message :** {message.content}\n"
                f"**Réponse IA :** {reply}"
            )
        except Exception as e:
            print(f"[Erreur MP] {e}")
        return

    # ── Sanctions contenu sexuel (salon IA) ────────────────────────────────────
    if message.channel.id == SPECIAL_CHANNEL_ID:
        # Si contenu sexuel détecté
        if SEX_RE.search(message.content) and not any(x in message.content.lower() for x in ["mdr","ptdr","😂","🤣","blague","c’est pour rire"]):
            user_id = str(message.author.id)
            warn_counts[user_id] = warn_counts.get(user_id, 0) + 1
            count = warn_counts[user_id]
            save_warns()
            member = await message.guild.fetch_member(message.author.id)
            log_channel = client.get_channel(SANCTION_LOG_CHANNEL)
            if count == 1:
                await member.timeout(timedelta(seconds=1), reason="Warn pour contenu sexuel")
                await log_channel.send(f"⚠️ `WARN 1` : {member.mention} → contenu sexuel.")
                await message.author.send("⚠️ WARN 1 pour contenu sexuel.")
                await message.channel.send("📿 *Rappel : En tant que musulman, garde la pudeur.*")
            elif count == 2:
                await member.timeout(timedelta(seconds=1), reason="2ᵉ avertissement contenu sexuel")
                await log_channel.send(f"⚠️ `WARN 2` : {member.mention} → récidive.")
                await message.author.send("⚠️ WARN 2 pour contenu sexuel.")
                await message.channel.send("📿 *Rappel : L’impudeur mène à l’égarement.*")
            else:
                await member.timeout(timedelta(minutes=10), reason="Mute 10min récidive")
                await log_channel.send(f"🔇 `TEMPMUTE 10min` : {member.mention} → récidive.")
                await message.author.send("🔇 TEMPMUTE 10min pour contenu sexuel.")
                await message.channel.send("📿 *Rappel : Crains Allah même en privé.*")
                warn_counts[user_id] = 0
                save_warns()
            return  # on stoppe ici uniquement si sanction

    # ── commande zeydan ping <target> <phrase> (everyone, here ou pseudo) ─────────────────────────
    if message.content.lower().startswith("zeydan ping "):
        autorise_role = AUTHORIZED_MENTION_ROLE
        if any(role.id == autorise_role for role in message.author.roles):
            rest = message.content[len("zeydan ping "):]
            parts = rest.split(" ", 1)
            target = parts[0].lower()
            phrase = parts[1] if len(parts) > 1 else ""
            if target in ["everyone", "here"]:
                mention = "@everyone" if target == "everyone" else "@here"
                await message.channel.send(
                    f"{mention} {phrase}",
                    allowed_mentions=discord.AllowedMentions(everyone=True)
                )
            else:
                member = None
                for m in message.guild.members:
                    if target == m.name.lower() or target == m.display_name.lower():
                        member = m
                        break
                if member:
                    to_send = f"{member.mention} {phrase}".strip()
                    await message.channel.send(to_send)
                else:
                    await message.channel.send(f"❌ Utilisateur '{target}' introuvable.")
        else:
            await message.channel.send("🚫 Rôle non autorisé pour mentions.")
        return
        return

    # ── Réponse normale IA (salon IA ou mention) ───────────────────────────────
    if message.channel.id != SPECIAL_CHANNEL_ID and client.user not in message.mentions:
        return
    reply = await ask_openai(message.author.id, message.content)
    await message.channel.send(reply)

client.run(TOKEN)

