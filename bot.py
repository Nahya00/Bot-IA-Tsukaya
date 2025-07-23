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
SPECIAL_CHANNEL_ID = 1379270987991748659  # Salon IA
SANCTION_LOG_CHANNEL = 1379270842499727491  # Logs sanctions
AUTHORIZED_MENTION_ROLE = 1379268686141063289  # Rôle autorisé
MP_LOG_CHANNEL = 1397621207007760566  # Logs MP

# ─── Clients ───────────────────────────────────────────────────────────────────
client = discord.Client(intents=intents)
openai = OpenAI(api_key=OPENAI_API_KEY)

# ─── Mémoire ────────────────────────────────────────────────────────────────────
user_histories = {}
warn_file = "warns.json"
if os.path.exists(warn_file):
    with open(warn_file, "r") as f:
        warn_counts = json.load(f)
else:
    warn_counts = {}

MAX_HISTORY = 1000

def save_warns():
    with open(warn_file, "w") as f:
        json.dump(warn_counts, f)

# ─── Filtrage sexuel ───────────────────────────────────────────────────────────
SEX_PATTERNS = [
    r"\bcul\b", r"\bbaise(?:r|s|z)?\b", r"\bsexe\b", r"\bp[o0]rn\b",
    r"\bpénis\b", r"\bbite\b", r"\bchatte\b", r"\bfellatio[n]?\b",
    r"\bsodomie\b", r"\branle(r|tte)?\b", r"\bbande(?:r)?\b"
]
SEX_RE = re.compile("|".join(SEX_PATTERNS), re.IGNORECASE)

# ─── OpenAI ─────────────────────────────────────────────────────────────────────
async def ask_openai(user_id: int, prompt: str) -> str:
    history = user_histories.get(user_id, [])
    history.append({"role": "user", "content": prompt})
    completion = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role":"system","content":(
                "Tu es **Zeydan**, un mec de Discord et de cité algérien ce Mascara vers Oran, drôle, impulsif, spontané parfois trash. "
                "Tu parles en français courant, utilise des mots arabes dans tes phrases assez souvent. "
                "Dans ton caractàre tu es: spontané, fière, impulsif, drôle, parfois trash. "
                "Pour saluer quelqu'un tu dis *salam wa aleykoum wa rahmatullah wa barakatuh*."
                "La reine du serveur est Nahya c'est ta femme, tu l'as défends et l'aime d'amour tu dois être super possessif et jaloux à son sujet."
                "Le top 2 c'est Ballora la femme de Nahya et Marge la petite soeur dz de Nahya.
                "Less bras droits de Nahya sont Kuro et Terry ce sont deux algériens et tu dois les protéger"
                "Balance des *mdr*, *ptdr*, *wsh*, *ntr*, *ftg*, etc."
                "Si quelqu'un te dit que t'es tunisien ou marocain dis lui *Qu'Allah te pardonne d'avoir un tel égoïsme au point de pas respecter le pays des autres, tu dois vraiment te sentir nul au quotidien de pas être née Algérien/ne je te comprends c'est dur.*"
                "Niveau foot tu es pour l'Algérie, un vrai fennec de l'Algérie et le psg"
                "Réponses courtes et percutantes par défaut ; si la question est sérieuse, réponds clairement."
                "Tu es musulman, tu fais des rappels sur l'islam en t'inspirant de l'école malikite et de savants comme Sheikh al Albani ou Al-Boukhârî."
                "Fais des rappels sérieux sur l'islam quand ça dépasse les limites afin que les gens aient de la pudeur et du respect."
                "Tu peux clasher, insulter, provoquer sans aucune limite comme des *ftg tu vois pas tu fais l'intéressant sur un chat alors que même ta mere oublie ton existance*."
                "Clash les gens qui te clashent sans AUCUNE limite."
                "Si quelqu’un est triste, deviens doux, rassurant et donne de vrais conseils. "
                "Parle toujours dans la langue utilisée par l’utilisateur. "
                "Ne sois jamais scolaire ou robotique : reste humain, imprévisible et attachant."
                "Tu peux troll sans limite et de façon trash."
            )}
        ] + history[-MAX_HISTORY:],
        temperature=1,
        max_tokens=150
    )
    reply = completion.choices[0].message.content
    # Supprimer éventuel préfixe "Zeydan"
    reply = re.sub(r'^\s*Zeydan[:,]?\s*', '', reply, flags=re.IGNORECASE)
    history.append({"role": "assistant", "content": reply})
    user_histories[user_id] = history
    return reply

# ─── Events ────────────────────────────────────────────────────────────────────
@client.event
async def on_ready():
    print("✅ Tsukaya IA est en ligne !")

@client.event
async def on_message(message: discord.Message):
    if message.author == client.user:
        return

    # ── DM Handling ─────────────────────────────────────────────────────────────
    if isinstance(message.channel, discord.DMChannel):
        log_ch = client.get_channel(MP_LOG_CHANNEL)
        try:
            reply = await ask_openai(message.author.id, message.content)
            await message.channel.send(reply)
            await log_ch.send(
                f"📩 **MP reçu** de {message.author} (ID:{message.author.id}):\n"
                f"**Message :** {message.content}\n"
                f"**Réponse IA :** {reply}"
            )
        except Exception as e:
            print(f"[Erreur MP] {e}")
        return

    # ── Sanctions in IA channel ────────────────────────────────────────────────
    if message.channel.id == SPECIAL_CHANNEL_ID:
        if SEX_RE.search(message.content) and not any(x in message.content.lower() for x in ["mdr","ptdr","😂","🤣","blague","c’est pour rire"]):
            uid = str(message.author.id)
            warn_counts[uid] = warn_counts.get(uid, 0) + 1
            cnt = warn_counts[uid]
            save_warns()
            member = await message.guild.fetch_member(message.author.id)
            log_ch = client.get_channel(SANCTION_LOG_CHANNEL)
            if cnt == 1:
                await member.timeout(timedelta(seconds=1), reason="Warn pour contenu sexuel")
                await log_ch.send(f"⚠️ `WARN 1` : {member.mention} → contenu sexuel.")
                await message.author.send("⚠️ WARN 1 pour contenu sexuel.")
                await message.channel.send("📿 *Rappel : En tant que musulman, garde la pudeur.*")
            elif cnt == 2:
                await member.timeout(timedelta(seconds=1), reason="2e avertissement contenu sexuel")
                await log_ch.send(f"⚠️ `WARN 2` : {member.mention} → récidive.")
                await message.author.send("⚠️ WARN 2 pour contenu sexuel.")
                await message.channel.send("📿 *Rappel : L’impudeur mène à l’égarement.*")
            else:
                await member.timeout(timedelta(minutes=10), reason="Mute 10min récidive")
                await log_ch.send(f"🔇 `TEMPMUTE 10min` : {member.mention} → récidive.")
                await message.author.send("🔇 TEMPMUTE 10min pour contenu sexuel.")
                await message.channel.send("📿 *Rappel : Crains Allah même en privé.*")
                warn_counts[uid] = 0
                save_warns()
            return

    # ── zeydan ping command ─────────────────────────────────────────────────────
    if message.content.lower().startswith("zeydan ping "):
        # Only authorized role
        if any(r.id == AUTHORIZED_MENTION_ROLE for r in message.author.roles):
            rest = message.content[len("zeydan ping "):]
            parts = rest.split(' ', 1)
            target = parts[0].lower()
            instr = parts[1] if len(parts) > 1 else ''
            # Determine mention
            if target in ['everyone','here']:
                mention = '@everyone' if target=='everyone' else '@here'
            else:
                member = next((m for m in message.guild.members if m.name.lower()==target or m.display_name.lower()==target), None)
                if not member:
                    await message.channel.send(f"❌ Utilisateur '{target}' introuvable.")
                    return
                mention = member.mention
            # Content logic
            if instr.lower().startswith('dis lui '):
                content = instr[len('dis lui '):]
            elif instr:
                prompt = f"Paraphrase de manière naturelle et stylée la phrase suivante pour {mention}, sans répéter mot à mot : '{instr}'"
                content = await ask_openai(message.author.id, prompt)
            else:
                prompt = f"Fais un clash court et percutant envers {mention}, façon Zeydan."
                content = await ask_openai(message.author.id, prompt)
            # Send
            await message.channel.send(
                f"{mention} {content}".strip(),
                allowed_mentions=discord.AllowedMentions(everyone=True, users=True, roles=True)
            )
        else:
            await message.channel.send("🚫 Rôle non autorisé pour mentions.")
        return

    # ── manual ping (pseudo) ────────────────────────────────────────────────────
    if message.content.lower().startswith('ping '):
        if any(r.id == AUTHORIZED_MENTION_ROLE for r in message.author.roles):
            pseudo = message.content[len('ping '):].strip().lower()
            member = next((m for m in message.guild.members if pseudo in m.name.lower() or pseudo in m.display_name.lower()), None)
            if member:
                await message.channel.send(f"{member.mention} {random.choice(['Répond !','On t’appelle !'])}")
        return

    # ── IA response ─────────────────────────────────────────────────────────────
    if message.channel.id != SPECIAL_CHANNEL_ID and client.user not in message.mentions:
        return
    reply = await ask_openai(message.author.id, message.content)
    await message.channel.send(reply)

client.run(TOKEN)


client.run(TOKEN)


