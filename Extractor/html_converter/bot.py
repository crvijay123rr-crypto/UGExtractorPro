import os
import re
import base64
import random
import string
from pyrogram import Client
from pyrogram.types import Message
from config import CHANNEL_ID

thumb_path = "Extractor/thumbs/html-5.png"


# ================= EXTRACT =================
def extract_names_and_urls(file_content):
    lines = file_content.strip().split("\n")
    data = []

    for line in lines:
        if not line.strip():
            continue

        for sep in [':', ' - ', '|', '=>', '->']:
            if sep in line:
                parts = line.split(sep, 1)
                if len(parts) == 2:
                    name = parts[0].strip()
                    url = parts[1].strip().strip('"').strip("'")

                    if "media-cdn.classplusapp.com" in url:
                        url = f"https://ugxclassplusapi.vercel.app/get/cp/dl?url={url}"

                    data.append((name, url))
                    break
    return data


# ================= CATEGORIZE =================
def categorize_urls(urls):
    videos, pdfs, others = [], [], []

    for name, url in urls:
        u = url.lower()

        if any(x in u for x in [".m3u8", ".mp4", ".mpd", "youtu", "vimeo", "jwplayer", "testbook"]):
            videos.append((name, url))
        elif ".pdf" in u:
            pdfs.append((name, url))
        else:
            others.append((name, url))

    return videos, pdfs, others


# ================= OBFUSCATE =================
def obfuscate_url(url):
    salt = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    return base64.b64encode((salt + url).encode()).decode()


# ================= HTML GENERATOR =================
def generate_html(file_name, videos, pdfs, others):
    title = file_name.replace(".txt", "")

    video_cards = ""
    for n, u in videos:
        encoded = obfuscate_url(u)
        video_cards += f"<div class='card' onclick=\"play('{encoded}')\">🎬 {n}</div>"

    pdf_cards = ""
    for n, u in pdfs:
        pdf_cards += f"<div class='card'><a href='{u}' target='_blank' rel='noopener noreferrer'>📄 {n}</a></div>"

    other_cards = ""
    for n, u in others:
        other_cards += f"<div class='card'><a href='{u}' target='_blank' rel='noopener noreferrer'>🔗 {n}</a></div>"

    return f"""<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>

<link rel="stylesheet" href="https://cdn.plyr.io/3.7.8/plyr.css">
<script src="https://cdn.plyr.io/3.7.8/plyr.polyfilled.js"></script>
<script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>

<style>
body {{
    margin:0;
    font-family:sans-serif;
    background: radial-gradient(circle at top,#2b0000,#000);
    color:white;
}}

h2 {{
    text-align:center;
}}

video {{
    width:100%;
    border-radius:10px;
}}

select {{
    width:100%;
    padding:10px;
    margin:10px 0;
    border-radius:8px;
    background:#111;
    color:white;
    border:none;
}}

.card {{
    background:#111;
    padding:12px;
    margin:8px 0;
    border-radius:10px;
    cursor:pointer;
    transition:0.3s;
}}

.card:hover {{
    background:#1f1f1f;
    box-shadow:0 0 10px red;
}}

.tabs {{
    display:flex;
    gap:5px;
}}

.tab {{
    flex:1;
    padding:10px;
    text-align:center;
    background:#111;
    cursor:pointer;
    border-radius:6px;
}}

.active {{
    background:red;
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

<h2>📦 {title}</h2>

<video id="player" controls></video>

<select onchange="changeQuality(this.value)">
<option value="auto">Auto Quality</option>
<option value="360">360p</option>
<option value="720">720p</option>
</select>

<div class="tabs">
<div class="tab active" onclick="tab('video',this)">🎬 Videos ({len(videos)})</div>
<div class="tab" onclick="tab('pdf',this)">📄 PDF ({len(pdfs)})</div>
<div class="tab" onclick="tab('other',this)">🔗 Others ({len(others)})</div>
</div>

<div id="video" class="section active">{video_cards}</div>
<div id="pdf" class="section">{pdf_cards}</div>
<div id="other" class="section">{other_cards}</div>

<script>
let player = new Plyr('#player');
let hls = null;

function decode(x){{
    return atob(x).slice(6);
}}

function play(x){{
    let url = decode(x);

    if(hls){{
        hls.destroy();
        hls = null;
    }}

    if(url.includes(".m3u8")){{
        hls = new Hls();
        hls.loadSource(url);
        hls.attachMedia(player.media);

        hls.on(Hls.Events.MANIFEST_PARSED, function () {{
            player.play();
        }});
    }} else {{
        player.source = {{
            type: 'video',
            sources: [{{ src: url, type: 'video/mp4' }}]
        }};
        player.play();
    }}

    window.scrollTo({{top:0,behavior:'smooth'}});
}}

function changeQuality(q){{
    if(!hls || !hls.levels) return;

    if(q === "auto"){{
        hls.currentLevel = -1;
    }} else {{
        for(let i=0;i<hls.levels.length;i++){{
            if(hls.levels[i].height == q){{
                hls.currentLevel = i;
                break;
            }}
        }}
    }}
}}

function tab(id,el){{
    document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
    el.classList.add('active');

    document.querySelectorAll('.section').forEach(s=>s.classList.remove('active'));
    document.getElementById(id).classList.add('active');
}}
</script>

</body>
</html>
"""


# ================= BOT HANDLER =================
async def handle_txt2html(client: Client, message: Message):
    
    if not message.document or not message.document.file_name.endswith('.txt'):
        await message.reply_text("❌ Please upload a valid .txt file.")
        return
        
    try:
        file_path = await message.download()
        file_name = message.document.file_name
        
        with open(file_path, "r", encoding='utf-8') as f:
            file_content = f.read()
            
        urls = extract_names_and_urls(file_content)
        if not urls:
            await message.reply_text(
                "❌ No valid content found!\n\n"
                "📌 Format:\nName: URL"
            )
            return
            
        videos, pdfs, others = categorize_urls(urls)
        html_content = generate_html(file_name, videos, pdfs, others)
        
        base_name = os.path.splitext(file_name)[0]
        html_file_name = f"{base_name}@courses_hub2_bot.html"
        html_file_path = os.path.join(os.path.dirname(file_path), html_file_name)
        
        with open(html_file_path, "w", encoding='utf-8') as f:
            f.write(html_content)
        
        caption = (
            "<b>✨ HTML FILE GENERATED SUCCESSFULLY ✨</b>\n\n"
            "┏━━━━━━━━━━━━━━━━━━━━━━━┓\n"
            "┃ 🖤 Ultra Dark Premium UI\n"
            "┃ 🎬 Direct Video Player\n"
            "┃ ⚡ Quality Selector (Auto/360/720)\n"
            "┃ 📄 PDF Support\n"
            "┃ 🔗 Clean Categories\n"
            "┃ 🚀 Fast Streaming\n"
            "┗━━━━━━━━━━━━━━━━━━━━━━━┛"
        )
        
        await message.reply_document(
            document=html_file_path,
            thumb=thumb_path if thumb_path else None,
            caption=caption,
            file_name=html_file_name
        )

        if CHANNEL_ID:
            await client.send_document(chat_id=CHANNEL_ID, document=html_file_path)
        
        try:
            os.remove(file_path)
            os.remove(html_file_path)
        except:
            pass
            
    except Exception as e:
        await message.reply_text(f"❌ Error: {str(e)}")


async def show_txt2html_help(client: Client, message: Message):
    await message.reply_text(
        "<b>📝 TXT ➜ HTML CONVERTER</b>\n\n"
        "┏━━━━━━━━━━━━━━━━━━━━━━━┓\n"
        "┃ 🖤 Modern Dark UI\n"
        "┃ 🎬 Built-in Video Player\n"
        "┃ 📄 PDF Section Support\n"
        "┃ 🔗 Smart Link Categorization\n"
        "┃ 🔍 Live Search Feature\n"
        "┃ 📱 Fully Responsive Design\n"
        "┗━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
        "<b>📩 Send a .txt file to start</b>\n"
        "<i>⚡ Auto convert into premium HTML player</i>"
    )
