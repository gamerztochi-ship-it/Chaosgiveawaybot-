import logging
import csv
import io
import json
import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)

# ============ CONFIG ============
BOT_TOKEN = "8649968862:AAFbV0IOW72JQpI7L_16d1GuMa7a4CtPrRM"
OWNER_ID = 6730329053
DATA_FILE = "giveaway_data.json"
ADMINS_FILE = "admins.json"
CHANNEL_FILE = "channel.json"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============ DATA MANAGEMENT ============
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"users": {}, "joined_ids": [], "left_users": []}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def load_admins():
    if os.path.exists(ADMINS_FILE):
        with open(ADMINS_FILE, "r") as f:
            return json.load(f)
    return []

def save_admins(admins):
    with open(ADMINS_FILE, "w") as f:
        json.dump(admins, f, indent=2)

def load_channel():
    if os.path.exists(CHANNEL_FILE):
        with open(CHANNEL_FILE, "r") as f:
            return json.load(f).get("channel", "@CHAOSINDIA")
    return "@CHAOSINDIA"

def save_channel(channel):
    with open(CHANNEL_FILE, "w") as f:
        json.dump({"channel": channel}, f)

def is_owner(user_id):
    return user_id == OWNER_ID

def is_admin(user_id):
    return user_id == OWNER_ID or user_id in load_admins()

def get_user_entry(data, user_id):
    return data["users"].get(str(user_id))

# ============ /start ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = str(user.id)
    data = load_data()
    channel = load_channel()

    args = context.args
    if args and args[0] == "giveaway":
        if user_id not in data["users"]:
            try:
                link_obj = await context.bot.create_chat_invite_link(
                    chat_id=channel,
                    name=f"ref_{user_id}",
                    creates_join_request=False
                )
                invite_link = link_obj.invite_link
            except Exception as e:
                logger.error(f"Link create error: {e}")
                invite_link = f"https://t.me/{channel.replace('@','')}"

            data["users"][user_id] = {
                "name": user.full_name,
                "username": user.username or "N/A",
                "invite_link": invite_link,
                "invited_count": 0,
                "invited_ids": []
            }
            save_data(data)

        invite_link = data["users"][user_id]["invite_link"]
        count = data["users"][user_id]["invited_count"]

        text = (
            f"🎉 *Welcome to CHAOS INDIA Giveaway, {user.first_name}!*\n\n"
            f"You're now registered! Here's your unique invite link:\n"
            f"🔗 `{invite_link}`\n\n"
            f"👥 *Total Invites So Far:* `{count}`\n\n"
            f"📌 *How It Works:*\n"
            f"1️⃣ Share your unique link with friends\n"
            f"2️⃣ Every real member who joins via your link counts\n"
            f"3️⃣ The more invites, the higher your rank!\n\n"
            f"⚠️ *Warning:* Fake accounts or bot invites will get you *disqualified and banned* automatically.\n\n"
            f"🏆 *Prizes:*\n"
            f"🥇 1st — ₹400\n"
            f"🥈 2nd — ₹300\n"
            f"🥉 3rd — ₹200\n"
            f"🎖 4th — Admin in Group Chat\n\n"
            f"❌ Want to leave the giveaway? Use /leave anytime.\n\n"
            f"Good luck! 🔥"
        )

        keyboard = [
            [InlineKeyboardButton("📊 My Stats", callback_data="mystats"),
             InlineKeyboardButton("👑 Leaderboard", callback_data="leaderboard")]
        ]
        await update.message.reply_text(text, parse_mode="Markdown",
                                        reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        bot_username = (await context.bot.get_me()).username
        keyboard = [
            [InlineKeyboardButton("🎯 Join Giveaway", url=f"https://t.me/{bot_username}?start=giveaway")],
            [InlineKeyboardButton("👑 Leaderboard", callback_data="leaderboard")]
        ]
        await update.message.reply_text(
            "👋 *CHAOS INDIA GIVEAWAY BOT*\n\nPress the button below to participate in the giveaway!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# ============ TRACK NEW MEMBERS ============
async def track_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.new_chat_members:
        return

    new_members = update.message.new_chat_members
    data = load_data()

    for member in new_members:
        new_id = str(member.id)

        if new_id in data.get("joined_ids", []):
            continue

        data["joined_ids"].append(new_id)

        invite_link_used = None
        if update.message.invite_link:
            invite_link_used = update.message.invite_link.invite_link

        if invite_link_used:
            for uid, udata in data["users"].items():
                if udata["invite_link"] == invite_link_used:
                    if new_id != uid:
                        udata["invited_ids"].append(new_id)
                        udata["invited_count"] += 1
                    break

    save_data(data)

# ============ /mystats ============
async def mystats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()
    entry = get_user_entry(data, user_id)

    if not entry:
        await update.message.reply_text("❌ You are not registered!\n\nUse /start to join.")
        return

    sorted_users = sorted(data["users"].values(), key=lambda x: x["invited_count"], reverse=True)
    rank = next((i+1 for i, u in enumerate(sorted_users) if u["invite_link"] == entry["invite_link"]), "N/A")
    count = entry["invited_count"]

    # Progress bar (goal: 50 invites)
    goal = 50
    filled = min(int((count / goal) * 10), 10)
    bar = "█" * filled + "░" * (10 - filled)
    percent = min(int((count / goal) * 100), 100)

    text = (
        f"📊 *Your Giveaway Stats*\n\n"
        f"👤 Name: {entry['name']}\n"
        f"🔗 Your Invite Link: `{entry['invite_link']}`\n"
        f"👥 Total Invites: `{count}`\n"
        f"🏆 Current Rank: `#{rank}`\n\n"
        f"📈 Progress: `{bar}` {percent}%\n"
        f"_{count}/{goal} invites to goal_\n\n"
        f"_Keep sharing to climb the leaderboard!_ 🔥"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def mystats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    data = load_data()
    entry = get_user_entry(data, user_id)

    if not entry:
        await query.message.reply_text("❌ You are not registered! Use /start to join.")
        return

    sorted_users = sorted(data["users"].values(), key=lambda x: x["invited_count"], reverse=True)
    rank = next((i+1 for i, u in enumerate(sorted_users) if u["invite_link"] == entry["invite_link"]), "N/A")
    count = entry["invited_count"]

    goal = 50
    filled = min(int((count / goal) * 10), 10)
    bar = "█" * filled + "░" * (10 - filled)
    percent = min(int((count / goal) * 100), 100)

    text = (
        f"📊 *Your Giveaway Stats*\n\n"
        f"👤 Name: {entry['name']}\n"
        f"🔗 Your Invite Link: `{entry['invite_link']}`\n"
        f"👥 Total Invites: `{count}`\n"
        f"🏆 Current Rank: `#{rank}`\n\n"
        f"📈 Progress: `{bar}` {percent}%\n"
        f"_{count}/{goal} invites to goal_\n\n"
        f"_Keep sharing to climb the leaderboard!_ 🔥"
    )
    await query.message.reply_text(text, parse_mode="Markdown")

# ============ /leaderboard ============
async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    sorted_users = sorted(data["users"].values(), key=lambda x: x["invited_count"], reverse=True)[:10]

    if not sorted_users:
        await update.message.reply_text("❌ No participants yet!")
        return

    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    text = "👑 *CHAOS INDIA GIVEAWAY — TOP 10*\n\n"
    for i, u in enumerate(sorted_users):
        name = u["name"][:20]
        text += f"{medals[i]} `#{i+1}` *{name}* — `{u['invited_count']} invites`\n"

    text += "\n_Share your link and climb the ranks!_ 🔥"
    await update.message.reply_text(text, parse_mode="Markdown")

async def leaderboard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = load_data()
    sorted_users = sorted(data["users"].values(), key=lambda x: x["invited_count"], reverse=True)[:10]

    if not sorted_users:
        await query.message.reply_text("❌ No participants yet!")
        return

    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    text = "👑 *CHAOS INDIA GIVEAWAY — TOP 10*\n\n"
    for i, u in enumerate(sorted_users):
        name = u["name"][:20]
        text += f"{medals[i]} `#{i+1}` *{name}* — `{u['invited_count']} invites`\n"

    text += "\n_Share your link and climb the ranks!_ 🔥"
    await query.message.reply_text(text, parse_mode="Markdown")

# ============ /leave (USER) ============
async def leave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user = update.effective_user
    data = load_data()

    if user_id not in data["users"]:
        await update.message.reply_text("❌ You are not registered in the giveaway.")
        return

    entry = data["users"][user_id]

    # Remove invites this user gave to others
    for invited_id in entry.get("invited_ids", []):
        for uid, udata in data["users"].items():
            if invited_id in udata.get("invited_ids", []):
                udata["invited_ids"].remove(invited_id)
                udata["invited_count"] = max(0, udata["invited_count"] - 1)
                break

    # Log the leave
    if "left_users" not in data:
        data["left_users"] = []
    data["left_users"].append({
        "name": entry["name"],
        "username": entry.get("username", "N/A"),
        "user_id": user_id,
        "had_invites": entry["invited_count"]
    })

    del data["users"][user_id]
    save_data(data)

    await update.message.reply_text(
        "✅ You have been removed from the giveaway.\n\n"
        "Your invite link is now inactive and all your data has been deleted.\n\n"
        "_You can rejoin anytime using /start._",
        parse_mode="Markdown"
    )


# ============ /leavelog (ADMIN) ============
async def leave_log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    data = load_data()
    left = data.get("left_users", [])

    if not left:
        await update.message.reply_text("📋 No one has left the giveaway yet.")
        return

    text = f"📋 *Users Who Left Giveaway*\n\n_Total: {len(left)}_\n\n"
    for i, u in enumerate(left, 1):
        text += f"`{i}.` *{u['name']}* (@{u['username']}) — had `{u['had_invites']}` invites\n"

    await update.message.reply_text(text, parse_mode="Markdown")

# ============ /kick (ADMIN) ============
async def kick_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    if not context.args:
        await update.message.reply_text("Usage: `/kick @username` or `/kick userID`", parse_mode="Markdown")
        return

    query_input = context.args[0].replace("@", "").lower()
    data = load_data()

    found_uid = None
    for uid, udata in data["users"].items():
        if uid == query_input or (udata.get("username") or "").lower() == query_input:
            found_uid = uid
            break

    if not found_uid:
        await update.message.reply_text("❌ User not found in giveaway.")
        return

    removed = data["users"].pop(found_uid)

    # Remove their invites from others
    for invited_id in removed.get("invited_ids", []):
        for uid, udata in data["users"].items():
            if invited_id in udata.get("invited_ids", []):
                udata["invited_ids"].remove(invited_id)
                udata["invited_count"] = max(0, udata["invited_count"] - 1)
                break

    # Log it
    if "left_users" not in data:
        data["left_users"] = []
    data["left_users"].append({
        "name": removed["name"],
        "username": removed.get("username", "N/A"),
        "user_id": found_uid,
        "had_invites": removed["invited_count"],
        "kicked": True
    })

    save_data(data)

    await update.message.reply_text(
        f"🚫 *User Kicked from Giveaway*\n\n"
        f"👤 Name: {removed['name']}\n"
        f"📛 Username: @{removed.get('username','N/A')}\n"
        f"🆔 ID: `{found_uid}`\n"
        f"👥 Had Invites: `{removed['invited_count']}`\n\n"
        f"All their data and invite counts removed.",
        parse_mode="Markdown"
    )

# ============ /check (ADMIN) ============
async def check_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    if not context.args:
        await update.message.reply_text("Usage: `/check @username` or `/check userID`", parse_mode="Markdown")
        return

    query_input = context.args[0].replace("@", "").lower()
    data = load_data()

    found = None
    found_uid = None
    for uid, udata in data["users"].items():
        if uid == query_input or (udata.get("username") or "").lower() == query_input:
            found = udata
            found_uid = uid
            break

    if not found:
        await update.message.reply_text("❌ User not found.")
        return

    sorted_users = sorted(data["users"].values(), key=lambda x: x["invited_count"], reverse=True)
    rank = next((i+1 for i, u in enumerate(sorted_users) if u["invite_link"] == found["invite_link"]), "N/A")

    text = (
        f"🔍 *User Details*\n\n"
        f"👤 Name: {found['name']}\n"
        f"🆔 User ID: `{found_uid}`\n"
        f"📛 Username: @{found['username']}\n"
        f"🔗 Invite Link: `{found['invite_link']}`\n"
        f"👥 Total Invites: `{found['invited_count']}`\n"
        f"🏆 Rank: `#{rank}`\n"
        f"📋 Invited IDs: `{', '.join(found['invited_ids']) if found['invited_ids'] else 'None'}`"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

# ============ /stats (ADMIN) ============
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    data = load_data()
    total_users = len(data["users"])
    total_invites = sum(u["invited_count"] for u in data["users"].values())
    total_left = len(data.get("left_users", []))
    top_user = max(data["users"].values(), key=lambda x: x["invited_count"]) if data["users"] else None

    text = (
        f"📊 *Giveaway Stats*\n\n"
        f"👥 Total Participants: `{total_users}`\n"
        f"🔗 Total Invites: `{total_invites}`\n"
        f"🚪 Total Left: `{total_left}`\n\n"
    )

    if top_user:
        text += f"🏆 Top Inviter: *{top_user['name']}* — `{top_user['invited_count']} invites`"

    await update.message.reply_text(text, parse_mode="Markdown")

# ============ /winner (ADMIN) ============
async def winner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    data = load_data()
    if not data["users"]:
        await update.message.reply_text("❌ No participants yet!")
        return

    sorted_users = sorted(
        [(uid, udata) for uid, udata in data["users"].items()],
        key=lambda x: x[1]["invited_count"],
        reverse=True
    )[:4]

    prizes = ["🥇 ₹400", "🥈 ₹300", "🥉 ₹200", "🎖 Admin in GC"]
    text = "🏆 *GIVEAWAY RESULTS*\n\n"
    for i, (uid, u) in enumerate(sorted_users):
        text += f"{prizes[i]} — *{u['name']}* (@{u['username']}) — `{u['invited_count']} invites`\n"

    text += "\n🎉 Congratulations to all winners!"
    await update.message.reply_text(text, parse_mode="Markdown")

# ============ /announce (ADMIN) ============
async def announce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    if not context.args:
        await update.message.reply_text("Usage: `/announce Your message here`", parse_mode="Markdown")
        return

    message = " ".join(context.args)
    data = load_data()

    if not data["users"]:
        await update.message.reply_text("❌ No registered users to announce to.")
        return

    success = 0
    failed = 0

    await update.message.reply_text(f"📢 Sending to {len(data['users'])} users...")

    for uid in data["users"]:
        try:
            await context.bot.send_message(
                chat_id=int(uid),
                text=f"📢 *Announcement from CHAOS INDIA Giveaway*\n\n{message}",
                parse_mode="Markdown"
            )
            success += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1

    await update.message.reply_text(
        f"✅ Announcement sent!\n\n"
        f"✔️ Success: `{success}`\n"
        f"❌ Failed: `{failed}` (users who blocked bot)"
    )

# ============ /setchannel (ADMIN) ============
async def set_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    if not context.args:
        current = load_channel()
        await update.message.reply_text(
            f"📌 *Current Channel:* `{current}`\n\nUsage: `/setchannel @channelname`",
            parse_mode="Markdown"
        )
        return

    new_channel = context.args[0]
    if not new_channel.startswith("@"):
        new_channel = "@" + new_channel

    save_channel(new_channel)
    await update.message.reply_text(
        f"✅ Channel set to `{new_channel}`",
        parse_mode="Markdown"
    )

# ============ /removechannel (ADMIN) ============
async def remove_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    save_channel("@CHAOSINDIA")
    await update.message.reply_text("✅ Channel reset to default: `@CHAOSINDIA`", parse_mode="Markdown")

# ============ /reset (ADMIN) ============
async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    save_data({"users": {}, "joined_ids": [], "left_users": []})
    await update.message.reply_text("✅ Giveaway has been reset. All data cleared.")

# ============ /export (ADMIN) ============
async def export_csv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    data = load_data()
    if not data["users"]:
        await update.message.reply_text("❌ No data to export!")
        return

    sorted_users = sorted(data["users"].items(), key=lambda x: x[1]["invited_count"], reverse=True)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Rank", "Name", "Username", "UserID", "Invite Link", "Total Invites"])

    for rank, (uid, udata) in enumerate(sorted_users, 1):
        writer.writerow([rank, udata["name"], f"@{udata['username']}", uid, udata["invite_link"], udata["invited_count"]])

    output.seek(0)
    bio = io.BytesIO(output.getvalue().encode("utf-8"))
    bio.name = "chaos_giveaway_results.csv"

    await update.message.reply_document(document=bio, filename="chaos_giveaway_results.csv", caption="📊 CHAOS INDIA Giveaway — Full Results")

MESSAGE_FILE = "saved_message.txt"

def load_saved_message():
    if os.path.exists(MESSAGE_FILE):
        with open(MESSAGE_FILE, "r", encoding="utf-8") as f:
            return f.read()
    return None

def save_message_file(text):
    with open(MESSAGE_FILE, "w", encoding="utf-8") as f:
        f.write(text)

# ============ /setmessage (ADMIN) ============
async def set_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    # Get raw text after /setmessage command — preserves newlines
    full_text = update.message.text
    # Remove the command part
    if "\n" in full_text:
        message = full_text.split("\n", 1)[1] if full_text.startswith("/setmessage\n") else full_text[len("/setmessage"):].strip()
    else:
        message = full_text[len("/setmessage"):].strip()

    if not message:
        current = load_saved_message()
        if current:
            await update.message.reply_text(
                f"📝 *Current saved message:*\n\n{current}\n\n_To update: send your new message on the next line after /setmessage_",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                "❌ No message saved yet.\n\n"
                "Send your message like this:\n"
                "`/setmessage`\n"
                "Your message here\n"
                "With all formatting and spaces",
                parse_mode="Markdown"
            )
        return

    save_message_file(message)
    await update.message.reply_text(
        f"✅ *Message saved!*\n\nNow use:\n`/post 🎯 Join Giveaway | 👑 Leaderboard`\n\nto post it to the channel with buttons.",
        parse_mode="Markdown"
    )

# ============ /post (ADMIN) ============
async def post_giveaway(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    saved_msg = load_saved_message()
    bot_username = (await context.bot.get_me()).username
    channel = load_channel()

    if not context.args:
        if not saved_msg:
            await update.message.reply_text(
                "❌ No saved message!\n\n"
                "First save your message:\n"
                "`/setmessage`\n"
                "Your message here...\n\n"
                "Then use:\n"
                "`/post 🎯 Join | 👑 Leaderboard`",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                "❌ *Buttons missing!*\n\n"
                "Usage:\n`/post Button1`\nor\n`/post Button1 | Button2`",
                parse_mode="Markdown"
            )
        return

    full_args = " ".join(context.args)
    parts = [p.strip() for p in full_args.split("|")]

    if len(parts) == 1:
        btn1_name = parts[0]
        keyboard = [[InlineKeyboardButton(btn1_name, url=f"https://t.me/{bot_username}?start=giveaway")]]
    else:
        btn1_name = parts[0]
        btn2_name = parts[1]
        keyboard = [[
            InlineKeyboardButton(btn1_name, url=f"https://t.me/{bot_username}?start=giveaway"),
            InlineKeyboardButton(btn2_name, url=f"https://t.me/{bot_username}?start=leaderboard")
        ]]

    if not saved_msg:
        await update.message.reply_text("❌ No saved message! Use `/setmessage` first.", parse_mode="Markdown")
        return

    try:
        await context.bot.send_message(
            chat_id=channel,
            text=saved_msg,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        await update.message.reply_text(f"✅ Post sent to {channel} with buttons!")
    except Exception as e:
        try:
            await context.bot.send_message(
                chat_id=channel,
                text=saved_msg,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            await update.message.reply_text(f"✅ Post sent to {channel}!")
        except Exception as e2:
            await update.message.reply_text(f"❌ Error: {e2}")

# ============ /addadmin (OWNER ONLY) ============
async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("❌ Only the owner can add admins.")
        return

    if not context.args:
        await update.message.reply_text("Usage: `/addadmin userID`", parse_mode="Markdown")
        return

    try:
        new_admin_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Please provide a valid numeric User ID.")
        return

    admins = load_admins()
    if new_admin_id in admins:
        await update.message.reply_text("⚠️ This user is already an admin.")
        return

    admins.append(new_admin_id)
    save_admins(admins)
    await update.message.reply_text(
        f"✅ *Admin Added!*\n\n🆔 `{new_admin_id}` now has admin access.",
        parse_mode="Markdown"
    )

# ============ /removeadmin (OWNER ONLY) ============
async def remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("❌ Only the owner can remove admins.")
        return

    if not context.args:
        await update.message.reply_text("Usage: `/removeadmin userID`", parse_mode="Markdown")
        return

    try:
        admin_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Please provide a valid numeric User ID.")
        return

    admins = load_admins()
    if admin_id not in admins:
        await update.message.reply_text("❌ This user is not an admin.")
        return

    admins.remove(admin_id)
    save_admins(admins)
    await update.message.reply_text(f"🚫 *Admin Removed!*\n\n🆔 `{admin_id}` no longer has admin access.", parse_mode="Markdown")

# ============ /admins (OWNER ONLY) ============
async def list_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return

    admins = load_admins()
    if not admins:
        await update.message.reply_text("📋 No admins added yet.\n\nUse `/addadmin userID`", parse_mode="Markdown")
        return

    text = "👮 *Current Bot Admins*\n\n"
    for i, aid in enumerate(admins, 1):
        text += f"`{i}.` `{aid}`\n"
    text += f"\n_Total: {len(admins)} admin(s)_"
    await update.message.reply_text(text, parse_mode="Markdown")

# ============ MAIN ============
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("leave", leave))
    app.add_handler(CommandHandler("mystats", mystats))
    app.add_handler(CommandHandler("leaderboard", leaderboard))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("leavelog", leave_log))
    app.add_handler(CommandHandler("check", check_user))
    app.add_handler(CommandHandler("kick", kick_user))
    app.add_handler(CommandHandler("winner", winner))
    app.add_handler(CommandHandler("announce", announce))
    app.add_handler(CommandHandler("setchannel", set_channel))
    app.add_handler(CommandHandler("removechannel", remove_channel))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("export", export_csv))
    app.add_handler(CommandHandler("setmessage", set_message))
    app.add_handler(CommandHandler("post", post_giveaway))
    app.add_handler(CommandHandler("addadmin", add_admin))
    app.add_handler(CommandHandler("removeadmin", remove_admin))
    app.add_handler(CommandHandler("admins", list_admins))

    app.add_handler(CallbackQueryHandler(mystats_callback, pattern="^mystats$"))
    app.add_handler(CallbackQueryHandler(leaderboard_callback, pattern="^leaderboard$"))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, track_new_member))

    logger.info("🚀 Chaos Giveaway Bot started!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
