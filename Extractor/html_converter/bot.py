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
    """Extract names and URLs from the text content."""
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
                    
                    # Handle classplusapp URLs
                    if "media-cdn.classplusapp.com" in url:
                        url = f"https://ugxclassplusapi.vercel.app/get/cp/dl?url={url}"
                    
                    data.append((name, url))
                    break
                    
    return data

def categorize_urls(urls):
    """Categorize URLs into videos, PDFs, and others."""
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
        
        # Check for video patterns
        is_video = any(re.search(pattern, url, re.IGNORECASE) for pattern in video_patterns)
        if is_video:
            videos.append((name, url))
            continue
            
        # Check for PDF patterns
        is_pdf = any(re.search(pattern, url, re.IGNORECASE) for pattern in pdf_patterns)
        if is_pdf:
            pdfs.append((name, url))
            continue
            
        # Add to others with type info
        link_type = 'default'
        link_icon = 'fas fa-link'
        
        # Check for image
        if any(re.search(pattern, url, re.IGNORECASE) for pattern in image_patterns):
            link_type = 'image'
            link_icon = 'fas fa-image'
        # Check for YouTube
        elif 'youtube.com' in url or 'youtu.be' in url:
            link_type = 'youtube'
            link_icon = 'fab fa-youtube'
        # Check for social media
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
    """Obfuscate URL to make it unreadable but decodable."""
    # Add some salt to make it more complex
    salt = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    salted = salt + url
    # Double encode to make it more obscure
    encoded = base64.b64encode(salted.encode()).decode()
    encoded = base64.b64encode(encoded.encode()).decode()
    return encoded
def generate_html(file_name, videos, pdfs, others):

    title = file_name.replace(".txt", "")

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>

<link rel="stylesheet" href="https://cdn.plyr.io/3.7.8/plyr.css" />
<script src="https://cdn.plyr.io/3.7.8/plyr.polyfilled.js"></script>
<script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>

<style>
body {{
    margin:0;
    font-family: 'Segoe UI';
    background: radial-gradient(circle at top,#2b0000,#000);
    color:white;
}}

.topbar {{
    display:flex;
    justify-content:space-between;
    padding:15px;
    background:#000;
    border-bottom:2px solid red;
}}

.logo {{
    color:#ff3c3c;
    font-weight:bold;
    font-size:22px;
}}

.container {{
    padding:15px;
}}

.video-box {{
    margin-bottom:15px;
}}

.card {{
    background:rgba(255,0,0,0.1);
    padding:14px;
    border-radius:12px;
    margin-bottom:10px;
    backdrop-filter: blur(10px);
    cursor:pointer;
    transition:0.3s;
}}

.card:hover {{
    transform:translateY(-3px);
    box-shadow:0 0 12px red;
}}

.search {{
    width:100%;
    padding:12px;
    border-radius:10px;
    border:none;
    margin:10px 0;
    background:#220000;
    color:white;
}}

.tabs {{
    display:flex;
    gap:10px;
    margin-bottom:10px;
}}

.tab {{
    flex:1;
    text-align:center;
    padding:10px;
    background:#220000;
    border-radius:8px;
    cursor:pointer;
}}

.active {{
    background:#ff3c3c;
}}

.section {{
    display:none;
}}

.section.active {{
    display:block;
}}

</style>
</head>

<body>

<div class="topbar">
<div class="logo">📦 Hub</div>
<div>@courses_hub2_bot</div>
</div>

<div class="container">

<h2 style="text-align:center;">{title}</h2>

<div class="video-box">
<video id="player" controls playsinline></video>
</div>

<input class="search" placeholder="Search..." onkeyup="filter(this.value)">

<div class="tabs">
<div class="tab active" onclick="showTab('video',this)">🎬 Videos ({len(videos)})</div>
<div class="tab" onclick="showTab('pdf',this)">📄 PDF ({len(pdfs)})</div>
<div class="tab" onclick="showTab('other',this)">🔗 Other ({len(others)})</div>
</div>

<div id="video" class="section active">
{''.join([f'<div class="card" onclick="play(\\'{obfuscate_url(u)}\\')">{n}</div>' for n,u in videos])}
</div>

<div id="pdf" class="section">
{''.join([f'<div class="card"><a href="{u}" target="_blank" style="color:white">{n}</a></div>' for n,u in pdfs])}
</div>

<div id="other" class="section">
{''.join([f'<div class="card"><a href="{u}" target="_blank" style="color:white">{n}</a></div>' for n,u in others])}
</div>

</div>

<script>

const player = new Plyr('#player');

function decode(x){{
 return atob(x).slice(6)
}}

function play(x){{
 let url = decode(x)

 if(url.includes(".m3u8")){{
    if(Hls.isSupported()){{
        const hls = new Hls();
        hls.loadSource(url);
        hls.attachMedia(player.media);
        hls.on(Hls.Events.MANIFEST_PARSED, ()=>player.play());
    }}
 }} else {{
    player.source = {{
        type:'video',
        sources:[{{src:url,type:'video/mp4'}}]
    }};
    player.play();
 }}

 window.scrollTo({{top:0,behavior:'smooth'}})
}}

function showTab(id,el){{
 document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'))
 el.classList.add('active')

 document.querySelectorAll('.section').forEach(s=>s.classList.remove('active'))
 document.getElementById(id).classList.add('active')
}}

function filter(q){{
 q=q.toLowerCase()
 document.querySelectorAll('.card').forEach(e=>{
   e.style.display = e.innerText.toLowerCase().includes(q)?'block':'none'
 })
}}

</script>

</body>
</html>
"""
    
    return html

def get_icon_color(link_type):
    """Get Bootstrap color class based on link type."""
    color_map = {
        'image': 'info',
        'youtube': 'danger',
        'twitter': 'info',
        'facebook': 'primary',
        'instagram': 'danger',
        'linkedin': 'primary',
        'github': 'dark',
        'gdrive': 'success',
        'gdocs': 'primary',
        'default': 'success'
    }
    return color_map.get(link_type, 'success')

async def handle_txt2html(client: Client, message: Message):
    """Handle text file to HTML conversion."""
    if not message.document or not message.document.file_name.endswith('.txt'):
        await message.reply_text("Please upload a .txt file.")
        return
        
    try:
        # Download the file
        file_path = await message.download()
        file_name = message.document.file_name
        
        # Read the file content
        with open(file_path, "r", encoding='utf-8') as f:
            file_content = f.read()
            
        # Extract names and URLs
        urls = extract_names_and_urls(file_content)
        if not urls:
            await message.reply_text("❌ No valid content found in the text file.\n\nFormat should be:\nName: URL\nName2: URL2")
            return
            
        # Categorize URLs
        videos, pdfs, others = categorize_urls(urls)
        
        # Generate HTML
        html_content = generate_html(file_name, videos, pdfs, others)
        
        # Save HTML file with @Courses_hub2_bot suffix
        base_name = os.path.splitext(file_name)[0]
        html_file_name = f"{base_name}@courses_hub2_bot.html"
        html_file_path = os.path.join(os.path.dirname(file_path), html_file_name)
        
        with open(html_file_path, "w", encoding='utf-8') as f:
            f.write(html_content)
        
        # Send the HTML file
        await message.reply_document(
            document=html_file_path,
            thumb=thumb_path if thumb_path else None,
            caption="<blockquote>✨ ʜᴛᴍʟ ꜰɪʟᴇ ɢᴇɴᴇʀᴀᴛᴇᴅ ꜱᴜᴄᴄᴇꜱꜰᴜʟʟʏ!</blockquote>\n\n"
            "• 🖤 ᴜʟᴛʀᴀ ᴍᴏᴅᴇʀɴ ᴅᴀʀᴋ ᴜɪ\n"
            "• 🎬 ꜱᴍᴀʀᴛ ᴠɪᴅᴇᴏ ᴘʟᴀʏᴇʀ\n"
            "• 📄 ᴘᴅꜰ ᴅᴏᴡɴʟᴏᴀᴅ ꜱᴜᴘᴘᴏʀᴛ\n"
            "• ✨ ʙᴇᴀᴜᴛɪꜰᴜʟ ᴀɴɪᴍᴀᴛɪᴏɴꜱ\n"
            "• 🧭 ꜰʟᴏᴀᴛɪɴɢ ᴄᴏɴᴛʀᴏʟꜱ",
    file_name=html_file_name
)

        
        # Forward to channel if configured
        if CHANNEL_ID:
            await client.send_document(chat_id=CHANNEL_ID, document=html_file_path)
        
        # Cleanup
        try:
            os.remove(file_path)
            os.remove(html_file_path)
        except:
            pass
            
    except Exception as e:
        await message.reply_text(f"❌ Error processing file: {str(e)}")
async def show_txt2html_help(client: Client, message: Message):
    await message.reply_text(
        "<b>📝 ᴛxᴛ ➜ ʜᴛᴍʟ ᴄᴏɴᴠᴇʀᴛᴇʀ</b>\n"
        "<blockquote>• ᴍᴏᴅᴇʀɴ ᴅᴀʀᴋ ᴛʜᴇᴍᴇ ᴜɪ 🖤</blockquote>\n"
        "<blockquote>• ᴠɪᴅᴇᴏ ᴘʟᴀʏᴇʀ ɪɴᴛᴇɢʀᴀᴛɪᴏɴ 🎬</blockquote>\n"
        "<blockquote>• ᴘᴅꜰ ᴅᴏᴄᴜᴍᴇɴᴛ ꜱᴇᴄᴛɪᴏɴ 📄</blockquote>\n"
        "<blockquote>• ꜱᴍᴀʀᴛ ꜱᴇᴀʀᴄʜ ꜰᴜɴᴄᴛɪᴏɴᴀʟɪᴛʏ 🔎</blockquote>\n"
        "<blockquote>• ʀᴇꜱᴘᴏɴꜱɪᴠᴇ ᴅᴇꜱɪɢɴ 📱</blockquote>\n"
        "<b>📩 ꜱᴇɴᴅ ᴀ .ᴛxᴛ ꜰɪʟᴇ ᴛᴏ ɢᴇᴛ ꜱᴛᴀʀᴛᴇᴅ!</b>"
    )

