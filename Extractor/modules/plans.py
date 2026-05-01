from datetime import timedelta
import pytz
import datetime
from Extractor import app
from config import PREMIUM_LOGS, OWNER_ID
from Extractor.core.func import get_seconds
from Extractor.core.mongo import plans_db  
from pyrogram import filters 
from pyrogram.errors import MessageTooLong
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from Extractor.core.script import (
    PLANS_TXT,
    FREE_TXT,
    BRONZE_TXT,
    SILVER_TXT,
    GOLD_TXT,
    OTHER_TXT,
    PAYMENT_TXT
)

IST = pytz.timezone("Asia/Kolkata")


# ---------------- REMOVE PREMIUM ---------------- #
@app.on_message(filters.command("remove_premium"))
async def remove_premium(client, message):
    try:
        if len(message.command) != 2:
            return await message.reply_text("Usage : /remove_premium user_id")

        user_id = int(message.command[1])

        try:
            user = await client.get_users(user_id)
            mention = user.mention
        except:
            mention = f"<code>{user_id}</code>"

        data = await plans_db.check_premium(user_id)

        if data:
            await plans_db.remove_premium(user_id)

            await message.reply_text("✅ User premium removed successfully!")

            await client.send_message(
                chat_id=user_id,
                text=f"👋 Hey {mention},\n\nYour premium has been removed."
            )
        else:
            await message.reply_text("❌ User not found in premium database!")

    except Exception as e:
        print("REMOVE ERROR:", e)


# ---------------- MY PLAN ---------------- #
@app.on_message(filters.command("myplan"))
async def myplan(client, message):
    try:
        user_id = message.from_user.id
        user = message.from_user.mention

        data = await plans_db.check_premium(user_id)

        if data and data.get("expire_date"):
            expiry = data.get("expire_date")

            if expiry.tzinfo is None:
                expiry = IST.localize(expiry)

            expiry_ist = expiry.astimezone(IST)

            expiry_str = expiry_ist.strftime("%d-%m-%Y | %I:%M %p")

            now = datetime.datetime.now(IST)
            time_left = expiry_ist - now

            days = time_left.days
            hours, rem = divmod(time_left.seconds, 3600)
            minutes, _ = divmod(rem, 60)

            await message.reply_text(
                f"👤 {user}\n"
                f"🆔 <code>{user_id}</code>\n"
                f"⏳ {days}d {hours}h {minutes}m left\n"
                f"📅 Expiry: {expiry_str}"
            )
        else:
            await message.reply_text("❌ No active premium found!")

    except Exception as e:
        print("MYPLAN ERROR:", e)


# ---------------- CHECK PREMIUM ---------------- #
@app.on_message(filters.command("chk_premium"))
async def chk_premium(client, message):
    try:
        if len(message.command) != 2:
            return await message.reply_text("Usage: /chk_premium user_id")

        try:
            user_id = int(message.command[1])
        except:
            return await message.reply_text("Invalid user id ❌")

        try:
            user = await client.get_users(user_id)
            mention = user.mention
        except:
            mention = f"<code>{user_id}</code>"

        data = await plans_db.check_premium(user_id)

        if data and data.get("expire_date"):
            expiry = data.get("expire_date")

            if expiry.tzinfo is None:
                expiry = IST.localize(expiry)

            expiry_ist = expiry.astimezone(IST)
            expiry_str = expiry_ist.strftime("%d-%m-%Y | %I:%M %p")

            now = datetime.datetime.now(IST)
            time_left = expiry_ist - now

            days = time_left.days
            hours, rem = divmod(time_left.seconds, 3600)
            minutes, _ = divmod(rem, 60)

            await message.reply_text(
                f"👤 {mention}\n"
                f"🆔 <code>{user_id}</code>\n"
                f"⏳ {days}d {hours}h {minutes}m\n"
                f"📅 Expiry: {expiry_str}"
            )
        else:
            await message.reply_text("❌ No premium found!")

    except Exception as e:
        print("CHK ERROR:", e)


# ---------------- PLANS UI ---------------- #
@app.on_message(filters.command("plans"))
async def plans(client, message):

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 Free", callback_data="free")],
        [InlineKeyboardButton("🥉 Bronze", callback_data="bronze"),
         InlineKeyboardButton("🥈 Silver", callback_data="silver")],
        [InlineKeyboardButton("🥇 Gold", callback_data="gold")],
        [InlineKeyboardButton("💳 Payment", callback_data="payment")]
    ])

    await message.reply_text(
        PLANS_TXT,
        reply_markup=buttons,
        disable_web_page_preview=True
    )


# ---------------- CALLBACK ---------------- #
@app.on_callback_query(filters.regex("^(free|bronze|silver|gold|payment|back)$"))
async def cb_handler(client, query):

    back = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back")]])

    if query.data == "free":
        await query.message.edit_text(FREE_TXT, reply_markup=back)

    elif query.data == "bronze":
        await query.message.edit_text(BRONZE_TXT, reply_markup=back)

    elif query.data == "silver":
        await query.message.edit_text(SILVER_TXT, reply_markup=back)

    elif query.data == "gold":
        await query.message.edit_text(GOLD_TXT, reply_markup=back)

    elif query.data == "payment":
        await query.message.edit_text(PAYMENT_TXT, reply_markup=back, disable_web_page_preview=True)

    elif query.data == "back":
        await plans(client, query.message)


# ---------------- ADD PREMIUM ---------------- #
@app.on_message(filters.command("add_premium") & filters.user(OWNER_ID))
async def add_premium(client, message):
    try:
        if len(message.command) != 4:
            return await message.reply_text("Usage: /add_premium user_id 1 day")

        user_id = int(message.command[1])
        time_str = f"{message.command[2]} {message.command[3]}"

        seconds = await get_seconds(time_str)

        if seconds <= 0:
            return await message.reply_text("Invalid time ❌")

        expiry = datetime.datetime.now(IST) + datetime.timedelta(seconds=seconds)

        await plans_db.add_premium(user_id, expiry)

        await message.reply_text(f"✅ Premium added for {user_id}")

    except Exception as e:
        print("ADD ERROR:", e)


# ---------------- PREMIUM USERS ---------------- #
@app.on_message(filters.command("premium_users") & filters.user(OWNER_ID))
async def premium_users(client, message):
    try:
        text = "⚜️ Premium Users:\n\n"
        count = 1

        users = await plans_db.get_all_premium_users()

        async for user in users:
            expiry = user.get("expire_date")

            if expiry.tzinfo is None:
                expiry = IST.localize(expiry)

            expiry = expiry.astimezone(IST)

            text += f"{count}. <code>{user['_id']}</code>\n📅 {expiry.strftime('%d-%m-%Y')}\n\n"
            count += 1

        try:
            await message.reply_text(text)
        except MessageTooLong:
            with open("users.txt", "w") as f:
                f.write(text)
            await message.reply_document("users.txt")

    except Exception as e:
        print("LIST ERROR:", e)
