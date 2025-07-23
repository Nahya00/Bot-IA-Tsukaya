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
                "Tu es Zeydan, un mec de cité algérien, drôle et parfois trash. "
                "Tu ne robots jamais, tu parles en français et insères de l’arabe. "
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

    # ── zeydan ping everyone/here avec copie de phrase ─────────────────────────

    # ── zeydan ping everyone/here avec copie de phrase ─────────────────────────
    if message.content.lower().startswith("zeydan ping "):
        if any(role.id == AUTHORIZED_MENTION_ROLE for role in message.author.roles):
            parts = message.content.split(maxsplit=2)
            if len(parts) >= 3 and parts[1].lower() in ["everyone","here"]:
                mention = "@everyone" if parts[1].lower()=="everyone" else "@here"
                phrase = parts[2]
                await message.channel.send(
                    f"{mention} {phrase}",
                    allowed_mentions=discord.AllowedMentions(everyone=True)
                )
            else:
                await message.channel.send("❌ Usage: zeydan ping everyone|here <phrase>")
        else:
            await message.channel.send("🚫 Rôle non autorisé pour mentions.")
        return

    # ── manual ping pseudo réservé au rôle ───────────────────────────────────────
    if message.content.lower().startswith("ping "):
        if any(role.id == AUTHORIZED_MENTION_ROLE for role in message.author.roles):
            pseudo = message.content[5:].strip().lower()
            for m in message.guild.members:
                if pseudo in m.name.lower() or pseudo in m.display_name.lower():
                    await message.channel.send(f"{m.mention} {random.choice(["Répond !","On t’appelle !"])}")
                    return
        return

    # ── Réponse normale IA (salon IA ou mention) ───────────────────────────────
    if message.channel.id != SPECIAL_CHANNEL_ID and client.user not in message.mentions:
        return
    reply = await ask_openai(message.author.id, message.content)
    await message.channel.send(reply)

client.run(TOKEN)


