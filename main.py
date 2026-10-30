import os, requests, json, random, xml.etree.ElementTree as ET
from datetime import datetime
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from concurrent.futures import ThreadPoolExecutor

# === FIXED TOKENS - SUPPORT ALL NAMES + HARDCODED PAGE ID ===
FB_TOKEN = os.getenv("FB_TOKEN") or os.getenv("FB_PAGE_ACCESS_TOKEN") or os.getenv("FB_PAGE_TOKEN")
FB_PAGE_ID = os.getenv("FB_PAGE_ID") or os.getenv("PAGE_ID") or "1293090263895541"
if not FB_PAGE_ID or FB_PAGE_ID.strip() == "0" or len(FB_PAGE_ID.strip()) < 5:
    FB_PAGE_ID = "1293090263895541"

FOOTBALL_KEY = os.getenv("FOOTBALL_API_KEY") or os.getenv("API_FOOTBALL_KEY")
MAX_API = int(os.getenv("MAX_API_REQUESTS", "95"))

POSTED_FILE = "posted.json"
COUNT_FILE = "/tmp/api_count.json"

ALL_LEAGUES = {
    39: "Premier League", 140: "La Liga", 2: "Champions League", 3: "Europa League", 78: "Bundesliga", 135: "Serie A", 61: "Ligue 1",
    88: "Eredivisie", 94: "Primeira Liga", 144: "Belgian Pro League", 40: "Championship", 79: "Bundesliga 2", 531: "UEFA Conference",
    204: "Kenya FKF Premier", 202: "Tanzania Premier", 203: "Uganda Premier", 201: "Rwanda Premier", 233: "Egypt Premier", 235: "Morocco Botola", 236: "Algeria Ligue 1", 237: "Tunisia Ligue 1", 238: "South Africa PSL", 239: "Nigeria NPFL", 6: "CAF Champions League", 7: "CAF Confederation Cup", 400: "AFCON", 11: "Africa WC Qualifiers"
}
AFRICAN_IDS = [204, 202, 203, 201, 233, 235, 236, 237, 238, 239, 6, 7, 400, 11]

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

# === TEXT POST FOR SCORES - NO PICTURE ===
def fb_text(msg):
    url = f"https://graph.facebook.com/v20.0/{FB_PAGE_ID}/feed"
    r = requests.post(url, data={"message": msg, "access_token": FB_TOKEN}, timeout=30)
    print(f"FB TEXT {r.status_code} {msg[:80]}")
    print(f"FB Resp: {r.text[:400]}")
    return r

# === PHOTO POST FOR NEWS ONLY - CLEAR REAL PHOTO ===
def fb_photo(msg, img_path):
    url = f"https://graph.facebook.com/v20.0/{FB_PAGE_ID}/photos"
    with open(img_path, "rb") as fp:
        r = requests.post(url, files={"source": fp}, data={"caption": msg, "access_token": FB_TOKEN}, timeout=30)
        print(f"FB PHOTO {r.status_code} {msg[:80]}")
        print(f"FB Resp: {r.text[:400]}")
        return r

RSS_FEEDS = [
    "http://feeds.bbci.co.uk/sport/football/rss.xml",
    "https://www.espn.com/espn/rss/soccer/news",
]

def fetch_news_rss():
    items=[]
    for feed_url in RSS_FEEDS:
        try:
            r = requests.get(feed_url, timeout=12)
            root = ET.fromstring(r.content)
            for item in root.findall(".//item")[:8]:
                title = item.findtext("title", "").strip()
                if not title or len(title) < 15: continue
                # Try get real image
                img = ""
                enc = item.find("enclosure")
                if enc is not None: img = enc.get("url","")
                if not img:
                    m = item.find("{http://search.yahoo.com/mrss/}content")
                    if m is not None: img = m.get("url","")
                if not img or "bbc" in img.lower() or "logo" in img.lower():
                    # Fallback to high quality football image
                    img = f"https://images.unsplash.com/photo-1579952363873-27d3bfad9c0d?w=1080&h=1350&fit=crop&q=90&auto=format&random={random.randint(1,5000)}"
                items.append({"title": title[:150], "image": img})
        except Exception as e:
            print(f"RSS {feed_url} error {e}")
            continue
    print(f"RSS fetched {len(items)} news")
    return items

def create_news_image_clear(title, img_url):
    W,H=1080,1350
    try:
        r=requests.get(img_url, timeout=15)
        bg=Image.open(BytesIO(r.content)).convert("RGB")
        # Center crop top focus (for faces)
        w,h = bg.size
        min_side = min(w,h)
        left = (w-min_side)//2
        top = max(0, (h-min_side)//3)
        bg = bg.crop((left, top, left+min_side, top+min_side))
        bg = bg.resize((W,H), Image.LANCZOS)
        bg = ImageEnhance.Brightness(bg).enhance(1.18)
        bg = ImageEnhance.Color(bg).enhance(1.25)
        bg = ImageEnhance.Contrast(bg).enhance(1.1)
    except Exception as e:
        print(f"News img fail {e}")
        bg=Image.new("RGB", (W,H), (15,25,45))
    
    draw=ImageDraw.Draw(bg, "RGBA")
    # Only bottom 45% dark gradient - keep top clear!
    for y in range(int(H*0.55), H):
        alpha = int((y - H*0.55) / (H*0.45) * 210)
        draw.rectangle([(0,y),(W,y+2)], fill=(0,0,0,alpha))
    
    try:
        font_big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 56)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 34)
    except:
        font_big = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Word wrap big text
    words=title.split()
    lines=[]; line=""
    for w in words:
        if len(line+" "+w) < 30:
            line=(line+" "+w).strip()
        else:
            lines.append(line)
            line=w
    if line: lines.append(line)
    lines=lines[:4]

    y = H - 300 - len(lines)*75
    for l in lines:
        draw.text((W//2, y), l, fill="white", font=font_big, anchor="mm", stroke_width=5, stroke_fill="black")
        y+=75
    
    # Brand banner
    draw.rectangle([(0, H-110),(W,H)], fill=(0,255,136,255))
    draw.text((W//2, H-55), "UNFILTERED SCORES", fill="black", font=font_small, anchor="mm")
    
    path=f"/tmp/news_{int(datetime.now().timestamp())}.jpg"
    bg.save(path, "JPEG", quality=98, optimize=True)
    return path

def fetch_european_livescore():
    games=[]
    espn_map={"eng.1":39, "esp.1":140, "uefa.champions":2, "uefa.europa":3, "ger.1":78, "ita.1":135, "fra.1":61, "ned.1":88, "por.1":94, "bel.1":144, "eng.2":40}
    for code, lid in espn_map.items():
        try:
            r=requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{code}/scoreboard", timeout=12).json()
            for ev in r.get("events", []):
                comp=ev["competitions"][0]
                games.append({"league_id": lid, "home": comp["competitors"][0]["team"]["displayName"], "away": comp["competitors"][1]["team"]["displayName"], "status_state": comp["status"]["type"]["state"], "status_detail": comp["status"]["type"]["detail"], "score": f"{comp['competitors'][0].get('score','0')}-{comp['competitors'][1].get('score','0')}", "date": ev.get("date","")[:10]})
        except: continue
    print(f"Euro FREE {len(games)} games")
    return games

def fetch_african_api_parallel():
    used=get_api_count()
    if used>=MAX_API: return []
    try:
        today=datetime.now().strftime("%Y-%m-%d")
        r=requests.get("https://v3.football.api-sports.io/fixtures", headers={"x-apisports-key": FOOTBALL_KEY}, params={"date": today}, timeout=20)
        save_api_count(used+1)
        data=[fx for fx in r.json().get("response", []) if fx["league"]["id"] in AFRICAN_IDS]
        print(f"African API {used+1}/{MAX_API} -> {len(data)}")
        return data
    except Exception as e:
        print(f"African API error {e}")
        return []

def main():
    posted=load_posted()
    print(f"=== V55 TEXT SCORES + CLEAR NEWS NO LINK === PAGE {FB_PAGE_ID} TOKEN {'YES' if FB_TOKEN else 'NO'}")
    
    with ThreadPoolExecutor(max_workers=2) as ex:
        euro_games = ex.submit(fetch_european_livescore).result()
        african_games = ex.submit(fetch_african_api_parallel).result()

    today_utc = datetime.utcnow().strftime("%Y-%m-%d")
    euro_games = [g for g in euro_games if g.get("date","")==today_utc or g["status_state"]=="in" or g.get("date","")==""]

    for g in euro_games:
        if g["league_id"] not in ALL_LEAGUES: continue
        base_key = f"{g['home']}_{g['away']}"
        state = g["status_state"]
        detail = g["status_detail"]
        league = ALL_LEAGUES[g["league_id"]]
        
        if state=="pre":
            key=f"lineup_{base_key}"
            if key in posted: continue
            if g["league_id"] in [39,140,2]:
                fb_text(f"📋 LINEUPS: {g['home']} vs {g['away']}\n🏆 {league}\n⏰ Kickoff soon!\n\nPredict score 👇\n\n#Lineup #UnfilteredScores")
                posted.add(key); save_posted(posted)
        elif state=="in" and ("0'" in detail or "1st" in detail):
            key=f"kickoff_{base_key}"
            if key in posted: continue
            fb_text(f"🟢 KICKOFF!\n\n{g['home']} vs {g['away']}\n🏆 {league}\n⚽ LIVE NOW!\n\n#Live #UnfilteredScores")
            posted.add(key); save_posted(posted)
        elif state=="in":
            key=f"live_{base_key}_{detail}"
            if key in posted: continue
            fb_text(f"⚽ {detail}: {g['home']} {g['score']} {g['away']}\n🏆 {league}\n\n#FootballLive #UnfilteredScores")
            posted.add(key); save_posted(posted)
        elif state=="post":
            if g.get("date","") and g.get("date","") != today_utc: continue
            key=f"ft_{base_key}"
            if key in posted: continue
            fb_text(f"✅ FULL TIME: {g['home']} {g['score']} {g['away']}\n🏆 {league}\n\nThoughts? 👇\n\n#FullTime #UnfilteredScores")
            posted.add(key); save_posted(posted)

    for fx in african_games:
        fid=fx["fixture"]["id"]
        status=fx["fixture"]["status"]["short"]
        home=fx["teams"]["home"]["name"]; away=fx["teams"]["away"]["name"]
        league=ALL_LEAGUES.get(fx["league"]["id"], "African Football")
        if fx["fixture"]["date"][:10] != datetime.now().strftime("%Y-%m-%d"): continue
        
        if status=="NS":
            key=f"af_lineup_{fid}"
            if key not in posted and get_api_count()<MAX_API:
                try:
                    r=requests.get("https://v3.football.api-sports.io/fixtures/lineups", headers={"x-apisports-key": FOOTBALL_KEY}, params={"fixture": fid}, timeout=10)
                    save_api_count(get_api_count()+1)
                    if r.json().get("response"):
                        fb_text(f"📋 LINEUP AFRICA: {home} vs {away}\n🏆 {league}\n\n#AfricanFootball #UnfilteredScores")
                        posted.add(key); save_posted(posted)
                except: pass
        elif status in ["1H","2H","ET","LIVE"]:
            key=f"af_live_{fid}_{status}_{fx['goals']['home']}_{fx['goals']['away']}"
            if key in posted: continue
            fb_text(f"🌍 LIVE AFRICA: {home} {fx['goals']['home']}-{fx['goals']['away']} {away}\n🏆 {league}\n\n#Live #UnfilteredScores")
            posted.add(key); save_posted(posted)
        elif status in ["FT","AET","PEN"]:
            key=f"af_ft_{fid}"
            if key in posted: continue
            fb_text(f"✅ FT AFRICA: {home} {fx['goals']['home']}-{fx['goals']['away']} {away}\n🏆 {league}\n\n#FT #UnfilteredScores")
            posted.add(key); save_posted(posted)

    news_key=f"news_{datetime.now().strftime('%Y-%m-%d_%H')}"
    if news_key not in posted:
        news=fetch_news_rss()
        if news:
            n=random.choice(news)
            img_path=create_news_image_clear(n["title"], n["image"])
            # NO LINK - ONLY TITLE + HASHTAGS
            fb_photo(f"🚨 {n['title']}\n\n#FootballNews #UnfilteredScores #BreakingNews", img_path)
            posted.add(news_key); save_posted(posted)

    print("V55 DONE")

if __name__=="__main__":
    main()
