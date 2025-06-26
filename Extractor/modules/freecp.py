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
from config import PREMIUM_LOGS
import config
from pyrogram import Client, filters, idle
from pyrogram.types import Message
# from pyrogram.errors import ListenerTimeout
from subprocess import getstatusoutput
from datetime import datetime, timedelta

import pytz
# from Extractor.modules.enc import process_file_content  # Add encryption import
import zipfile

# Global variables and constants
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

THREADPOOL = ThreadPoolExecutor(max_workers=5000)

async def download_thumbnail(session: aiohttp.ClientSession, url: str) -> str | None:
    """Download thumbnail from URL"""
    try:
        # Create a temporary filename with timestamp
        thumb_path = f"thumb_{int(time.time())}.jpg"
        
        async with session.get(url, timeout=30) as response:
            if response.status == 200:
                # Save the thumbnail
                with open(thumb_path, "wb") as f:
                    f.write(await response.read())
                return thumb_path
            return None
    except Exception as e:
        logging.error(f"Error downloading thumbnail: {e}")
        return None

def create_html_file(file_name, batch_name, contents):
    tbody = ''
    parts = contents.split('\n')
    for part in parts:
        split_part = [item.strip() for item in part.split(':', 1)]
    
        text = split_part[0] if split_part[0] else 'Untitled'
        url = split_part[1].strip() if len(split_part) > 1 and split_part[1].strip() else 'No URL'

        tbody += f'<tr><td>{text}</td><td><a href="{url}" target="_blank">{url}</a></td></tr>'

    with open('Extractor/core/template.html', 'r') as fp:
        file_content = fp.read()
    title = batch_name.strip()
    with open(file_name, 'w') as fp:
        fp.write(file_content.replace('{{tbody_content}}', tbody).replace('{{batch_name}}', title))
        

def clean_filename(name: str) -> str:
    """Clean filename to be Windows-compatible"""
    # Remove invalid characters and common problematic characters
    invalid_chars = '<>:"/\\|?*\n\r\t'
    name = ''.join(char if char not in invalid_chars else '_' for char in name)
    # Remove trailing spaces and periods
    name = name.strip('. ')
    # Replace multiple spaces/underscores with single one
    name = re.sub(r'[_\s]+', '_', name)
    # Limit length
    if len(name) > 180:
        name = name[:177] + '...'
    return name

def create_safe_path(*parts: str) -> str:
    """Create a safe path from parts"""
    # Clean each part and join with forward slashes
    cleaned_parts = [clean_filename(part) for part in parts if part]
    return '/'.join(cleaned_parts)

#======================================================================================================================





async def fetch_cpwp_signed_url(url_val: str, name: str, session: aiohttp.ClientSession, headers: Dict[str, str]) -> str | None:
    MAX_RETRIES = 5  # Increased from 3 to 5
    TIMEOUT = 60  # Increased timeout to 60 seconds
    
    for attempt in range(MAX_RETRIES):
        params = {"url": url_val}
        try:
            async with session.get(
                "https://api.classplusapp.com/cams/uploader/video/jw-signed-url", 
                params=params, 
                headers=headers,
                timeout=TIMEOUT
            ) as response:
                if response.status == 429:  # Rate limit
                    wait_time = min(2 ** attempt, 30)  # Exponential backoff, max 30 seconds
                    await asyncio.sleep(wait_time)
                    continue
                    
                response.raise_for_status()
                response_json = await response.json()
                signed_url = response_json.get("url") or response_json.get('drmUrls', {}).get('manifestUrl')
                if signed_url:
                    return signed_url
                
        except asyncio.TimeoutError:
            logging.error(f"Timeout fetching signed URL for {name} (Attempt {attempt + 1}/{MAX_RETRIES})")
            if attempt < MAX_RETRIES - 1:
                wait_time = min(2 ** attempt, 30)
                await asyncio.sleep(wait_time)
        except Exception as e:
            logging.error(f"Error fetching signed URL for {name}: {e} (Attempt {attempt + 1}/{MAX_RETRIES})")
            if attempt < MAX_RETRIES - 1:
                wait_time = min(2 ** attempt, 30)
                await asyncio.sleep(wait_time)

    logging.error(f"Failed to fetch signed URL for {name} after {MAX_RETRIES} attempts.")
    return None

async def process_cpwp_url(url_val: str, name: str, session: aiohttp.ClientSession, headers: Dict[str, str]) -> str | None:
    """Process video URLs"""
    try:
        # Clean up the name - remove extra spaces and special chars
        clean_name = name.strip().replace('\n', ' ').replace('\r', '')
        # Get video name from the full path
        if '][' in clean_name:
            video_name = clean_name.split(']')[1].strip('[')
        else:
            video_name = clean_name
        
        # If already a video URL, return as is
        if url_val.endswith(('.m3u8', '.mp4', '.mpd')):
            return f"{video_name} : {url_val}\n"
            
        # For special cases like testbook or drm content
        if "testbook.com" in url_val or "classplusapp.com/drm" in url_val:
            return f"{video_name} : {url_val}\n"
            
        # Transform URLs based on patterns
        if "media-cdn.classplusapp.com/tencent/" in url_val:
            url_val = url_val.rsplit('/', 1)[0] + "/master.m3u8"
        elif "media-cdn.classplusapp.com" in url_val and url_val.endswith('.jpg'):
            identifier = url_val.split('/')[-3]
            url_val = f'https://media-cdn.classplusapp.com/alisg-cdn-a.classplusapp.com/{identifier}/master.m3u8'
        elif "tencdn.classplusapp.com" in url_val and url_val.endswith('.jpg'):
            identifier = url_val.split('/')[-2]
            url_val = f'https://media-cdn.classplusapp.com/tencent/{identifier}/master.m3u8'
        elif "4b06bf8d61c41f8310af9b2624459378203740932b456b07fcf817b737fbae27" in url_val and url_val.endswith('.jpeg'):
            url_val = f"https://media-cdn.classplusapp.com/alisg-cdn-a.classplusapp.com/b08bad9ff8d969639b2e43d5769342cc62b510c4345d2f7f153bec53be84fe35/{url_val.split('/')[-1].split('.')[0]}/master.m3u8"
        elif "cpvideocdn.testbook.com" in url_val and url_val.endswith('.png'):
            match = re.search(r'/streams/([a-f0-9]{24})/', url_val)
            video_id = match.group(1) if match else url_val.split('/')[-2]
            url_val = f'https://cpvod.testbook.com/{video_id}/playlist.m3u8'
        elif "media-cdn.classplusapp.com/drm/" in url_val and url_val.endswith('.png'):
            video_id = url_val.split('/')[-3]
            url_val = f'https://media-cdn.classplusapp.com/drm/{video_id}/playlist.m3u8'
        elif "https://media-cdn.classplusapp.com" in url_val and ("cc/" in url_val or "lc/" in url_val or "uc/" in url_val or "dy/" in url_val) and url_val.endswith('.png'):
            url_val = url_val.replace('thumbnail.png', 'master.m3u8')
        elif "https://tb-video.classplusapp.com" in url_val and url_val.endswith('.jpg'):
            video_id = url_val.split('/')[-1].split('.')[0]
            url_val = f'https://tb-video.classplusapp.com/{video_id}/master.m3u8'
            
        return f"{video_name} : {url_val}\n"
        
    except Exception as e:
        logging.error(f"Error processing URL for {name}: {e}")
        return None


async def get_cpwp_course_content(session: aiohttp.ClientSession, headers: Dict[str, str], Batch_Token: str, folder_id: int = 0, folder_path: str = "", limit: int = 9999999999, retry_count: int = 0, m: Message = None, status_msg = None) -> Tuple[Dict[str, List[str]], int, int, int]:
    MAX_RETRIES = 5
    TIMEOUT = 120
    fetched_urls: set[str] = set()
    folder_contents: Dict[str, List[str]] = {}
    video_count = 0
    pdf_count = 0
    image_count = 0
     
    try:
        content_api = f'https://api.classplusapp.com/v2/course/preview/content/list/{Batch_Token}'
        params = {'folderId': folder_id, 'limit': limit}

        async with session.get(content_api, params=params, headers=headers, timeout=TIMEOUT) as res:
            if res.status == 429:
                wait_time = min(2 ** retry_count, 30)
                await asyncio.sleep(wait_time)
                return await get_cpwp_course_content(session, headers, Batch_Token, folder_id, folder_path, limit, retry_count + 1, m, status_msg)
                
            res.raise_for_status()
            res_json = await res.json()
            contents: List[Dict[str, Any]] = res_json['data']

            # Process folders first
            folders = [c for c in contents if c['contentType'] == 1]
            files = [c for c in contents if c['contentType'] != 1]
            
            current_folder = folder_path if folder_path else "Root"
            
            # Process folders
            for folder in folders:
                folder_name = folder['name'].strip()
                current_path = f"{folder_path}/{folder_name}" if folder_path else folder_name
                
                nested_contents, v_count, p_count, i_count = await get_cpwp_course_content(
                    session, headers, Batch_Token, folder['id'], current_path, retry_count=0, m=m, status_msg=status_msg
                )
                
                # Merge nested contents
                for folder_key, content_list in nested_contents.items():
                    if folder_key in folder_contents:
                        folder_contents[folder_key].extend(content_list)
                    else:
                        folder_contents[folder_key] = content_list
                        
                video_count += v_count
                pdf_count += p_count
                image_count += i_count

            # Process files
            if current_folder not in folder_contents:
                folder_contents[current_folder] = []

            if files:
                for content in files:
                    name = content['name'].strip()
                    url_val = content.get('url') or content.get('thumbnailUrl')

                    if not url_val or url_val in fetched_urls:
                            continue
                            
                    fetched_urls.add(url_val)
                    full_name = f"[{current_folder}][{name}]" if current_folder != "Root" else f"[{name}]"
                    
                    processed_url = await process_cpwp_url(url_val, full_name, session, headers)
                    if processed_url:
                        folder_contents[current_folder].append(processed_url)
                        if '.m3u8' in processed_url or '.mp4' in processed_url:
                            video_count += 1
                        elif '.pdf' in processed_url:
                            pdf_count += 1
                        else:
                            image_count += 1
                                
    except Exception as e:
        logging.error(f"Error: {e}")
        if retry_count < MAX_RETRIES:
            wait_time = min(2 ** retry_count, 30)
            await asyncio.sleep(wait_time)
            return await get_cpwp_course_content(session, headers, Batch_Token, folder_id, folder_path, limit, retry_count + 1, m, status_msg)
        return {}, 0, 0, 0

    return folder_contents, video_count, pdf_count, image_count
    

    
async def process_cpwp(bot: Client, m: Message, user_id: int):
    CHANNEL_ID = -1002601604234
    
    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-encoding': 'gzip',
        'accept-language': 'EN',
        'api-version': '35',
        'app-version': '1.4.73.2',
        'build-number': '35',
        'connection': 'Keep-Alive',
        'content-type': 'application/json',
        'device-details': 'Xiaomi_Redmi 7_SDK-32',
        'device-id': 'c28d3cb16bbdac01',
        'host': 'api.classplusapp.com',
        'region': 'IN',
        'user-agent': 'Mobile-Android',
        'webengage-luid': '00000187-6fe4-5d41-a530-26186858be4c',
        'x-access-token': 'eyJhbGciOiJIUzM4NCIsInR5cCI6IkpXVCJ9.eyJpZCI6MTU0NzYyMTM2LCJvcmdJZCI6OTU2LCJ0eXBlIjoxLCJtb2JpbGUiOiI5MTc4MTc1MjMwNDEiLCJuYW1lIjoiU0lUQSBERVZJIiwiZW1haWwiOiJlcGhwcXFycEBwdW5rcHJvb2YuY29tIiwiaXNGaXJzdExvZ2luIjp0cnVlLCJkZWZhdWx0TGFuZ3VhZ2UiOiJFTiIsImNvdW50cnlDb2RlIjoiSU4iLCJpc0ludGVybmF0aW9uYWwiOjAsImlzRGl5Ijp0cnVlLCJsb2dpblZpYSI6Ik90cCIsImZpbmdlcnByaW50SWQiOiIxOTdiYjA3YzNjYTJjMmFmZWQxZjg4ZDNkMGJjNGRmOSIsImlhdCI6MTc1MDkxOTQ3OCwiZXhwIjoxNzUxNTI0Mjc4fQ._TxiY6KfCG2Dvl622ONdOobnV9I4cqEL9RVaEvhc-Gt76h7hF7z4pOp0_60puqHM'
    }

    loop = asyncio.get_event_loop()
    CONNECTOR = aiohttp.TCPConnector(limit=1000, loop=loop)
    async with aiohttp.ClientSession(connector=CONNECTOR, loop=loop) as session:
        editable = None
        try:
            user = await bot.get_users(user_id)
            user_name = user.first_name
            if user.last_name:
                user_name += f" {user.last_name}"
            mention = f'<a href="tg://user?id={user_id}">{user_name}</a>'
            
            editable = await m.reply_text("**Enter ORG Code Of Your Classplus App**")
            
            try:
                input1 = await bot.listen(chat_id=m.chat.id, filters=filters.user(user_id), timeout=120)
                org_code = input1.text.lower()
                await input1.delete(True)
            except Exception as e:
                    await editable.edit(f"**Error: {e}**")
                    return
        except Exception as e:
            await editable.edit(f"**Error: {e}**")
            return

        hash_headers = {
                'Accept': '*/*',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/128.0.0.0'
            }
            
        try:
                # Get course hash
                async with session.get(f"https://{org_code}.courses.store", headers=hash_headers) as response:
                    html_text = await response.text()
                    hash_match = re.search(r'"hash":"(.*?)"', html_text)

                    if not hash_match:
                        raise Exception("No courses found! Please check the org code.")
                    
                    token = hash_match.group(1)
                    all_courses = []
                    
                # Try new API first
                async with session.get(
                    "https://api.classplusapp.com/v2/course/search/published?limit=100&offset=0&sortBy=courseCreationDate&status=published", 
                            headers=headers
                        ) as response:
                            if response.status == 200:
                                res_json = await response.json()
                                all_courses = res_json.get('data', {}).get('courses', [])
                            else:
                            # Fallback to old API
                                page = 0
                            while True:
                                    async with session.get(
                                f"https://api.classplusapp.com/v2/course/preview/similar/{token}?limit=100&page={page}", 
                                        headers=headers
                                    ) as response:
                                        if response.status != 200:
                                            break
                                        
                                        res_json = await response.json()
                
                                    courses = res_json.get('data', {}).get('coursesData', [])
                                    if not courses:
                                        break
                                    
                                    all_courses.extend(courses)
                                    if len(courses) < 100:
                                        break
                                    page += 1

                                    if not all_courses:
                                        raise Exception("No batches found! Please check if the org code is correct.")

                        # Sort courses by name
                            all_courses.sort(key=lambda x: x.get('name', '').lower())

                        # Split courses into chunks of 20 for display
                            chunks = [all_courses[i:i + 20] for i in range(0, len(all_courses), 20)]
                            total_chunks = len(chunks)

                        # Send first chunk with modern header
                            first_text = (
                    "📚 Available Batches\n"
                    f"📑 Page 1/{total_chunks}\n"
                    "──────────────────\n\n"
                )
                            
                for cnt, course in enumerate(chunks[0], 1):
                    first_text += await format_batch_info(course, cnt)

                first_text += (
                    "──────────────────\n"
                    "Send up to 5 batch numbers\n"
                    "Example: 1, 3, 5, 11, 14"
                )
                await editable.edit(first_text)

                # Send remaining chunks with clean format
                for chunk_num, chunk in enumerate(chunks[1:], 2):
                    chunk_text = (
                        "📚 Available Batches\n"
                        f"📑 Page {chunk_num}/{total_chunks}\n"
                        "──────────────────\n\n"
                    )
                    
                    start_idx = (chunk_num - 1) * 20
                    for cnt, course in enumerate(chunk, start_idx + 1):
                        chunk_text += await format_batch_info(course, cnt)
                    
                    await m.reply_text(chunk_text)
                    await asyncio.sleep(0.5)

        except Exception as e:
                await editable.edit(f"**Error: {e}**")
                return

            # Split by comma and limit to 5 batches
        batch_input = await bot.listen(chat_id=m.chat.id, filters=filters.user(user_id), timeout=300)
        raw_text2 = batch_input.text
        await batch_input.delete(True)

        batch_indices = [idx.strip() for idx in raw_text2.split(',')][:5]
        if len(batch_indices) > 5:
                await m.reply_text("**⚠️ Only first 5 batches will be processed**")
                return
            
        total_batches = len(batch_indices)
        processed_batches = 0
            
        for batch_index in batch_indices:
                batch_index = batch_index.strip()
                start_time = time.time()
                
                if batch_index.isdigit() and int(batch_index) <= len(all_courses):
                    try:
                        batch_headers = {
                            'Accept': '*/*',
                        'region': 'IN',
                        'accept-language': 'EN',
                        'Api-Version': '22',
                            'tutorWebsiteDomain': f'https://{org_code}.courses.store',
                            'x-access-token': headers.get('x-access-token'),
                            'accept-encoding': 'gzip',
                            'connection': 'Keep-Alive',
                            'user-agent': 'Mobile-Android'
                        }
                        
                        try:
                            selected_course_index = int(batch_index)
                            course = all_courses[selected_course_index - 1]
                            selected_batch_id = course['id']
                            clean_batch_name = course['name'].replace('/', '-').replace('|', '-')
                            batch_thumbnail = course.get('imageUrl', '')
                            
                            # Get course preview info
                            preview_url = f"https://api.classplusapp.com/v2/course/preview/org/info"
                            params = {'courseId': selected_batch_id}
                            
                            async with session.get(preview_url, params=params, headers=batch_headers) as response:
                                response_text = await response.text()
                                print(f"\nAPI Response Text: {response_text}")
                                
                                if response.status != 200:
                                    print(f"\n⚠️ Failed to get preview details. Status: {response.status}")
                                    await m.reply_text("⚠️ Failed to get batch preview details")
                                    continue
                                    
                                preview_details = json.loads(response_text)
                                print("\nCOURSE PREVIEW API RESPONSE:")
                                print("="*50)
                                print(json.dumps(preview_details, indent=4))
                                print("="*50 + "\n")
                                
                                # Get Batch Token from preview response
                                Batch_Token = preview_details.get('data', {}).get('hash')
                                App_Name = preview_details.get('data', {}).get('name')
                                
                                if not Batch_Token:
                                    await m.reply_text("⚠️ Failed to get batch token")
                                    continue
                        except Exception as e:
                            await m.reply_text(f"**Error: {e}**")
                            return

                        try:
                            status_msg = await m.reply_text(
                                f"📥 ᴇxᴛʀᴀᴄᴛɪɢ: {clean_batch_name}"
                            )

                            course_content, video_count, pdf_count, image_count = await get_cpwp_course_content(
                                session, headers, Batch_Token, m=m, status_msg=status_msg
                            )

                            if course_content:
                                batch_filename = f"{clean_batch_name}_{batch_index}.txt"
                                zip_filename = f"{clean_batch_name}_{batch_index}_folders.zip"

                                # Try to get thumbnail
                                thumb_path = None
                                if batch_thumbnail:
                                    thumb_path = await download_thumbnail(session, batch_thumbnail)
                                elif config.THUMB_URL:
                                    thumb_path = await download_thumbnail(session, config.THUMB_URL)

                                # Create organized content for txt file
                                organized_content = [
                                    f"{clean_batch_name} : {batch_thumbnail}\n\n"
                                ]
                                
                                # Create zip file with proper folder structure
                                with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
                                    # Add content organized by folders
                                    for folder_name, contents in sorted(course_content.items()):
                                        if contents:
                                            if folder_name != "Root":
                                                organized_content.append(f"[{folder_name}]\n")
                                                folder_path = folder_name.replace('/', '-').replace('\\', '-')
                                        else:
                                                folder_path = "Main"
                                                
                                            # Create folder content
                                        folder_content = []
                                        for content in sorted(contents):
                                                if content:  # Skip empty content
                                                    organized_content.append(content)
                                                    # Extract name and URL
                                                    parts = content.split(" : ", 1)
                                                    if len(parts) == 2:
                                                        name = parts[0].strip('[]')
                                                        url = parts[1].strip()
                                                        folder_content.append(f"{name}\n{url}\n\n")
                                                        
                                            # Add to zip with folder structure
                                        if folder_content:
                                                zip_path = f"{folder_path}/content.txt"
                                                zipf.writestr(zip_path, ''.join(folder_content))
                                            
                                        organized_content.append("\n")  # Add space between folders
                                
                                # Add owner info at the end
                                organized_content.append("Owner: https://t.me/ItsUGBot")

                                # Save txt file
                                with open(batch_filename, 'w', encoding='utf-8') as f:
                                    f.write(''.join(organized_content))

                                # Create caption
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
                                    f"<blockquote><b>👑 EXTRACTED BY:</b> {mention}</blockquote>"
                                )

                                # Send files
                                try:
                                    # Send txt file
                                        with open(batch_filename, 'rb') as f:
                                            await m.reply_document(
                                                document=f, 
                                                caption=caption,
                                                thumb=thumb_path,
                                                file_name=f"{clean_batch_name}_{batch_index}.txt"
                                            )
                                            # Forward to log channel
                                            await sent_txt.copy(chat_id=PREMIUM_LOGS)
                                        # Send zip file
                                        with open(zip_filename, 'rb') as f:
                                            await m.reply_document(
                                            document=f,
                                            caption=f"<blockquote>📁 Folder-wise content for {clean_batch_name}</blockquote>",
                                            thumb=thumb_path,
                                            file_name=f"{clean_batch_name}_{batch_index}_folders.zip"
                                            )
                                except Exception as e:
                                    await m.reply_text(f"**Error sending files: {str(e)}**")
                                finally:
                                        
                                        try:
                                            os.remove(batch_filename)
                                            os.remove(zip_filename)
                                            if thumb_path and os.path.exists(thumb_path):
                                                os.remove(thumb_path)
                                            if status_msg:
                                                await status_msg.delete()
                                        except:
                                            pass
                            else:
                                await m.reply_text(f"**No content found in batch: {clean_batch_name}**")
                    
                        except Exception as e:
                            await m.reply_text(f"**Error processing batch: {str(e)}**")
                        finally:
                            processed_batches += 1
                    except Exception as e:
                        await m.reply_text(f"**Error processing batch: {str(e)}**")
                    finally:
                            processed_batches += 1
                else:
                    await m.reply_text(f"**Invalid batch index: {batch_index}**")

        await m.reply_text(f"<blockquote>✅ Completed {processed_batches}/{total_batches} batches</blockquote>")
            
        try:
            await editable.delete()
        except:
            pass
            
        try:
            await editable.edit(error_msg)
            if editable:
                try:
                    await editable.delete()
                except:
                    pass
                    
            if editable:
                try:
                    await editable.edit(error_msg)
                except:
                    await m.reply_text(error_msg)
            else:
                await m.reply_text(error_msg)
            
        finally:
            await session.close()
            await CONNECTOR.close()

async def get_thumbnail_url(url: str) -> str | None:
    """Extract thumbnail URL from video URL"""
    try:
        if url.endswith('.m3u8'):
            return url.replace('master.m3u8', 'thumbnail.jpg')
        elif url.endswith('.mp4'):
            return url.replace('.mp4', '.jpg')
        return None
    except Exception as e:
        logging.error(f"Error getting thumbnail URL: {e}")
        return None

async def format_batch_info(course: Dict[str, Any], index: int) -> str:
    """Format batch information for display"""
    try:
        name = course.get('name', 'Untitled').strip()
        price = course.get('finalPrice', 'N/A')
        created_at = course.get('createdAt', 'N/A')
        if created_at and 'T' in created_at:
            created_at = created_at.split('T')[0]
        
        return (
            f"{index}. {name}\n"
            f"   💰 Price: ₹{price}\n"
            f"   📅 Created: {created_at}\n\n"
        )
    except Exception as e:
        logging.error(f"Error formatting batch info: {e}")
        return f"{index}. Error formatting batch info\n\n"
