import os, requests, json, random
from datetime import datetime
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# === CONFIG ===
FB_TOKEN = os.getenv("FB_TOKEN")
FB_PAGE_ID = os.getenv("FB_PAGE_ID")
FOOTBALL_KEY = os.getenv("FOOTBALL_API_KEY") or os.getenv("API_FOOTBALL_KEY")
NEWS_KEY = os.getenv("NEWS_API_KEY")  # Optional - if you have NewsAPI

ALLOWED_LEAGUE_IDS = {39: "Premier League", 140: "La Liga", 2: "Champions League", 3: "Europa League", 78: "Bundesliga", 135: "Serie A", 61: "Ligue 1"}
LINEUP_LEAGUE_IDS = [39, 140, 2]
POSTED_FILE = "posted.json"

def load_posted():
    try:
        with open(POSTED_FILE, "r") as f: return set(json.load(f))
    except: return set()

def save_posted(p):
    with open(POSTED_FILE, "w") as f: json.dump(list(p)[-800:], f)

# === IPHONE CLEAR IMAGE GENERATOR - NO BLACK SPACE ===
def create_match_image(home, away, league, score_text, home_logo_url, away_logo_url, status_type="KICKOFF"):
    # 1080x1080 - iPhone clear, no black bars
    W, H = 1080, 1080
    # Gradient background - dark premium
    bg = Image.new("RGB", (W, H), (10, 15, 25))
    draw = ImageDraw.Draw(bg)
    # Gradient effect
    for y in range(H):
        r = int(10 + y*0.08)
        g = int(15 + y*0.05)
        b = int(25 + y*0.1)
        draw.line([(0, y), (W, y)], fill=(r, g, b))
    
    # Download logos - high quality
    def get_logo(url):
        try:
            r = requests.get(url, timeout=10)
            logo = Image.open(BytesIO(r.content)).convert("RGBA")
            return logo.resize((320, 320), Image.LANCZOS)
        except:
            return Image.new("RGBA", (320, 320), (255,255,255,0))

    home_logo = get_logo(home_logo_url)
    away_logo = get_logo(away_logo_url)

    # Paste logos centered - NO BLACK SPACE - cover entire
    bg.paste(home_logo, (120, 300), home_logo)
    bg.paste(away_logo, (640, 300), away_logo)

    # VS text
    try: font_bold = ImageFont.truetype("arial.ttf", 80)
    except: font_bold = ImageFont.load_default()
    try: font_small = ImageFont.truetype("arial.ttf", 40)
    except: font_small = ImageFont.load_default()

    draw.text((W//2-40, 400), "VS", fill=(255,255,255), font=font_bold, anchor="mm")
    
    # Teams
    draw.text((280, 680), home[:15], fill="white", font=font_bold, anchor="mm")
    draw.text((800, 680), away[:15], fill="white", font=font_bold, anchor="mm")
    
    # Score / Status
    draw.text((W//2, 780), score_text, fill=(0, 255, 136), font=font_bold, anchor="mm")
    
    # League
    draw.text((W//2, 850), league, fill=(200,200,200), font=font_small, anchor="mm")

    # === POP UP Unfiltered Scores - Watermark ===
    # Semi-transparent banner bottom
    overlay = Image.new("RGBA", (W, 120), (0, 255, 136, 230))
    bg.paste(overlay, (0, H-120), overlay)
    draw = ImageDraw.Draw(bg)
    draw.text((W//2, H-60), "UNFILTERED SCORES • LIVE", fill="black", font=font_bold, anchor="mm")

    # Save high quality - iPhone clear
    path = f"/tmp/{home}_{away}.jpg"
    bg.save(path, "JPEG", quality=95, optimize=True)
    return path

def fb_post_with_image(message, image_path):
    url = f"https://graph.facebook.com/{FB_PAGE_ID}/photos"
    with open(image_path, "rb") as f:
        files = {"source": f}
        data = {"caption": message, "access_token": FB_TOKEN}
        r = requests.post(url, files=files, data=data, timeout=30)
        print(f"FB PHOTO POST: {r.status_code} {r.text[:200]}")
        return r

def fb_post_text(message):
    url = f"https://graph.facebook.com/{FB_PAGE_ID}/feed"
    data = {"message": message, "access_token": FB_TOKEN}
    r = requests.post(url, data=data, timeout=20)
    print(f"FB TEXT: {r.status_code}")
    return r

# === NEWS WITH IMAGE - NO REPETITION ===
def fetch_football_news():
    news_items = []
    # Try NewsAPI if key exists
    if NEWS_KEY:
        try:
            url = f"https://newsapi.org/v2/everything?q=football+Premier League&language=en&sortBy=publishedAt&pageSize=10&apiKey={NEWS_KEY}"
            r = requests.get(url, timeout=15).json()
            for art in r.get("articles", [])[:5]:
                if art.get("urlToImage"):
                    news_items.append({"title": art["title"], "image": art["urlToImage"], "url": art["url"]})
        except: pass
    
    # Fallback - BBC RSS style + ESPN images
    if not news_items:
        fallback = [
            {"title": "Transfer News Live: Big moves expected", "image": "https://images.unsplash.com/photo-1574629810360-214f3770f775?w=1080", "url": ""},
            {"title": "Premier League Form Guide", "image": "https://images.unsplash.com/photo-1431324155629-1a6deb1dec8d?w=1080", "url": ""},
        ]
        news_items = fallback
    return news_items

def create_news_image(title, news_image_url):
    W, H = 1080, 1080
    try:
        r = requests.get(news_image_url, timeout=10)
        bg = Image.open(BytesIO(r.content)).convert("RGB")
        # COVER - No black space - crop to fill
        bg = bg.resize((W, H), Image.LANCZOS)
        # Blur overlay for text readability
        overlay = Image.new("RGBA", (W, H), (0,0,0,100))
        bg = Image.alpha_composite(bg.convert("RGBA"), overlay).convert("RGB")
    except:
        bg = Image.new("RGB", (W, H), (10,15,25))

    draw = ImageDraw.Draw(bg)
    try: font = ImageFont.truetype("arial.ttf", 55)
    except: font = ImageFont.load_default()

    # Title wrapped
    words = title.split()
    lines = []
    line = ""
    for w in words:
        if len(line + " " + w) < 35: line += " " + w
        else: lines.append(line); line = w
    lines.append(line)
    
    y = 350
    for l in lines[:3]:
        draw.text((W//2, y), l.strip(), fill="white", font=font, anchor="mm", stroke_width=2, stroke_fill="black")
        y += 70

    # Unfiltered Scores pop up
    banner = Image.new("RGBA", (W, 120), (0, 255, 136, 230))
    bg.paste(banner, (0, H-120), banner)
    draw.text((W//2, H-60), "UNFILTERED SCORES", fill="black", font=font, anchor="mm")
    
    path = f"/tmp/news_{int(datetime.now().timestamp())}.jpg"
    bg.save(path, "JPEG", quality=95)
    return path

def main():
    posted = load_posted()
    # ... your existing fixture fetching code ...
    today = datetime.now().strftime("%Y-%m-%d")
    url = "https://v3.football.api-sports.io/fixtures"
    headers = {"x-apisports-key": FOOTBALL_KEY}
    params = {"date": today}
    try:
        r = requests.get(url, headers=headers, params=params, timeout=20)
        fixtures = r.json().get("response", [])
    except:
        fixtures = []

    for fx in fixtures:
        league_id = fx["league"]["id"]
        if league_id not in ALLOWED_LEAGUE_IDS: continue
        fixture_id = fx["fixture"]["id"]
        status = fx["fixture"]["status"]["short"]
        home = fx["teams"]["home"]["name"]
        away = fx["teams"]["away"]["name"]
        league_name = ALLOWED_LEAGUE_IDS[league_id]
        home_logo = fx["teams"]["home"]["logo"]
        away_logo = fx["teams"]["away"]["logo"]
        goals_h = fx["goals"]["home"]
        goals_a = fx["goals"]["away"]

        if status in ["1H", "HT", "2H"]:
            key = f"kickoff_{fixture_id}"
            if key in posted: continue
            img = create_match_image(home, away, league_name, f"{goals_h} - {goals_a}" if goals_h is not None else "LIVE", home_logo, away_logo, "KICKOFF")
            msg = f"🟢 ⚽ KICKOFF: {home} vs {away}\n{league_name} LIVE!\n\n#FootballLive #UnfilteredScores"
            fb_post_with_image(msg, img)
            posted.add(key); save_posted(posted)

    # === POST NEWS - 1 per run max, no repeat ===
    news_key = f"news_{today}_{datetime.now().hour}"
    if news_key not in posted:
        news_list = fetch_football_news()
        if news_list:
            n = random.choice(news_list)
            img = create_news_image(n["title"], n["image"])
            msg = f"🚨 {n['title']}\n\n#FootballNews #UnfilteredScores #EPL #LaLiga #UCL"
            fb_post_with_image(msg, img)
            posted.add(news_key); save_posted(posted)

if __name__ == "__main__":
    main()
