import os, requests, json, random, xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from concurrent.futures import ThreadPoolExecutor

FB_TOKEN = os.getenv("FB_TOKEN")
FB_PAGE_ID = os.getenv("FB_PAGE_ID")
FOOTBALL_KEY = os.getenv("FOOTBALL_API_KEY") or os.getenv("API_FOOTBALL_KEY")
MAX_API = int(os.getenv("MAX_API_REQUESTS", "95"))

POSTED_FILE = "posted.json"
COUNT_FILE = "/tmp/api_count.json"

# === ALL LEAGUES - MAIN + TOP EUROPEAN + AFRICAN ===
ALL_LEAGUES = {
    # Your original main
    39: "Premier League", 140: "La Liga", 2: "Champions League", 3: "Europa League", 78: "Bundesliga", 135: "Serie A", 61: "Ligue 1",
    # ADDED Top European
    88: "Eredivisie", 94: "Primeira Liga", 144: "Belgian Pro League", 40: "Championship", 79: "Bundesliga 2", 140: "La Liga", 531: "UEFA Conference",
    # African
    204: "Kenya FKF Premier", 202: "Tanzania Premier", 203: "Uganda Premier", 201: "Rwanda Premier", 233: "Egypt Premier", 235: "Morocco Botola", 236: "Algeria Ligue 1", 237: "Tunisia Ligue 1", 238: "South Africa PSL", 239: "Nigeria NPFL", 6: "CAF Champions League", 7: "CAF Confederation Cup", 400: "AFCON", 11: "Africa WC Qualifiers"
}

AFRICAN_IDS = [204, 202, 203, 201, 233, 235, 236, 237, 238, 239, 6, 7, 400, 11]
EUROPEAN_IDS = [39, 140, 2, 3, 78, 135, 61, 88, 94, 144, 40, 531]

def load_posted():
    try:
        with open(POSTED_FILE, "r") as f: return set(json.load(f))
    except: return set()
def save_posted(p):
    with open(POSTED_FILE, "w") as f: json.dump(list(p)[-1000:], f)
def get_api_count():
    try:
        with open(COUNT_FILE, "r") as f:
            d = json.load(f)
            if d["date"] == datetime.now().strftime("%Y-%m-%d"): return d["count"]
            return 0
    except: return 0
def save_api_count(c):
    with open(COUNT_FILE, "w") as f: json.dump({"date": datetime.now().strftime("%Y-%m-%d"), "count": c}, f)

# === IMAGE GENERATOR - IPHONE CLEAR NO BLACK SPACE + POPUP ===
def create_image(home, away, league, score_text, home_logo, away_logo, state="LIVE"):
    W, H = 1080, 1080
    bg = Image.new("RGB", (W, H), (10,15,25))
    draw = ImageDraw.Draw(bg)
    for y in range(H): draw.line([(0,y),(W,y)], fill=(int(10+y*0.08), int(15+y*0.05), int(25+y*0.1)))
    def get_logo(url):
        try:
            r = requests.get(url, timeout=10)
            logo = Image.open(BytesIO(r.content)).convert("RGBA")
            return logo.resize((340,340), Image.LANCZOS)
        except: return Image.new("RGBA", (340,340), (0,0,0,0))
    hl = get_logo(home_logo); al = get_logo(away_logo)
    bg.paste(hl, (110, 280), hl); bg.paste(al, (630, 280), al)
    try: fb = ImageFont.truetype("arial.ttf", 80)
    except: fb = ImageFont.load_default()
    try: fs = ImageFont.truetype("arial.ttf", 38)
    except: fs = ImageFont.load_default()
    try: fsmall = ImageFont.truetype("arial.ttf", 32)
    except: fsmall = ImageFont.load_default()
    
    draw.text((W//2, 420), "VS", fill="white", font=fb, anchor="mm")
    draw.text((280, 680), home[:15], fill="white", font=fb, anchor="mm")
    draw.text((800, 680), away[:15], fill="white", font=fb, anchor="mm")
    draw.text((W//2, 780), score_text, fill=(0,255,136), font=fb, anchor="mm")
    draw.text((W//2, 850), league, fill=(200,200,200), font=fs, anchor="mm")
    draw.text((W//2, 900), state, fill=(255,215,0), font=fsmall, anchor="mm")
    overlay = Image.new("RGBA", (W, 130), (0, 255, 136, 235))
    bg.paste(overlay, (0, H-130), overlay)
    draw.text((W//2, H-65), "UNFILTERED SCORES", fill="black", font=fb, anchor="mm")
    path = f"/tmp/{home}_{away}_{state}.jpg"
    bg.save(path, "JPEG", quality=95, optimize=True)
    return path

def fb_photo(msg, img_path):
    url = f"https://graph.facebook.com/{FB_PAGE_ID}/photos"
    with open(img_path, "rb") as fp:
        r = requests.post(url, files={"source": fp}, data={"caption": msg, "access_token": FB_TOKEN}, timeout=30)
        print(f"FB {r.status_code} {msg[:60]}")
        return r

# === NEWS RSS - NO API KEY NEEDED - ALL SOURCES ===
RSS_FEEDS = [
    "http://feeds.bbci.co.uk/sport/football/rss.xml",
    "https://www.espn.com/espn/rss/soccer/news",
    "https://feeds.skynews.com/feeds/rss/sports.xml",
    "https://rss.app/en/rss-feed/african-football-news"
]

def fetch_news_rss():
    items=[]
    for feed_url in RSS_FEEDS:
        try:
            r = requests.get(feed_url, timeout=12)
            root = ET.fromstring(r.content)
            for item in root.findall(".//item")[:5]:
                title = item.findtext("title", "")
                link = item.findtext("link", "")
                # Try find image in enclosure or media
                enclosure = item.find("enclosure")
                img = enclosure.get("url") if enclosure is not None else ""
                if not img:
                    # Try media:content
                    for ns in ["{http://search.yahoo.com/mrss/}content", "media:content"]:
                        m = item.find(ns)
                        if m is not None: img = m.get("url","")
                if not img: img = f"https://images.unsplash.com/photo-1574629810360-214f3770f775?w=1080&random={random.randint(1,100)}"
                if title: items.append({"title": title[:120], "image": img, "link": link})
        except Exception as e:
            print(f"RSS {feed_url} error {e}")
            continue
    print(f"RSS fetched {len(items)} news")
    return items

def create_news_image_rss(title, img_url):
    W,H=1080,1080
    try:
        r=requests.get(img_url, timeout=10)
        bg=Image.open(BytesIO(r.content)).convert("RGB")
        bg=bg.resize((W,H), Image.LANCZOS)
        dark=Image.new("RGBA", (W,H), (0,0,0,120))
        bg=Image.alpha_composite(bg.convert("RGBA"), dark).convert("RGB")
    except: bg=Image.new("RGB", (W,H), (10,15,25))
    draw=ImageDraw.Draw(bg)
    try: f=ImageFont.truetype("arial.ttf", 50)
    except: f=ImageFont.load_default()
    words=title.split(); lines=[]; line=""
    for w in words:
        if len(line+" "+w)<30: line+=" "+w
        else: lines.append(line); line=w
    lines.append(line)
    y=360
    for l in lines[:4]:
        draw.text((W//2, y), l.strip(), fill="white", font=f, anchor="mm", stroke_width=3, stroke_fill="black")
        y+=70
    banner=Image.new("RGBA", (W, 130), (0,255,136,230))
    bg.paste(banner, (0, H-130), banner)
    draw.text((W//2, H-65), "UNFILTERED SCORES", fill="black", font=f, anchor="mm")
    path=f"/tmp/rss_{int(datetime.now().timestamp())}.jpg"
    bg.save(path, "JPEG", quality=95)
    return path

# === PARALLEL FETCH - AFRICAN API + LIVESCORES AT SAME TIME ===
def fetch_european_livescore():
    games=[]
    espn_map={"eng.1":39, "esp.1":140, "uefa.champions":2, "uefa.europa":3, "ger.1":78, "ita.1":135, "fra.1":61, "ned.1":88, "por.1":94, "bel.1":144, "eng.2":40}
    for code, lid in espn_map.items():
        try:
            r=requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{code}/scoreboard", timeout=12).json()
            for ev in r.get("events", []):
                comp=ev["competitions"][0]
                status_short=comp["status"]["type"]["state"] # pre, in, post
                status_detail=comp["status"]["type"]["detail"]
                games.append({"league_id": lid, "home": comp["competitors"][0]["team"]["displayName"], "away": comp["competitors"][1]["team"]["displayName"], "status_state": status_short, "status_detail": status_detail, "home_logo": comp["competitors"][0]["team"].get("logo",""), "away_logo": comp["competitors"][1]["team"].get("logo",""), "score": f"{comp['competitors'][0].get('score','0')}-{comp['competitors'][1].get('score','0')}", "source": "espn"})
        except: continue
    print(f"European Livescore {len(games)} games FREE")
    return games

def fetch_african_api_parallel():
    used=get_api_count()
    if used>=MAX_API:
        print(f"🛑 API {used}/{MAX_API} OVER - African using cache/livescore")
        return []
    try:
        today=datetime.now().strftime("%Y-%m-%d")
        r=requests.get("https://v3.football.api-sports.io/fixtures", headers={"x-apisports-key": FOOTBALL_KEY}, params={"date": today}, timeout=20)
        save_api_count(used+1)
        print(f"African API {used+1}/{MAX_API} remaining {r.headers.get('x-ratelimit-requests-remaining')}")
        data=[]
        for fx in r.json().get("response", []):
            if fx["league"]["id"] in AFRICAN_IDS or fx["league"]["id"] in ALL_LEAGUES:
                if fx["league"]["id"] in AFRICAN_IDS:
                    data.append(fx)
        return data
    except Exception as e:
        print(f"African API error {e}")
        return []

def main():
    posted=load_posted()
    print("=== V53 PERFECT START - PARALLEL ===")
    
    # RUN BOTH AT SAME TIME
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_euro = executor.submit(fetch_european_livescore)
        future_african = executor.submit(fetch_african_api_parallel)
        euro_games = future_euro.result()
        african_games = future_african.result()

    # === TRACK FROM LINEUP TO FT ===
    # EUROPEAN TRACKING
    for g in euro_games:
        if g["league_id"] not in ALL_LEAGUES: continue
        base_key = f"{g['home']}_{g['away']}"
        state = g["status_state"] # pre, in, post
        detail = g["status_detail"]
        
        # 1. LINEUP - 60 min before
        if state=="pre" and "lineup" in detail.lower() or state=="pre":
            key=f"lineup_{base_key}"
            if key in posted: continue
            # Only big leagues lineup like you wanted
            if g["league_id"] in [39,140,2]:
                img=create_image(g["home"], g["away"], ALL_LEAGUES[g["league_id"]], "LINEUPS OUT", g["home_logo"], g["away_logo"], "LINEUP")
                fb_photo(f"📋 LINEUPS: {g['home']} vs {g['away']}\n{ALL_LEAGUES[g['league_id']]}\nKickoff soon! Predict score 👇\n\n#Lineup #UnfilteredScores", img)
                posted.add(key); save_posted(posted)
        
        # 2. KICKOFF
        elif state=="in" and "0'" in detail or "1st" in detail:
            key=f"kickoff_{base_key}"
            if key in posted: continue
            img=create_image(g["home"], g["away"], ALL_LEAGUES[g["league_id"]], "KICKOFF", g["home_logo"], g["away_logo"], "KICKOFF")
            fb_photo(f"🟢 KICKOFF: {g['home']} vs {g['away']}\n{ALL_LEAGUES[g['league_id']]} LIVE!\n\n#Live #UnfilteredScores", img)
            posted.add(key); save_posted(posted)
        
        # 3. LIVE / HT / FT
        elif state=="in":
            key=f"live_{base_key}_{detail}"
            if key in posted: continue
            img=create_image(g["home"], g["away"], ALL_LEAGUES[g["league_id"]], g["score"], g["home_logo"], g["away_logo"], detail.upper())
            fb_photo(f"⚽ {detail}: {g['home']} {g['score']} {g['away']}\n{ALL_LEAGUES[g['league_id']]}\n\n#FootballLive #UnfilteredScores", img)
            posted.add(key); save_posted(posted)
        
        elif state=="post":
            key=f"ft_{base_key}"
            if key in posted: continue
            img=create_image(g["home"], g["away"], ALL_LEAGUES[g["league_id"]], g["score"], g["home_logo"], g["away_logo"], "FULL TIME")
            fb_photo(f"✅ FT: {g['home']} {g['score']} {g['away']}\n{ALL_LEAGUES[g['league_id']]}\n\n#FullTime #UnfilteredScores", img)
            posted.add(key); save_posted(posted)

    # AFRICAN TRACKING - API
    for fx in african_games:
        fid=fx["fixture"]["id"]
        status=fx["fixture"]["status"]["short"]
        home=fx["teams"]["home"]["name"]; away=fx["teams"]["away"]["name"]
        league=ALL_LEAGUES.get(fx["league"]["id"], "African Football")
        
        # LINEUP -> FT TRACKING
        if status=="NS":
            # Check if lineup available - API needs extra call (1 request) - we do for African only
            key=f"af_lineup_{fid}"
            if key not in posted and get_api_count()<MAX_API:
                try:
                    r=requests.get("https://v3.football.api-sports.io/fixtures/lineups", headers={"x-apisports-key": FOOTBALL_KEY}, params={"fixture": fid}, timeout=10)
                    save_api_count(get_api_count()+1)
                    if r.json().get("response"):
                        img=create_image(home, away, league, "LINEUPS CONFIRMED", fx["teams"]["home"]["logo"], fx["teams"]["away"]["logo"], "LINEUP")
                        fb_photo(f"📋 AFRICAN LINEUP: {home} vs {away}\n{league}\n\n#AfricanFootball #UnfilteredScores", img)
                        posted.add(key); save_posted(posted)
                except: pass
        elif status in ["1H","2H","ET","LIVE"]:
            key=f"af_live_{fid}_{status}_{fx['goals']['home']}_{fx['goals']['away']}"
            if key in posted: continue
            img=create_image(home, away, league, f"{fx['goals']['home']}-{fx['goals']['away']}", fx["teams"]["home"]["logo"], fx["teams"]["away"]["logo"], "LIVE")
            fb_photo(f"🌍 LIVE AFRICA: {home} {fx['goals']['home']}-{fx['goals']['away']} {away}\n{league}\n\n#AfricanFootball #UnfilteredScores", img)
            posted.add(key); save_posted(posted)
        elif status in ["FT","AET","PEN"]:
            key=f"af_ft_{fid}"
            if key in posted: continue
            img=create_image(home, away, league, f"{fx['goals']['home']}-{fx['goals']['away']}", fx["teams"]["home"]["logo"], fx["teams"]["away"]["logo"], "FULL TIME")
            fb_photo(f"✅ FT AFRICA: {home} {fx['goals']['home']}-{fx['goals']['away']} {away}\n{league}\n\n#FT #UnfilteredScores", img)
            posted.add(key); save_posted(posted)

    # === NEWS RSS ===
    news_key=f"news_{datetime.now().strftime('%Y-%m-%d_%H')}"
    if news_key not in posted:
        news=fetch_news_rss()
        if news:
            n=random.choice(news)
            img=create_news_image_rss(n["title"], n["image"])
            fb_photo(f"🚨 {n['title']}\n\nRead more: {n['link']}\n\n#FootballNews #UnfilteredScores", img)
            posted.add(news_key); save_posted(posted)

    print("V53 PERFECT DONE")

if __name__=="__main__":
    main()
