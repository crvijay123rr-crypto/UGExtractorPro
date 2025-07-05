import requests, os, sys, re
import json, asyncio
import subprocess
import datetime
import time
import logging
from typing import List, Dict, Tuple, Any
import aiohttp
from concurrent.futures import ThreadPoolExecutor
from Extractor import app
from config import *
import config
from pyrogram import Client, filters, idle
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
#from pyrogram.errors import ListenerTimeout
from subprocess import getstatusoutput
from datetime import datetime
import pytz
import gc
from datetime import datetime, timedelta


join = config.join
india_timezone = pytz.timezone('Asia/Kolkata')
current_time = datetime.now(india_timezone)
time_new = current_time.strftime("%d-%m-%Y %I:%M %p")

# Format time taken
def format_time_taken(start_time: float) -> str:
    end_time = time.time()
    time_taken = end_time - start_time
    formatted_time = str(timedelta(seconds=int(time_taken)))
    return formatted_time

# Reduce max workers to prevent memory overload
THREADPOOL = ThreadPoolExecutor(max_workers=2000)
CHUNK_SIZE = 8192

thumb = os.path.join(os.path.dirname(__file__), "logo.jpg")

async def download_thumbnail(session: aiohttp.ClientSession, url: str) -> str | None:
    try:
        thumb_path = f"thumb_{int(time.time())}.jpg"
        
        async with session.get(url, timeout=30) as response:
            if response.status == 200:
                with open(thumb_path, "wb") as f:
                    while True:
                        chunk = await response.content.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        f.write(chunk)
                return thumb_path
            else:
                logging.warning(f"Thumbnail download failed. Status: {response.status}")
                return None
    except Exception as e:
        logging.error(f"Error downloading thumbnail: {e}")
        return None
    finally:
        gc.collect()

def create_html_file(file_name, batch_name, contents):
    tbody = ''
    parts = contents.split('\n')
    
    # Process in chunks to reduce memory usage
    chunk_size = 100
    for i in range(0, len(parts), chunk_size):
        chunk = parts[i:i + chunk_size]
        for part in chunk:
            split_part = [item.strip() for item in part.split(':', 1)]
            text = split_part[0] if split_part[0] else 'Untitled'
            url = split_part[1].strip() if len(split_part) > 1 and split_part[1].strip() else 'No URL'
            tbody += f'<tr><td>{text}</td><td><a href="{url}" target="_blank">{url}</a></td></tr>'
        
        # Force garbage collection after each chunk
        gc.collect()

    with open('Extractor/core/template.html', 'r') as fp:
        file_content = fp.read()
    title = batch_name.strip()
    with open(file_name, 'w') as fp:
        fp.write(file_content.replace('{{tbody_content}}', tbody).replace('{{batch_name}}', title))

async def fetch_cpwp_signed_url(url_val: str, name: str, session: aiohttp.ClientSession, headers: Dict[str, str]) -> str:
    # Always return the original URL to ensure we get content
    return url_val

async def process_cpwp_url(url_val: str, name: str, folder_path: str, session: aiohttp.ClientSession, headers: Dict[str, str]) -> str | None:
    try:
        # No need to try signing, just use original URL
        if url_val:
            display_name = f"{folder_path}{name}" if folder_path else name
            return f"{display_name}:{url_val}\n"
        return None
    except Exception as e:
        logging.error(f"Error processing {name}: {e}")
        return None

async def get_cpwp_course_content(session: aiohttp.ClientSession, headers: Dict[str, str], Batch_Token: str, folder_id: int = 0, limit: int = 9999999999, retry_count: int = 0, folder_path: str = "") -> Tuple[List[str], int, int, int]:
    MAX_RETRIES = 3
    fetched_urls: set[str] = set()
    results: List[str] = []
    video_count = 0
    pdf_count = 0
    image_count = 0
    content_tasks: List[Tuple[int, asyncio.Task[str | None]]] = []
    folder_tasks: List[Tuple[int, asyncio.Task[Tuple[List[str], int, int, int]]]] = []

    try:
        content_api = f'https://api.classplusapp.com/v2/course/preview/content/list/{Batch_Token}'
        params = {'folderId': folder_id, 'limit': limit}

        async with session.get(content_api, params=params, headers=headers) as res:
            res.raise_for_status()
            res_json = await res.json()
            contents: List[Dict[str, Any]] = res_json['data']

            for content in contents:
                if content['contentType'] == 1:  # Folder
                    folder_name = content['name']
                    new_folder_path = f"{folder_path}({folder_name})" if folder_path else f"({folder_name})"
                    
                    folder_task = asyncio.create_task(
                        get_cpwp_course_content(session, headers, Batch_Token, content['id'], limit, 0, new_folder_path)
                    )
                    folder_tasks.append((content['id'], folder_task))

                else:  # File content
                    name: str = content['name']
                    url_val: str | None = content.get('url') or content.get('thumbnailUrl')

                    if not url_val:
                        continue

                    # Process URLs without signing
                    if "media-cdn.classplusapp.com/tencent/" in url_val:
                        url_val = url_val.rsplit('/', 1)[0] + "/master.m3u8"
                    elif "media-cdn.classplusapp.com" in url_val and url_val.endswith('.jpg'):
                        identifier = url_val.split('/')[-3]
                        url_val = f"https://media-cdn.classplusapp.com/alisg-cdn-a.classplusapp.com/{identifier}/master.m3u8"
                    elif "tencdn.classplusapp.com" in url_val and url_val.endswith('.jpg'):
                        identifier = url_val.split('/')[-2]
                        url_val = f"https://media-cdn.classplusapp.com/tencent/{identifier}/master.m3u8"
                    elif "4b06bf8d61c41f8310af9b2624459378203740932b456b07fcf817b737fbae27" in url_val and url_val.endswith('.jpeg'):
                        url_val = f"https://media-cdn.classplusapp.com/alisg-cdn-a.classplusapp.com/b08bad9ff8d969639b2e43d5769342cc62b510c4345d2f7f153bec53be84fe35/{url_val.split('/')[-1].split('.')[0]}/master.m3u8"
                    elif "cpvideocdn.testbook.com" in url_val and url_val.endswith('.png'):
                        match = re.search(r'/streams/([a-f0-9]{24})/', url_val)
                        video_id = match.group(1) if match else url_val.split('/')[-2]
                        url_val = f"https://cpvod.testbook.com/{video_id}/playlist.m3u8"
                    elif "media-cdn.classplusapp.com/drm/" in url_val and url_val.endswith('.png'):
                        video_id = url_val.split('/')[-3]
                        url_val = f"https://media-cdn.classplusapp.com/drm/{video_id}/playlist.m3u8"
                    elif "https://media-cdn.classplusapp.com" in url_val and ("cc/" in url_val or "lc/" in url_val or "uc/" in url_val or "dy/" in url_val) and url_val.endswith('.png'):
                        url_val = url_val.replace('thumbnail.png', 'master.m3u8')
                    elif "https://tb-video.classplusapp.com" in url_val and url_val.endswith('.jpg'):
                        video_id = url_val.split('/')[-1].split('.')[0]
                        url_val = f"https://tb-video.classplusapp.com/{video_id}/master.m3u8"

                    if url_val not in fetched_urls:
                        fetched_urls.add(url_val)
                        display_name = f"{folder_path}{name}" if folder_path else name
                        
                        if url_val.endswith(('.m3u8', '.mp4')):
                            video_count += 1
                        elif url_val.endswith('.pdf'):
                            pdf_count += 1
                        else:
                            image_count += 1
                            
                        results.append(f"{display_name}:{url_val}\n")

    except Exception as e:
        logging.exception(f"An unexpected error occurred: {e}")
        if retry_count < MAX_RETRIES:
            logging.info(f"Retrying folder {folder_id} (Attempt {retry_count + 1}/{MAX_RETRIES})")
            await asyncio.sleep(2 ** retry_count)
            return await get_cpwp_course_content(session, headers, Batch_Token, folder_id, limit, retry_count + 1, folder_path)
        else:
            logging.error(f"Failed to retrieve folder {folder_id} after {MAX_RETRIES} retries.")
            return [], 0, 0, 0

    # Process folder results
    for (folder_id, _), folder_result in zip(folder_tasks, await asyncio.gather(*(task for _, task in folder_tasks), return_exceptions=True)):
        try:
            if isinstance(folder_result, Exception):
                logging.error(f"Folder task failed with exception: {folder_result}")
                continue
                
            nested_results, nested_video_count, nested_pdf_count, nested_image_count = folder_result
            results.extend(nested_results)
            video_count += nested_video_count
            pdf_count += nested_pdf_count
            image_count += nested_image_count
        except Exception as e:
            logging.error(f"Error processing folder {folder_id}: {e}")

    return results, video_count, pdf_count, image_count


    
async def process_cpwp(bot: Client, m: Message, user_id: int):
    
    headers = {
        'accept-encoding': 'gzip',
        'accept-language': 'EN',
        'api-version'    : '35',
        'app-version'    : '1.4.73.2',
        'build-number'   : '35',
        'connection'     : 'Keep-Alive',
        'content-type'   : 'application/json',
        'device-details' : 'Xiaomi_Redmi 7_SDK-32',
        'device-id'      : 'c28d3cb16bbdac01',
        'host'           : 'api.classplusapp.com',
        'region'         : 'IN',
        'user-agent'     : 'Mobile-Android',
        'webengage-luid' : '00000187-6fe4-5d41-a530-26186858be4c'
    }

    loop = asyncio.get_event_loop()
    CONNECTOR = aiohttp.TCPConnector(limit=500, loop=loop)
    async with aiohttp.ClientSession(connector=CONNECTOR, loop=loop) as session:
        try:
            editable = await m.reply_text("🔑 **Sᴇɴᴅ ᴏʀɢ ᴄᴏᴅᴇ ᴏғ ʏᴏᴜʀ Cʟᴀssᴘʟᴜs ᴀᴘᴘ**")
            
            try:
                input1 = await bot.listen(chat_id=m.chat.id, filters=filters.user(user_id), timeout=120)
                org_code = input1.text.lower()
                await input1.delete(True)
            except asyncio.TimeoutError:
                await editable.edit("⏰ **Tɪᴍᴇᴏᴜᴛ!** Yᴏᴜ ᴛᴏᴏᴋ ᴛᴏᴏ ʟᴏɴɢ ᴛᴏ ʀᴇsᴘᴏɴᴅ")
                return
            except Exception as e:
                logging.exception("Error during input1 listening:")
                await editable.edit(f"❌ **Eʀʀᴏʀ:** {str(e)}")
                return

            hash_headers = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br, zstd',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://qsvfn.courses.store/?mainCategory=0&subCatList=[130504,62442]',
                'Sec-CH-UA': '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
                'Sec-CH-UA-Mobile': '?0',
                'Sec-CH-UA-Platform': '"Windows"',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'
            }
            
            async with session.get(f"https://{org_code}.courses.store", headers=hash_headers) as response:
                html_text = await response.text()
                hash_match = re.search(r'"hash":"(.*?)"', html_text)

                if hash_match:
                    token = hash_match.group(1)
                    
                    async with session.get(f"https://api.classplusapp.com/v2/course/preview/similar/{token}?limit=1000", headers=headers) as response:
                        if response.status == 200:
                            res_json = await response.json()
                            courses = res_json.get('data', {}).get('coursesData', [])

                            if courses:
                                # Split courses into chunks of 20
                                chunk_size = 20
                                course_chunks = [courses[i:i + chunk_size] for i in range(0, len(courses), chunk_size)]
                                batch_messages = []  # Store message IDs for later cleanup
                                
                                for chunk_index, chunk in enumerate(course_chunks):
                                    text = '📚 **Available Batches:**\n\n'
                                    for course in chunk:
                                        batch_id = course['id']
                                        name = course['name']
                                        price = course['finalPrice']
                                        text += f'`{batch_id}` : <blockquote>{name} 💵₹{price}</blockquote>\n'
                                    
                                    # Add Extract ALL button on last page
                                    if chunk_index == len(course_chunks) - 1:
                                        text += "\n🔄 **To extract all batches one by one, send:** `EXTRACT_ALL`"
                                    
                                    if chunk_index == 0:
                                        msg = await editable.edit(f"{text}\n\n📝 **Send the batch ID to extract**\n🔍 **Total Batches:** {len(courses)}\n📄 **Page:** {chunk_index + 1}/{len(course_chunks)}")
                                        batch_messages.append(msg.id)
                                    else:
                                        # Add 3 second delay between pages
                                        await asyncio.sleep(3)
                                        msg = await m.reply_text(f"{text}\n\n📝 **Send the batch ID to extract**\n🔍 **Total Batches:** {len(courses)}\n📄 **Page:** {chunk_index + 1}/{len(course_chunks)}")
                                        batch_messages.append(msg.id)
                            
                                try:
                                    input2 = await bot.listen(chat_id=m.chat.id, filters=filters.user(user_id), timeout=120)
                                    batch_id = input2.text.strip()
                                    await input2.delete(True)

                                    # Delete all batch list messages
                                    for msg_id in batch_messages:
                                        try:
                                            await bot.delete_messages(m.chat.id, msg_id)
                                        except Exception as e:
                                            logging.error(f"Error deleting message {msg_id}: {e}")

                                    if batch_id.upper() == "EXTRACT_ALL":
                                        status_msg = await m.reply_text("🔄 **Starting batch extraction process...**")
                                        for course in courses:
                                            try:
                                                selected_batch_id = course['id']
                                                selected_batch_name = course['name']
                                                price = course['finalPrice']
                                                clean_batch_name = selected_batch_name.replace("/", "-").replace("|", "-")
                                                clean_file_name = f"{user_id}_{clean_batch_name}"

                                                await status_msg.edit(f"⏳ **Extracting:** {selected_batch_name}")

                                                batch_headers = {
                                                    'Accept': 'application/json, text/plain, */*',
                                                    'region': 'IN',
                                                    'accept-language': 'EN',
                                                    'Api-Version': '22',
                                                    'tutorWebsiteDomain': f'https://{org_code}.courses.store'
                                                }
                                                
                                                params = {
                                                    'courseId': f'{selected_batch_id}',
                                                }

                                                async with session.get(f"https://api.classplusapp.com/v2/course/preview/org/info", params=params, headers=batch_headers) as response:
                                                    if response.status == 200:
                                                        res_json = await response.json()
                                                        Batch_Token = res_json['data']['hash']
                                                        App_Name = res_json['data']['name']

                                                        start_time = time.time()
                                                        course_content, video_count, pdf_count, image_count = await get_cpwp_course_content(session, headers, Batch_Token)
                                                    
                                                        if course_content:
                                                            file = f"{clean_file_name}.txt"
                                                            with open(file, 'w', encoding='utf-8') as f:
                                                                for i in range(0, len(course_content), 1000):
                                                                    chunk = course_content[i:i + 1000]
                                                                    f.write(''.join(chunk))
                                                                    gc.collect()
                                                                    await asyncio.sleep(0.1)

                                                            caption = (
                                                                f"🎯 <b>{App_Name.upper()}</b>\n\n"
                                                                f"🔑 ᴄᴏᴅᴇ: `{org_code}`\n"
                                                                f"<blockquote>📝 ʙᴀᴛᴄʜ: {clean_batch_name}</blockquote>\n\n"
                                                                f"💰 ᴘʀɪᴄᴇ: ₹{course.get('finalPrice', 'N/A')}\n"
                                                                f"📅 ꜱᴛᴀʀᴛ: {course.get('createdAt', 'N/A').split('T')[0] if course.get('createdAt') else 'N/A'}\n"
                                                                f"📅 ᴇɴᴅ: {course.get('expiresAt', 'N/A')}\n"
                                                                f"<blockquote>📊 ᴄᴏɴᴛᴇɴᴛ ᴅᴇᴛᴀɪʟꜱ:\n"
                                                                f"├─⭓ 🎬 ᴠɪᴅᴇᴏꜱ: {video_count}\n"
                                                                f"├─⭓ 📑 ᴘᴅꜰꜱ: {pdf_count}\n"
                                                                f"└─⭓ 🖼 ɪᴍᴀɢᴇꜱ: {image_count}</blockquote>\n\n"
                                                                f"🤖 ᴜꜱɪɴɢ: {join}\n"
                                                                f"⏱ ᴛɪᴍᴇ ᴛᴀᴋᴇɴ: {format_time_taken(start_time)}\n"
                                                                f"📅 ᴅᴀᴛᴇ: {time_new}\n\n"
                                                                f"<blockquote>👑 EXTRACTED BY: {m.from_user.mention}</blockquote>"
                                                            )

                                                            with open(file, 'rb') as f:
                                                                await m.reply_document(
                                                                    document=f,
                                                                    caption=caption,
                                                                    file_name=f"{clean_batch_name}.txt",
                                                                    thumb=thumb
                                                                )
                                                                await app.send_document(
                                                                    chat_id=WITHOUT_LOGS,
                                                                    document=f,
                                                                    caption=caption,
                                                                    file_name=f"{clean_batch_name}.txt",
                                                                    thumb=thumb
                                                                )
                                                            
                                                            os.remove(file)
                                                            # Add 15 second delay between batches
                                                            await status_msg.edit(f"✅ **Extracted:** {selected_batch_name}\n⏳ **Waiting 15s before next batch...**")
                                                            await asyncio.sleep(15)

                                            except Exception as e:
                                                logging.error(f"Error extracting batch {selected_batch_name}: {e}")
                                                await status_msg.edit(f"❌ **Error extracting:** {selected_batch_name}\n⏳ **Skipping to next batch...**")
                                                await asyncio.sleep(5)
                                                continue

                                        await status_msg.edit("✅ **Completed extracting all batches!**")
                                        return

                                    # Continue with single batch extraction as before
                                    selected_course = next((course for course in courses if str(course['id']) == batch_id), None)
                                    
                                    if selected_course:
                                        selected_batch_id = selected_course['id']
                                        selected_batch_name = selected_course['name']
                                        price = selected_course['finalPrice']
                                        clean_batch_name = selected_batch_name.replace("/", "-").replace("|", "-")
                                        clean_file_name = f"{user_id}_{clean_batch_name}"
                                    else:
                                        raise Exception("**Invalid Batch ID**")

                                except asyncio.TimeoutError:
                                    await editable.edit("⏰ **Tɪᴍᴇᴏᴜᴛ!** Yᴏᴜ ᴛᴏᴏᴋ ᴛᴏᴏ ʟᴏɴɢ ᴛᴏ ʀᴇsᴘᴏɴᴅ")
                                    return
                                except Exception as e:
                                    logging.exception("Error during batch selection:")
                                    await editable.edit(f"❌ **Eʀʀᴏʀ:** {str(e)}")
                                    return

                                download_price = int(price * 0.10)
                                batch_headers = {
                                    'Accept': 'application/json, text/plain, */*',
                                    'region': 'IN',
                                    'accept-language': 'EN',
                                    'Api-Version': '22',
                                    'tutorWebsiteDomain': f'https://{org_code}.courses.store'
                                }
                                
                                params = {
                                    'courseId': f'{selected_batch_id}',
                                }

                                async with session.get(f"https://api.classplusapp.com/v2/course/preview/org/info", params=params, headers=batch_headers) as response:
                                    if response.status == 200:
                                        res_json = await response.json()
                                        Batch_Token = res_json['data']['hash']
                                        App_Name = res_json['data']['name']

                                        await editable.edit(f"🔄 **Exᴛʀᴀᴄᴛɪɴɢ ᴄᴏᴜʀsᴇ:** {selected_batch_name} ...")

                                        start_time = time.time()
                                        course_content, video_count, pdf_count, image_count = await get_cpwp_course_content(session, headers, Batch_Token)
                                    
                                        if course_content:
                                            # Count different types of links
                                            video_count = sum(1 for line in course_content if any(ext in line.lower() for ext in ['.m3u8', '.mp4', '.m4s']))
                                            pdf_count = sum(1 for line in course_content if '.pdf' in line.lower())
                                            total_links = len(course_content)

                                            # Write content to file in chunks
                                            file = f"{clean_file_name}.txt"
                                            chunk_size = 1000  # Process 1000 lines at a time
                                            
                                            with open(file, 'w', encoding='utf-8') as f:
                                                for i in range(0, len(course_content), chunk_size):
                                                    chunk = course_content[i:i + chunk_size]
                                                    f.write(''.join(chunk))
                                                    # Force garbage collection after each chunk
                                                    gc.collect()
                                                    
                                                    # Add a small delay to prevent memory spikes
                                                    await asyncio.sleep(0.1)
                                            
                                            # Clear large variables when no longer needed
                                            course_content = None
                                            gc.collect()

                                            end_time = time.time()
                                            response_time = end_time - start_time
                                            minutes = int(response_time // 60)
                                            seconds = int(response_time % 60)

                                            if minutes == 0:
                                                if seconds < 1:
                                                    formatted_time = f"{response_time:.2f} sᴇᴄᴏɴᴅs"
                                                else:
                                                    formatted_time = f"{seconds} sᴇᴄᴏɴᴅs"
                                            else:
                                                formatted_time = f"{minutes} ᴍɪɴᴜᴛᴇs {seconds} sᴇᴄᴏɴᴅs"

                                            await editable.delete(True)
                                        
                                            user = await bot.get_users(user_id)
                                            user_name = user.first_name
                                            if user.last_name:
                                                user_name += f" {user.last_name}"
                                            mention = f'<a href="tg://user?id={user_id}">{user_name}</a>'
                                            
                                            # Create caption
                                            caption = (
                                            f"🎯 <b>{App_Name.upper()}</b>\n\n"
                                            f"🔑 ᴄᴏᴅᴇ: `{org_code}`\n"
                                            f"<blockquote>📝 ʙᴀᴛᴄʜ: {clean_batch_name}</blockquote>\n\n"
                                            f"💰 ᴘʀɪᴄᴇ: ₹{selected_course.get('finalPrice', 'N/A')}\n"
                                            f"📅 ꜱᴛᴀʀᴛ: {selected_course.get('createdAt', 'N/A').split('T')[0] if selected_course.get('createdAt') else 'N/A'}\n"
                                            f"📅 ᴇɴᴅ: {selected_course.get('expiresAt', 'N/A')}\n"
                                            f"<blockquote>📊 ᴄᴏɴᴛᴇɴᴛ ᴅᴇᴛᴀɪʟꜱ:\n"
                                            f"├─⭓ 🎬 ᴠɪᴅᴇᴏꜱ: {video_count}\n"
                                            f"├─⭓ 📑 ᴘᴅꜰꜱ: {pdf_count}\n"
                                            f"└─⭓ 🖼 ɪᴍᴀɢᴇꜱ: {image_count}</blockquote>\n\n"
                                            f"🤖 ᴜꜱɪɴɢ: {join}\n"
                                            f"⏱ ᴛɪᴍᴇ ᴛᴀᴋᴇɴ: {format_time_taken(start_time)}\n"
                                            f"📅 ᴅᴀᴛᴇ: {time_new}\n\n"
                                            f"<blockquote><b>👑 EXTRACTED BY:</b> {mention}</blockquote>"
                                        )
                                            
                                            progress = await m.reply_text("🔄 **Exᴛʀᴀᴄᴛɪɴɢ ʟɪɴᴋs, ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ...**")
                                            await progress.edit("💾 **Sᴀᴠɪɴɢ ʟɪɴᴋs ᴛᴏ ғɪʟᴇ...**")
                                            with open(file, 'rb') as f:
                                                # Send to user
                                                doc = await m.reply_document(document=f, caption=caption, file_name=f"{clean_batch_name}.txt", thumb=thumb)
                                                # Send to log channel
                                                await app.send_document(chat_id=WITHOUT_LOGS, document=f, caption=caption, file_name=f"{clean_batch_name}.txt", thumb=thumb)
                                            await progress.edit("⬆️ **Uᴘʟᴏᴀᴅɪɴɢ ʏᴏᴜʀ ᴛxᴛ ғɪʟᴇ...**")
                                            await progress.edit("✅ **Dᴏɴᴇ! Yᴏᴜʀ ᴛxᴛ ғɪʟᴇ ɪs ʀᴇᴀᴅʏ.**")

                                            os.remove(file)

                                        else:
                                            raise Exception("**Dɪᴅɴ'ᴛ Fɪɴᴅ Aɴʏ Cᴏɴᴛᴇɴᴛ Iɴ Tʜᴇ Cᴏᴜʀsᴇ**")
                                    else:
                                        raise Exception(f"{response.text}")
                        else:
                            raise Exception(f"{response.text}")
                else:
                    raise Exception('**Nᴏ Aᴘᴘ Fᴏᴜɴᴅ Iɴ Oʀɢ Cᴏᴅᴇ**')
                    
        except Exception as e:
            await editable.edit(f"❌ **Eʀʀᴏʀ:** {str(e)}")
            
        finally:
            await session.close()
            await CONNECTOR.close()
            gc.collect()
