from config import CHANNEL_ID2
from Extractor.core import script
from pyrogram.errors import UserNotParticipant
from pyrogram.types import *
from Extractor.core.mongo.plans_db import premium_users


# Check if user is premium
async def chk_user(query, user_id):
    user = await premium_users()
    if user_id in user:
        await query.answer("✅ Premium User!")
        return 0
    else:
        await query.answer("❌ Sir, you don't have premium access!", show_alert=True)
        return 1


# Generate invite link (admin approval join request)
async def gen_link(app, chat_id):
    try:
        link = await app.create_chat_invite_link(
            chat_id=chat_id,
            name="Join Request Link",
            creates_join_request=True
        )
        return link.invite_link
    except Exception as e:
        print(f"Failed to create invite link: {e}")
        return None


# Force subscription check
async def subscribe(app, message):
    try:
        update_channel = CHANNEL_ID2
        if not update_channel:
            return 0  # No channel set, skip checking

        try:
            user = await app.get_chat_member(update_channel, message.from_user.id)
            if user.status == "kicked":
                await message.reply_text("🚫 Sorry Sir, You are Banned. Contact My Support Group @DevsOops")
                return 1
        except UserNotParticipant:
            try:
                url = await gen_link(app, update_channel)
                if url:
                    await message.reply_photo(
                        photo="https://pbs.twimg.com/media/EQY3-X8WoAAUWg4.png",
                        caption=script.FORCE_MSG.format(message.from_user.mention),
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton("🤖 ɴᴇᴇᴅ ᴀᴘᴘʀᴏᴠᴀʟ ᴛᴏ ᴊᴏɪɴ 🤖", url=url)
                        ]])
                    )
                else:
                    raise Exception("Invite link is None")
            except Exception as e:
                print(f"Link generation failed: {e}")
                await message.reply_text(
                    "❗ Please join our updates channel to use the bot.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🤖 ᴊᴏɪɴ ᴜᴘᴅᴀᴛᴇs ᴄʜᴀɴɴᴇʟ 🤖", url="https://t.me/UGxPro")
                    ]])
                )
            return 1
        except Exception as e:
            print(f"Error in subscribe inner: {e}")
            return 0  # Allow user to continue if error

        return 0  # Already a member
    except Exception as e:
        print(f"Error in subscribe outer: {e}")
        return 0


# Convert string time to seconds
async def get_seconds(time_string):
    def extract_value_and_unit(ts):
        value = ""
        index = 0
        while index < len(ts) and ts[index].isdigit():
            value += ts[index]
            index += 1
        unit = ts[index:].strip()
        return int(value) if value else 0, unit

    value, unit = extract_value_and_unit(time_string)

    if unit == 's':
        return value
    elif unit == 'min':
        return value * 60
    elif unit == 'hour':
        return value * 3600
    elif unit == 'day':
        return value * 86400
    elif unit == 'month':
        return value * 86400 * 30
    elif unit == 'year':
        return value * 86400 * 365
    else:
        return 0
