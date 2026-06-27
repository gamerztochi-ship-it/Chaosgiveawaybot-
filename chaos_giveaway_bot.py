import logging
import csv
import io
import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)

# ============ CONFIG ============
BOT_TOKEN = "8649968862:AAFbV0IOW72JQpI7L_16d1GuMa7a4CtPrRM"
OWNER_ID = 6730329053
CHANNEL_USERNAME = "@CHAOSINDIA"
DATA_FILE = "giveaway_data.json"
ADMINS_FILE = "admins.json"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============ DATA MANAGEMENT ============
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"users": {}, "joined_ids": []}

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

    args = context.args
    if args and args[0] == "giveaway":
        if user_id not in data["users"]:
            try:
                link_obj = await context.bot.create_chat_invite_link(
                    chat_id=CHANNEL_USERNAME,
                    name=f"ref_{user_id}",
                    creates_join_request=False
                )
                invite_link = link_obj.invite_link
            except Exception as e:
                logger.error(f"Link create error: {e}")
                invite_link = "https://t.me/CHAOSINDIA"

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

        # If this user EVER joined before (even after leaving), skip permanently
        if new_id in data.get("joined_ids", []):
            continue

        # First time joining — mark permanently, no second chances
        data["joined_ids"].append(new_id)

        invite_link_used = None
        if update.message.invite_link:
            invite_link_used = update.message.invite_link.invite_link

        if invite_link_used:
            for uid, udata in data["users"].items():
                if udata["invite_link"] == invite_link_used:
                    # Don't count self-invites
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
        await update.message.reply_text(
            "❌ You are not registered in the giveaway!\n\nUse /start to join."
        )
        return

    sorted_users = sorted(data["users"].values(), key=lambda x: x["invited_count"], reverse=True)
    rank = next((i+1 for i, u in enumerate(sorted_users) if u["invite_link"] == entry["invite_link"]), "N/A")

    text = (
        f"📊 *Your Giveaway Stats*\n\n"
        f"👤 Name: {entry['name']}\n"
        f"🔗 Your Invite Link: `{entry['invite_link']}`\n"
        f"👥 Total Invites: `{entry['invited_count']}`\n"
        f"🏆 Current Rank: `#{rank}`\n\n"
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
        await query.message.reply_text("❌ You are not registered! Use /start to join the giveaway.")
        return

    sorted_users = sorted(data["users"].values(), key=lambda x: x["invited_count"], reverse=True)
    rank = next((i+1 for i, u in enumerate(sorted_users) if u["invite_link"] == entry["invite_link"]), "N/A")

    text = (
        f"📊 *Your Giveaway Stats*\n\n"
        f"👤 Name: {entry['name']}\n"
        f"🔗 Your Invite Link: `{entry['invite_link']}`\n"
        f"👥 Total Invites: `{entry['invited_count']}`\n"
        f"🏆 Current Rank: `#{rank}`\n\n"
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
    text = "👑 *CHAOS INDIA 2K GIVEAWAY — TOP 10*\n\n"
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
    text = "👑 *CHAOS INDIA 2K GIVEAWAY — TOP 10*\n\n"
    for i, u in enumerate(sorted_users):
        name = u["name"][:20]
        text += f"{medals[i]} `#{i+1}` *{name}* — `{u['invited_count']} invites`\n"

    text += "\n_Share your link and climb the ranks!_ 🔥"
    await query.message.reply_text(text, parse_mode="Markdown")

# ============ /check (OWNER ONLY) ============
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
        await update.message.reply_text("❌ User not found. Check the username or ID.")
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

# ============ /winner (OWNER ONLY) ============
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

# ============ /leave (USER) ============
async def leave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()

    if user_id not in data["users"]:
        await update.message.reply_text("❌ You are not registered in the giveaway.")
        return

    del data["users"][user_id]
    save_data(data)
    await update.message.reply_text(
        "✅ You have been successfully removed from the giveaway.\n\n"
        "Your invite link is now inactive and your data has been deleted.\n\n"
        "_You can rejoin anytime using /start._",
        parse_mode="Markdown"
    )

# ============ /kick (OWNER ONLY) ============
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
    save_data(data)

    await update.message.reply_text(
        f"🚫 *User Removed from Giveaway*\n\n"
        f"👤 Name: {removed['name']}\n"
        f"📛 Username: @{removed['username']}\n"
        f"🆔 ID: `{found_uid}`\n"
        f"👥 Had Invites: `{removed['invited_count']}`\n\n"
        f"Their link is now invalid.",
        parse_mode="Markdown"
    )

# ============ /reset (OWNER ONLY) ============
async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    save_data({"users": {}, "joined_ids": []})
    await update.message.reply_text("✅ Giveaway has been reset. All data cleared.")

# ============ /export (OWNER ONLY) ============
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
        writer.writerow([
            rank,
            udata["name"],
            f"@{udata['username']}",
            uid,
            udata["invite_link"],
            udata["invited_count"]
        ])

    output.seek(0)
    bio = io.BytesIO(output.getvalue().encode("utf-8"))
    bio.name = "chaos_giveaway_results.csv"

    await update.message.reply_document(
        document=bio,
        filename="chaos_giveaway_results.csv",
        caption="📊 CHAOS INDIA Giveaway — Full Results"
    )

# ============ /post (OWNER ONLY) ============
async def post_giveaway(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    bot_username = (await context.bot.get_me()).username

    text = (
        "🎉 *CHAOS INDIA 🇮🇳 — Members Giveaway is LIVE!* 🎉\n\n"
        "We're celebrating our community and YOU can win by inviting your friends!\n\n"
        "🎯 *Target:* 2,000 Members\n\n"
        "🏆 *Prizes:*\n"
        "🥇 1st Place — ₹400\n"
        "🥈 2nd Place — ₹300\n"
        "🥉 3rd Place — ₹200\n"
        "🎖 4th Place — Admin in Group Chat\n\n"
        "📌 *Rules:*\n"
        "• Invite the highest number of real members\n"
        "• Fake accounts or bot invites = instant disqualification & ban\n"
        "• Leaderboard will be checked at the end of the event\n"
        "• Only invites via your unique bot link will be counted\n\n"
        "⏳ *Duration:* 5 Days\n"
        "👥 *Current Members:* 970\n\n"
        "The more people you invite, the higher your chances of winning!\n\n"
        "🚀 *Press the button below to get your unique invite link and start now!*"
    )

    keyboard = [
        [
            InlineKeyboardButton("🎯 Join Giveaway", url=f"https://t.me/{bot_username}?start=giveaway"),
            InlineKeyboardButton("👑 Leaderboard", url=f"https://t.me/{bot_username}?start=leaderboard")
        ]
    ]

    await context.bot.send_message(
        chat_id=CHANNEL_USERNAME,
        text=text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await update.message.reply_text("✅ Giveaway post sent to channel!")

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
        f"✅ *Admin Added!*\n\n🆔 User ID: `{new_admin_id}` now has admin access.\n\n"
        f"They can use: /check, /kick, /winner, /export, /reset, /post",
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
    await update.message.reply_text(
        f"🚫 *Admin Removed!*\n\n🆔 User ID: `{admin_id}` no longer has admin access.",
        parse_mode="Markdown"
    )

# ============ /admins (OWNER ONLY) ============
async def list_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return

    admins = load_admins()
    if not admins:
        await update.message.reply_text("📋 No admins added yet.\n\nUse `/addadmin userID` to add one.", parse_mode="Markdown")
        return

    text = "👮 *Current Bot Admins*\n\n"
    for i, aid in enumerate(admins, 1):
        text += f"`{i}.` `{aid}`\n"
    text += f"\n_Total: {len(admins)} admin(s)_\n\nUse `/removeadmin userID` to remove."

    await update.message.reply_text(text, parse_mode="Markdown")

# ============ MAIN ============
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("leave", leave))
    app.add_handler(CommandHandler("mystats", mystats))
    app.add_handler(CommandHandler("leaderboard", leaderboard))
    app.add_handler(CommandHandler("addadmin", add_admin))
    app.add_handler(CommandHandler("removeadmin", remove_admin))
    app.add_handler(CommandHandler("admins", list_admins))
    app.add_handler(CommandHandler("check", check_user))
    app.add_handler(CommandHandler("kick", kick_user))
    app.add_handler(CommandHandler("winner", winner))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("export", export_csv))
    app.add_handler(CommandHandler("post", post_giveaway))

    app.add_handler(CallbackQueryHandler(mystats_callback, pattern="^mystats$"))
    app.add_handler(CallbackQueryHandler(leaderboard_callback, pattern="^leaderboard$"))

    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, track_new_member))

    logger.info("🚀 Chaos Giveaway Bot started!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

