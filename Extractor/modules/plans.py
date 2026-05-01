from datetime import timedelta
import pytz
import datetime, time
from Extractor import app
from config import  PREMIUM_LOGS, OWNER_ID
from Extractor.core.func import get_seconds
from Extractor.core.mongo import plans_db  
from pyrogram import filters 
from pyrogram.errors.exceptions.bad_request_400 import MessageTooLong
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton


@app.on_message(filters.command("remove_premium") )
async def remove_premium(client, message):
    if len(message.command) == 2:
        user_id = int(message.command[1])  
        user = await client.get_users(user_id)
        data = await plans_db.check_premium(user_id)  
        
        if data and data.get("_id"):
            await plans_db.remove_premium(user_id)
            await message.reply_text("ᴜꜱᴇʀ ʀᴇᴍᴏᴠᴇᴅ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ !")
            await client.send_message(
                chat_id=user_id,
                text=f"<b>ʜᴇʏ {user.mention},\n\nʏᴏᴜʀ ᴘʀᴇᴍɪᴜᴍ ᴀᴄᴄᴇss ʜᴀs ʙᴇᴇɴ ʀᴇᴍᴏᴠᴇᴅ.\nᴛʜᴀɴᴋ ʏᴏᴜ ꜰᴏʀ ᴜsɪɴɢ ᴏᴜʀ sᴇʀᴠɪᴄᴇ 😊.</b>"
            )
        else:
            await message.reply_text("ᴜɴᴀʙʟᴇ ᴛᴏ ʀᴇᴍᴏᴠᴇ ᴜꜱᴇᴅ !\nᴀʀᴇ ʏᴏᴜ ꜱᴜʀᴇ, ɪᴛ ᴡᴀꜱ ᴀ ᴘʀᴇᴍɪᴜᴍ ᴜꜱᴇʀ ɪᴅ ?")
    else:
        await message.reply_text("ᴜꜱᴀɢᴇ : /remove_premium user_id") 



@app.on_message(filters.command("myplan"))
async def myplan(client, message):
    try:
        user_id = message.from_user.id
        user = message.from_user.mention

        data = await plans_db.check_premium(user_id)

        if data and data.get("expire_date"):
            expiry = data.get("expire_date")

            if expiry.tzinfo is None:
                expiry = pytz.timezone("Asia/Kolkata").localize(expiry)

            expiry_ist = expiry.astimezone(pytz.timezone("Asia/Kolkata"))

            expiry_str_in_ist = expiry_ist.strftime(
                "%d-%m-%Y\n⏱️ ᴇxᴘɪʀʏ ᴛɪᴍᴇ : %I:%M:%S %p"
            )

            current_time = datetime.datetime.now(pytz.timezone("Asia/Kolkata"))
            time_left = expiry_ist - current_time

            days = time_left.days
            hours, remainder = divmod(time_left.seconds, 3600)
            minutes, _ = divmod(remainder, 60)

            time_left_str = f"{days} ᴅᴀʏꜱ, {hours} ʜᴏᴜʀꜱ, {minutes} ᴍɪɴᴜᴛᴇꜱ"

            await message.reply_text(
                f"⚜️ ᴘʀᴇᴍɪᴜᴍ ᴜꜱᴇʀ ᴅᴀᴛᴀ :\n\n"
                f"👤 ᴜꜱᴇʀ : {user}\n"
                f"⚡ ᴜꜱᴇʀ ɪᴅ : <code>{user_id}</code>\n"
                f"⏰ ᴛɪᴍᴇ ʟᴇꜰᴛ : {time_left_str}\n"
                f"⌛️ ᴇxᴘɪʀʏ ᴅᴀᴛᴇ : {expiry_str_in_ist}"
            )
        else:
            await message.reply_text(
                f"ʜᴇʏ {user},\n\nʏᴏᴜ ᴅᴏ ɴᴏᴛ ʜᴀᴠᴇ ᴀɴʏ ᴀᴄᴛɪᴠᴇ ᴘʀᴇᴍɪᴜᴍ ᴘʟᴀɴs"
            )

    except Exception as e:
        print("Error:", e)
        await message.reply_text("Something went wrong 😅")

@app.on_message(filters.command("chk_premium"))
async def get_premium(client, message):
    try:
        if len(message.command) == 2:

            try:
                user_id = int(message.command[1])
            except:
                return await message.reply_text("Invalid user id ❌")

            # safe user fetch
            try:
                user = await client.get_users(user_id)
                user_mention = user.mention
            except:
                user_mention = f"<code>{user_id}</code>"

            data = await plans_db.check_premium(user_id)

            if data and data.get("expire_date"):
                expiry = data.get("expire_date")

                # FIX timezone
                if expiry.tzinfo is None:
                    expiry = pytz.timezone("Asia/Kolkata").localize(expiry)

                expiry_ist = expiry.astimezone(pytz.timezone("Asia/Kolkata"))

                expiry_str_in_ist = expiry_ist.strftime(
                    "%d-%m-%Y\n⏱️ ᴇxᴘɪʀʏ ᴛɪᴍᴇ : %I:%M:%S %p"
                )

                current_time = datetime.datetime.now(pytz.timezone("Asia/Kolkata"))
                time_left = expiry_ist - current_time

                days = time_left.days
                hours, remainder = divmod(time_left.seconds, 3600)
                minutes, _ = divmod(remainder, 60)

                time_left_str = f"{days} days, {hours} hours, {minutes} minutes"

                await message.reply_text(
                    f"⚜️ ᴘʀᴇᴍɪᴜᴍ ᴜꜱᴇʀ ᴅᴀᴛᴀ :\n\n"
                    f"👤 ᴜꜱᴇʀ : {user_mention}\n"
                    f"⚡ ᴜꜱᴇʀ ɪᴅ : <code>{user_id}</code>\n"
                    f"⏰ ᴛɪᴍᴇ ʟᴇꜰᴛ : {time_left_str}\n"
                    f"⌛️ ᴇxᴘɪʀʏ ᴅᴀᴛᴇ : {expiry_str_in_ist}"
                )

            else:
                await message.reply_text(
                    "ɴᴏ ᴀɴʏ ᴘʀᴇᴍɪᴜᴍ ᴅᴀᴛᴀ ꜰᴏᴜɴᴅ ❌"
                )

        else:
            await message.reply_text("Usage: /chk_premium user_id")

    except Exception as e:
        print("ERROR:", e)
        await message.reply_text("Error aa gaya 😅")


# MAIN COMMAND
@app.on_message(filters.command("plans"))
async def plans(client, message):

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 Free Trial", callback_data="free")],
        [InlineKeyboardButton("🥉 Bronze", callback_data="bronze"),
         InlineKeyboardButton("🥈 Silver", callback_data="silver")],
        [InlineKeyboardButton("🥇 Gold", callback_data="gold")],
        [InlineKeyboardButton("🎯 Other Plan", callback_data="other")],
        [InlineKeyboardButton("💳 Payment", callback_data="payment")]
    ])

    await message.reply_text(
        PLANS_TXT,
        reply_markup=buttons,
        disable_web_page_preview=True
    )

@app.on_callback_query()
async def cb_handler(client, query):

    data = query.data

    back_btn = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="back")]
    ])

    if data == "free":
        await query.message.edit_text(FREE_TXT, reply_markup=back_btn)

    elif data == "bronze":
        await query.message.edit_text(BRONZE_TXT, reply_markup=back_btn)

    elif data == "silver":
        await query.message.edit_text(SILVER_TXT, reply_markup=back_btn)

    elif data == "gold":
        await query.message.edit_text(GOLD_TXT, reply_markup=back_btn)

    elif data == "other":
        await query.message.edit_text(OTHER_TXT, reply_markup=back_btn)

    elif data == "payment":
        await query.message.edit_text(PAYMENT_TXT, reply_markup=back_btn, disable_web_page_preview=True)

    elif data == "back":
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎁 Free Trial", callback_data="free")],
            [InlineKeyboardButton("🥉 Bronze", callback_data="bronze"),
             InlineKeyboardButton("🥈 Silver", callback_data="silver")],
            [InlineKeyboardButton("🥇 Gold", callback_data="gold")],
            [InlineKeyboardButton("🎯 Other Plan", callback_data="other")],
            [InlineKeyboardButton("💳 Payment", callback_data="payment")]
        ])

        await query.message.edit_text(
            PLANS_TXT,
            reply_markup=buttons,
            disable_web_page_preview=True
        )
@app.on_message(filters.command("add_premium"))
async def give_premium_cmd_handler(client, message):
    if len(message.command) == 4:
        time_zone = datetime.datetime.now(pytz.timezone("Asia/Kolkata"))
        current_time = time_zone.strftime("%d-%m-%Y\n⏱️ ᴊᴏɪɴɪɴɢ ᴛɪᴍᴇ : %I:%M:%S %p") 
        user_id = int(message.command[1])
        user = await client.get_users(user_id)
        time = message.command[2]+" "+message.command[3]
        seconds = await get_seconds(time)
        if seconds > 0:
            expiry_time = datetime.datetime.now() + datetime.timedelta(seconds=seconds)  
            await plans_db.add_premium(user_id, expiry_time)  
            data = await plans_db.check_premium(user_id)
            expiry = data.get("expire_date")   
            expiry_str_in_ist = expiry.astimezone(pytz.timezone("Asia/Kolkata")).strftime("%d-%m-%Y\n⏱️ ᴇxᴘɪʀʏ ᴛɪᴍᴇ : %I:%M:%S %p")         
            await message.reply_text(f"ᴘʀᴇᴍɪᴜᴍ ᴀᴅᴅᴇᴅ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ✅\n\n👤 ᴜꜱᴇʀ : {user.mention}\n⚡ ᴜꜱᴇʀ ɪᴅ : <code>{user_id}</code>\n⏰ ᴘʀᴇᴍɪᴜᴍ ᴀᴄᴄᴇꜱꜱ : <code>{time}</code>\n\n⏳ ᴊᴏɪɴɪɴɢ ᴅᴀᴛᴇ : {current_time}\n\n⌛️ ᴇxᴘɪʀʏ ᴅᴀᴛᴇ : {expiry_str_in_ist}", disable_web_page_preview=True)
            await client.send_message(
                chat_id=user_id,
                text=f"👋 ʜᴇʏ {user.mention},\nᴛʜᴀɴᴋ ʏᴏᴜ ꜰᴏʀ ᴘᴜʀᴄʜᴀꜱɪɴɢ ᴘʀᴇᴍɪᴜᴍ.\nᴇɴᴊᴏʏ !! ✨🎉\n\n⏰ ᴘʀᴇᴍɪᴜᴍ ᴀᴄᴄᴇꜱꜱ : <code>{time}</code>\n⏳ ᴊᴏɪɴɪɴɢ ᴅᴀᴛᴇ : {current_time}\n\n⌛️ ᴇxᴘɪʀʏ ᴅᴀᴛᴇ : {expiry_str_in_ist}", disable_web_page_preview=True              
            )    
            await client.send_message(PREMIUM_LOGS, text=f"#Added_Premium\n\n👤 ᴜꜱᴇʀ : {user.mention}\n⚡ ᴜꜱᴇʀ ɪᴅ : <code>{user_id}</code>\n⏰ ᴘʀᴇᴍɪᴜᴍ ᴀᴄᴄᴇꜱꜱ : <code>{time}</code>\n\n⏳ ᴊᴏɪɴɪɴɢ ᴅᴀᴛᴇ : {current_time}\n\n⌛️ ᴇxᴘɪʀʏ ᴅᴀᴛᴇ : {expiry_str_in_ist}", disable_web_page_preview=True)
                    
        else:
            await message.reply_text("Invalid time format. Please use '1 day for days', '1 hour for hours', or '1 min for minutes', or '1 month for months' or '1 year for year'")
    else:
        await message.reply_text("Usage : /add_premium user_id time (e.g., '1 day for days', '1 hour for hours', or '1 min for minutes', or '1 month for months' or '1 year for year')")



@app.on_message(filters.command("premium_users"))
async def premium_user(client, message):
    aa = await message.reply_text("<i>ꜰᴇᴛᴄʜɪɴɢ...</i>")
    new = f"⚜️ ᴘʀᴇᴍɪᴜᴍ ᴜꜱᴇʀꜱ ʟɪꜱᴛ :\n\n"
    user_count = 1
    users = await db.get_all_users()
    async for user in users:
        data = await db.get_user(user['id'])
        if data and data.get("expiry_time"):
            expiry = data.get("expiry_time") 
            expiry_ist = expiry.astimezone(pytz.timezone("Asia/Kolkata"))
            expiry_str_in_ist = expiry.astimezone(pytz.timezone("Asia/Kolkata")).strftime("%d-%m-%Y\n⏱️ ᴇxᴘɪʀʏ ᴛɪᴍᴇ : %I:%M:%S %p")            
            current_time = datetime.datetime.now(pytz.timezone("Asia/Kolkata"))
            time_left = expiry_ist - current_time
            days = time_left.days
            hours, remainder = divmod(time_left.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            time_left_str = f"{days} days, {hours} hours, {minutes} minutes"	 
            new += f"{user_count}. {(await client.get_users(user['id'])).mention}\n👤 ᴜꜱᴇʀ ɪᴅ : {user['id']}\n⏳ ᴇxᴘɪʀʏ ᴅᴀᴛᴇ : {expiry_str_in_ist}\n⏰ ᴛɪᴍᴇ ʟᴇꜰᴛ : {time_left_str}\n"
            user_count += 1
        else:
            pass
    try:    
        await aa.edit_text(new)
    except MessageTooLong:
        with open('usersplan.txt', 'w+') as outfile:
            outfile.write(new)
        await message.reply_document('usersplan.txt', caption="Paid Users:")


