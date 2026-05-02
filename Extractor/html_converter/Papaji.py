import os
import re
import base64
import random
import string
from pyrogram import Client, filters
from pyrogram.types import Message
from config import CHANNEL_ID

thumb_path = "Extractor/thumbs/html-5.png"


def extract_names_and_urls(file_content):
    lines = file_content.strip().split("\n")
    data = []
    
    for line in lines:
        if not line.strip():
            continue
            
        separators = [':', ' - ', '|', '=>', '->']
        for separator in separators:
            if separator in line:
                parts = line.split(separator, 1)
                if len(parts) == 2:
                    name = parts[0].strip()
                    url = parts[1].strip()
                    url = url.strip('"').strip("'").strip()
                    
                    if "media-cdn.classplusapp.com" in url:
                        url = f"https://ugxclassplusapi.vercel.app/get/cp/dl?url={url}"
                    
                    data.append((name, url))
                    break
                    
    return data


def categorize_urls(urls):
    videos = []
    pdfs = []
    others = []

    video_patterns = [
        r'\.m3u8',
        r'\.mp4',
        r'media-cdn\.classplusapp\.com',
        r'api\.extractor\.workers\.dev',
        r'cpvod\.testbook',
        r'/master\.mpd',
        r'youtube\.com',
        r'youtu\.be',
        r'player\.vimeo\.com',
        r'dailymotion\.com',
        r'jwplayer',
        r'brightcove'
    ]
    
    pdf_patterns = [
        r'\.pdf',
        r'/pdf/',
        r'drive\.google\.com.*pdf',
        r'docs\.google\.com.*pdf'
    ]
    
    image_patterns = [
        r'\.jpg', r'\.jpeg', r'\.png', r'\.gif', r'\.webp',
        r'imgur\.com', r'\.svg', r'\.bmp'
    ]

    for name, url in urls:
        url = url.strip()
        
        is_video = any(re.search(pattern, url, re.IGNORECASE) for pattern in video_patterns)
        if is_video:
            videos.append((name, url))
            continue
            
        is_pdf = any(re.search(pattern, url, re.IGNORECASE) for pattern in pdf_patterns)
        if is_pdf:
            pdfs.append((name, url))
            continue
            
        link_type = 'default'
        link_icon = 'fas fa-link'
        
        if any(re.search(pattern, url, re.IGNORECASE) for pattern in image_patterns):
            link_type = 'image'
            link_icon = 'fas fa-image'
        elif 'youtube.com' in url or 'youtu.be' in url:
            link_type = 'youtube'
            link_icon = 'fab fa-youtube'
        elif 'twitter.com' in url or 'x.com' in url:
            link_type = 'twitter'
            link_icon = 'fab fa-twitter'
        elif 'facebook.com' in url:
            link_type = 'facebook'
            link_icon = 'fab fa-facebook'
        elif 'instagram.com' in url:
            link_type = 'instagram'
            link_icon = 'fab fa-instagram'
        elif 'linkedin.com' in url:
            link_type = 'linkedin'
            link_icon = 'fab fa-linkedin'
        elif 'github.com' in url:
            link_type = 'github'
            link_icon = 'fab fa-github'
        elif 'drive.google.com' in url:
            link_type = 'gdrive'
            link_icon = 'fab fa-google-drive'
        elif 'docs.google.com' in url:
            link_type = 'gdocs'
            link_icon = 'fas fa-file-alt'
        
        others.append((name, url, link_type, link_icon))

    return videos, pdfs, others


def obfuscate_url(url):
    salt = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    salted = salt + url
    encoded = base64.b64encode(salted.encode()).decode()
    encoded = base64.b64encode(encoded.encode()).decode()
    return encoded
def generate_html(file_name, videos, pdfs, others):
    file_name_without_extension = os.path.splitext(file_name)[0]

    def get_video_action(url):
        if 'utkarshapp.com' in url:
            return f"window.open('{url}', '_blank')"
        return f"playVideo('{obfuscate_url(url)}')"

    video_items = "".join(
        f'<div class="list-group-item video" onclick="{get_video_action(url)}"><i class="fas fa-play"></i> {name}</div>'
        for name, url in videos
    )

    pdf_items = "".join(
        f'<div class="list-group-item pdf"><i class="fas fa-file-pdf"></i> {name} <button onclick="openPDF(`{obfuscate_url(url)}`)">Open</button></div>'
        for name, url in pdfs
    )

    other_items = "".join(
        f'<div class="list-group-item other"><i class="{icon}"></i> <a href="{url}" target="_blank">{name}</a></div>'
        for name, url, _, icon in others
    )

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">

<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">

<style>

/* 🔥 BACKGROUND */
body {{
    margin:0;
    background:#2b0000;
    background-image: radial-gradient(rgba(255,255,255,0.08) 1px, transparent 1px);
    background-size:18px 18px;
    color:white;
    font-family:sans-serif;
}}

/* 🔥 TOPBAR */
.topbar {{
    display:flex;
    justify-content:space-between;
    padding:15px;
    background:#1a0000;
}}

.logo {{
    font-size:20px;
    font-weight:bold;
    background:linear-gradient(45deg,orange,red);
    -webkit-background-clip:text;
    -webkit-text-fill-color:transparent;
}}

.bot {{
    color:#00ffd5;
    animation:glow 2s infinite alternate;
}}

@keyframes glow {{
    from{{text-shadow:0 0 5px #00ffd5;}}
    to{{text-shadow:0 0 20px #00ffd5;}}
}}

/* HERO */
.hero {{
    text-align:center;
    padding:20px;
}}

.clock {{
    font-size:40px;
    text-shadow:0 0 10px red;
}}

.main-title {{
    font-size:26px;
    font-weight:bold;
}}

.creator {{
    color:orange;
}}

/* SEARCH */
.search {{
    width:90%;
    padding:12px;
    border-radius:12px;
    border:none;
    margin-top:10px;
    background:#3a0000;
    color:white;
}}

/* TABS */
.tabs {{
    display:flex;
    justify-content:center;
    gap:10px;
    margin-top:15px;
}}

.tab {{
    padding:10px 15px;
    border-radius:20px;
    border:none;
    background:#3a0000;
    color:white;
    cursor:pointer;
}}

.tab.active {{
    background:linear-gradient(45deg,orange,red);
}}

/* ITEMS */
.list-group-item {{
    background:#1f0000;
    margin:10px;
    padding:15px;
    border-radius:12px;
    cursor:pointer;
}}

.list-group-item:hover {{
    background:#330000;
}}

/* CATEGORY */
.category {{
    background:#3a0000;
    margin:20px;
    padding:30px;
    border-radius:20px;
    text-align:center;
}}

</style>
</head>

<body>

<div class="topbar">
    <div class="logo">⚡ CR CHOUDHARY</div>
    <div class="bot">@COURSES_HUB2_BOT</div>
</div>

<div class="hero">
    <div class="clock" id="clock"></div>
    <h1 class="main-title">{file_name_without_extension}</h1>
    <p class="creator">👤 Created by CHOUDHARY</p>

    <input type="text" id="search" class="search" placeholder="Search...">

    <div class="tabs">
        <button class="tab active" onclick="filterTab('all')">All</button>
        <button class="tab" onclick="filterTab('video')">🎬 Video</button>
        <button class="tab" onclick="filterTab('pdf')">📄 PDF</button>
        <button class="tab" onclick="filterTab('other')">📂 Other</button>
    </div>
</div>

<div class="category">
    📂 {len(videos)+len(pdfs)+len(others)} Items
</div>

<div id="content">
{video_items}
{pdf_items}
{other_items}
</div>

<!-- 🎬 PLAYER -->
<video id="player" controls style="width:100%;"></video>

<script>

function decodeUrl(data){{
    try{{
        return atob(atob(data)).slice(8);
    }}catch(e){{return data;}}
}}

function playVideo(data){{
    let url = decodeUrl(data);
    let v = document.getElementById("player");
    v.src = url;
    v.play();
    window.scrollTo(0,0);
}}

function openPDF(data){{
    let url = decodeUrl(data);
    window.open(url,"_blank");
}}

function filterTab(type){{
    document.querySelectorAll(".list-group-item").forEach(el=>{{
        el.style.display="block";
        if(type!="all" && !el.classList.contains(type)){{
            el.style.display="none";
        }}
    }});

    document.querySelectorAll(".tab").forEach(t=>t.classList.remove("active"));
    event.target.classList.add("active");
}}

document.getElementById("search").oninput=function(){{
    let val=this.value.toLowerCase();
    document.querySelectorAll(".list-group-item").forEach(el=>{{
        el.style.display = el.innerText.toLowerCase().includes(val) ? "block":"none";
    }});
}}

setInterval(()=>{
    document.getElementById("clock").innerText = new Date().toLocaleTimeString();
},1000);

</script>

</body>
</html>
"""
    return html  
async def handle_txt2html(client: Client, message: Message):
    if not message.document:
        return

    file_path = await message.download()

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        await message.reply_text("❌ File read error")
        return

    urls = extract_names_and_urls(content)

    if not urls:
        await message.reply_text("❌ No valid links found")
        return

    videos, pdfs, others = categorize_urls(urls)

    html_content = generate_html(message.document.file_name, videos, pdfs, others)

    output_file = file_path + ".html"

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)
    except Exception:
        await message.reply_text("❌ HTML generate error")
        return

    await message.reply_document(
        document=output_file,
        thumb=thumb_path,
        caption="✅ Your PRO HTML is ready!"
    )

    # optional cleanup
    try:
        os.remove(file_path)
    except:
        pass  
