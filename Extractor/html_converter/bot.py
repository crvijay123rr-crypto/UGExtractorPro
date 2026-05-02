import os
import re
import base64
import random
import string
from pyrogram import Client
from pyrogram.types import Message
from config import CHANNEL_ID

thumb_path = "Extractor/thumbs/html-5.png"

# =========================
# EXTRACT DATA
# =========================
def extract_names_and_urls(file_content):
    lines = file_content.strip().split("\n")
    data = []

    for line in lines:
        if not line.strip():
            continue

        separators = [':', ' - ', '|', '=>', '->']

        for sep in separators:
            if sep in line:
                name, url = line.split(sep, 1)
                name = name.strip()
                url = url.strip().strip('"').strip("'")

                if "media-cdn.classplusapp.com" in url:
                    url = f"https://ugxclassplusapi.vercel.app/get/cp/dl?url={url}"

                data.append((name, url))
                break

    return data


# =========================
# CATEGORIZE
# =========================
def categorize_urls(urls):
    videos, pdfs, others = [], [], []

    for name, url in urls:

        if re.search(r"\.mp4|\.m3u8|youtube|youtu\.be", url, re.I):
            videos.append((name, url))

        elif re.search(r"\.pdf", url, re.I):
            pdfs.append((name, url))

        else:
            others.append((name, url))

    return videos, pdfs, others


# =========================
# ENCODE
# =========================
def obfuscate_url(url):
    salt = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    return base64.b64encode((salt + url).encode()).decode()


# =========================
# FOLDER SYSTEM 🔥
# =========================
def group_by_folder(items):
    folders = {}

    for name, url in items:
        if "/" in name:
            folder, item = name.split("/", 1)
        else:
            folder, item = "General", name

        folders.setdefault(folder, []).append((item, url))

    return folders


# =========================
# HTML GENERATOR (FULL UI)
# =========================
def generate_html(file_name, videos, pdfs, others):

    video_folders = group_by_folder(videos)
    pdf_folders = group_by_folder(pdfs)
    other_folders = group_by_folder(others)

    def build_section(folders, mode):
        html = ""

        for folder, items in folders.items():
            html += f"<h4 class='folder'>📁 {folder}</h4>"

            for name, url in items:
                enc = obfuscate_url(url)

                if mode == "video":
                    html += f"""
                    <div class="item" onclick="playVideo('{enc}')">
                        ▶ {name}
                    </div>
                    """

                elif mode == "pdf":
                    html += f"""
                    <div class="item">
                        📄 {name}
                        <button onclick="viewPDF('{enc}')">View</button>
                        <button onclick="downloadFile('{enc}','{name}.pdf')">Download</button>
                    </div>
                    """

                else:
                    html += f"""
                    <div class="item">
                        🔗 <span onclick="openLink('{enc}')">{name}</span>
                    </div>
                    """

        return html

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{file_name}</title>

<style>
body {{
    margin:0;
    font-family: 'Segoe UI';
    background: #0f172a;
    color: white;
}}

.header {{
    text-align:center;
    padding:20px;
}}

h2 {{
    margin:0;
}}

.folder {{
    margin-top:25px;
    color:#38bdf8;
}}

.section {{
    margin:20px;
}}

.item {{
    background:#1e293b;
    padding:12px;
    margin:8px 0;
    border-radius:10px;
    cursor:pointer;
    transition:0.3s;
}}

.item:hover {{
    background:#334155;
    transform:translateX(5px);
}}

button {{
    margin-left:10px;
    padding:5px 10px;
    border:none;
    border-radius:6px;
    background:#3b82f6;
    color:white;
    cursor:pointer;
}}

.video-box {{
    width:100%;
    max-width:800px;
    margin:auto;
}}

video {{
    width:100%;
    border-radius:10px;
}}

.search {{
    width:90%;
    padding:10px;
    margin:20px auto;
    display:block;
    border-radius:8px;
    border:none;
}}

</style>
</head>

<body>

<div class="header">
<h1 style="color:#38bdf8;">⚡ CR Choudhary join now @free_courses_2026</h1>
<h2>{file_name}</h2>
</div>

<input class="search" placeholder="Search..." oninput="searchItems(this.value)">

<div class="video-box">
<video id="player" controls></video>
</div>

<div class="section">
<h3>🎬 Videos</h3>
{build_section(video_folders, "video")}
</div>

<div class="section">
<h3>📄 PDFs</h3>
{build_section(pdf_folders, "pdf")}
</div>

<div class="section">
<h3>🔗 Others</h3>
{build_section(other_folders, "other")}
</div>

<script>
function decode(u){{
    return atob(u).slice(6);
}}

function playVideo(u){{
    let url = decode(u);
    let player = document.getElementById("player");
    player.src = url;
    player.play();
    window.scrollTo(0,0);
}}

function viewPDF(u){{
    window.open(decode(u),'_blank');
}}

function downloadFile(u,name){{
    let a = document.createElement('a');
    a.href = decode(u);
    a.download = name;
    a.click();
}}

function openLink(u){{
    window.open(decode(u),'_blank');
}}

function searchItems(val){{
    val = val.toLowerCase();
    document.querySelectorAll('.item').forEach(e=>{{
        e.style.display = e.innerText.toLowerCase().includes(val) ? '' : 'none';
    }});
}}
</script>

</body>
</html>
"""


# =========================
# MAIN HANDLER
# =========================
async def handle_txt2html(client: Client, message: Message):

    if not message.document or not message.document.file_name.endswith(".txt"):
        return await message.reply_text("Send TXT file")

    file_path = await message.download()
    file_name = message.document.file_name

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    urls = extract_names_and_urls(content)

    if not urls:
        return await message.reply_text("Invalid format")

    videos, pdfs, others = categorize_urls(urls)

    html = generate_html(file_name, videos, pdfs, others)

    out_file = file_name.replace(".txt", "@courses_hub2_bot.html")

    with open(out_file, "w", encoding="utf-8") as f:
        f.write(html)

    await message.reply_document(out_file)

    if CHANNEL_ID:
        await client.send_document(CHANNEL_ID, out_file)

    os.remove(file_path)
    os.remove(out_file)


# =========================
# HELP
# =========================
async def show_txt2html_help(client: Client, message: Message):
    await message.reply_text(
        "Format:\nFolder/Name: URL\n\nExample:\nMath/Video1: link"
    )
