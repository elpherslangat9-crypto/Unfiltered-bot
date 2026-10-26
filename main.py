import requests
import json
import os
import time
import random
from datetime import datetime
from flask import Flask
import threading

# --- FAKE WEB SERVER FOR RENDER FREE TIER (DO NOT DELETE) ---
app = Flask(__name__)
@app.route('/')
def home():
    return "🟢 Unfiltered Football Bot is LIVE! - African Leagues + Big Leagues"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_web, daemon=True).start()
# --- END WEB SERVER ---

# --- YOUR BRAND 🟢 ---
BRAND = "🟢 Unfiltered Football"

# --- KEYS FROM RENDER ---
PAGE_ID = os.getenv("PAGE_ID")
PAGE_TOKEN = os.getenv("PAGE_TOKEN")
FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY")
LAST_FILE = "last_scores.json"
REQUEST_FILE = "requests_today.json"

# --- 13 AFRICAN LEAGUES - NEVER MISS! ---
AFRICAN_LEAGUES = {
    525: {"name": "Linafoot DRC 🇨🇩", "lang": "congo", "tags": "#Linafoot #RDC #FootRDC #LinafootRDC #VitaClub #TPMazembe #Lupopo #CongoFootball #Kinshasa #Ligue1RDC"},
    332: {"name": "KPL Kenya 🇰🇪", "lang": "kenya", "tags": "#KPL #KenyaPremierLeague #FKFPL #GorMahia #AFCLeopards #KenyaFootball #Nairobi #HarambeeStars #KPLLive #Kenyans"},
    378: {"name": "NBC Tanzania 🇹🇿", "lang": "swahili", "tags": "#NBCPremierLeague #LigiKuu #SimbaSC #YangaSC #TanzaniaFootball #DarEsSalaam #LigiKuuTanzania #AzamFC"},
    390: {"name": "UPL Uganda 🇺🇬", "lang": "english", "tags": "#UPL #UgandaPremierLeague #VipersSC #KCCA #SCVilla #UgandaFootball #Kampala #StarTimesUPL"},
    288: {"name": "PSL South Africa 🇿🇦", "lang": "english", "tags": "#PSL #DStvPrem #KaizerChiefs #OrlandoPirates #MamelodiSundowns #SouthAfrica #Bafana #PSLLive"},
    393: {"name": "Zambia Super League 🇿🇲", "lang": "english", "tags": "#ZambiaSuperLeague #ZPL #ZambiaFootball #ZescoUnited #PowerDynamos #Lusaka"},
    200: {"name": "Botola Morocco 🇲🇦", "lang": "french", "tags": "#Botola #BotolaPro #Wydad #RajaCasablanca #MoroccoFootball #Maroc"},
    233: {"name": "Egypt Premier 🇪🇬", "lang": "english", "tags": "#EgyptianPremierLeague #AlAhly #Zamalek #EgyptFootball #Cairo"},
    341: {"name": "Nigeria NPFL 🇳🇬", "lang": "english", "tags": "#NPFL #NigeriaPremierLeague #Enyimba #KanoPillars #NaijaFootball #Lagos"},
    235: {"name": "Algeria Ligue 1 🇩🇿", "lang": "french", "tags": "#Ligue1Algeria #AlgeriaFootball #MCA #USMA #Alger"},
    323: {"name": "Ghana Premier 🇬🇭", "lang": "english", "tags": "#GhanaPremierLeague #GPL #HeartsOfOak #Kotoko #GhanaFootball"},
    12: {"name": "CAF Champions League 🏆", "lang": "english", "tags": "#CAFCL #CAFChampionsLeague #TotalEnergiesCAFCL #AfricanFootball"},
    14: {"name": "CAF Confederation Cup", "lang": "english", "tags": "#CAFCC #CAFConfederationCup #Africa"},
}

CONGO_CAPS = [
    "BUUUUT! ⚽ {p} a tiye na {s} {m}'",
    "Tshibiiii ya goal! {p} vient de marquer! {s} {m}' 🔥",
    "GOAL na Linafoot! {p} {s} {m}' - Bino bozali wapi?",
    "Eeeeeh! {p} a bimisi {s}! {l} {m}'",
    "MOKONZI A TIE! {p} {s} {m}' 🇨🇩🔥"
]
SWAHILI_CAPS = [
    "GOLI! ⚽ {p} ameifunga! {s} {m}'",
    "WAMEFUNGWA! {p} {s} - {l} {m}'",
    "BAO! {p} kaweka {s} {m}' 🔥",
    "Imekwisha! {p} amefunga {s} {m}'",
    "Goli la dakika ya {m}'! {p} {s}"
]
ENGLISH_CAPS = [
    "GOAL! {p} scores! {s} {m}' ⚽🔥",
    "What a goal! {p} {s} - {l} {m}'",
    "BOOM! {p} {s} {m}'",
    "Goal alert! {p} makes it {s} {m}'"
]
FRENCH_CAPS = [
    "BUT! {p} marque! {s} {m}' ⚽",
    "Goal! {p} {s} - {l} {m}' 🔥",
    "Incroyable! {p} vient de marquer {s} {m}'"
]

def load_last():
    try:
        with open(LAST_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_last(data):
    with open(LAST_FILE, "w") as f:
        json.dump(data, f)

def get_request_count():
    try:
        with open(REQUEST_FILE, "r") as f:
            data = json.load(f)
            if data.get("date") != datetime.now().strftime("%Y-%m-%d"):
                return 0
            return data.get("count", 0)
    except:
        return 0

def increment_request():
    count = get_request_count() + 1
    with open(REQUEST_FILE, "w") as f:
        json.dump({"date": datetime.now().strftime("%Y-%m-%d"), "count": count}, f)
    print(f"📊 API Requests today: {count}/100")
    return count

def post_fb(message, tags):
    if not PAGE_ID or not PAGE_TOKEN:
        print("❌ Missing PAGE_ID or PAGE_TOKEN in Render!")
        return False
    viral_extra = " #FootballLive #LiveScore #GoalAlert #AfricanFootball #UnfilteredFootball #FYP #FootballAfrica #Live"
    # --- BRAND 🟢 ADDED AT START OF EVERY POST ---
    full_message = f"{BRAND}\n\n{message}\n\n{tags}{viral_extra}"
    try:
        url = f"https://graph.facebook.com/{PAGE_ID}/feed"
        data = {"message": full_message, "access_token": PAGE_TOKEN}
        r = requests.post(url, data=data, timeout=20).json()
        if "id" in r:
            print(f"✅ POSTED: {message[:60]}...")
            return True
        else:
            print(f"❌ FB FAILED: {r}")
            return False
    except Exception as e:
        print(f"❌ FB Error: {e}")
        return False

def check_african_leagues():
    print(f"\n--- Checking African leagues {datetime.now()} ---")
    if not FOOTBALL_API_KEY:
        print("❌ No FOOTBALL_API_KEY found in Render! Add it!")
        return
    last = load_last()
    headers = {"x-apisports-key": FOOTBALL_API_KEY}
    try:
        url = "https://v3.football.api-sports.io/fixtures?live=all"
        response = requests.get(url, headers=headers, timeout=20)
        increment_request()
        data = response.json()
        found = 0
        for fx in data.get("response", []):
            league_id = fx["league"]["id"]
            if league_id not in AFRICAN_LEAGUES:
                continue
            found += 1
            fixture_id = str(fx["fixture"]["id"])
            home_goals = fx["goals"]["home"]
            away_goals = fx["goals"]["away"]
            if home_goals is None or away_goals is None:
                continue
            current_score = f"{home_goals}-{away_goals}"
            if last.get(fixture_id) == current_score:
                continue
            if last.get(fixture_id):
                minute = fx["fixture"]["status"]["elapsed"]
                if minute is None:
                    minute = "Live"
                home_team = fx["teams"]["home"]["name"]
                away_team = fx["teams"]["away"]["name"]
                scorer_name = home_team
                try:
                    event_url = f"https://v3.football.api-sports.io/fixtures/events?fixture={fixture_id}"
                    event_res = requests.get(event_url, headers=headers, timeout=10).json()
                    increment_request()
                    events = event_res.get("response", [])
                    for ev in reversed(events):
                        if ev["type"] == "Goal":
                            scorer_name = ev["player"]["name"]
                            break
                except Exception as e:
                    print(f"Could not get scorer: {e}")
                info = AFRICAN_LEAGUES[league_id]
                lang = info["lang"]
                if lang == "congo":
                    template = random.choice(CONGO_CAPS)
                elif lang == "swahili":
                    template = random.choice(SWAHILI_CAPS)
                elif lang == "kenya":
                    if random.random() < 0.8:
                        template = random.choice(ENGLISH_CAPS)
                    else:
                        template = random.choice(SWAHILI_CAPS)
                elif lang == "french":
                    template = random.choice(FRENCH_CAPS)
                else:
                    template = random.choice(ENGLISH_CAPS)
                msg = template.format(p=scorer_name, s=f"{home_team} {home_goals}-{away_goals} {away_team}", m=minute, l=info["name"])
                msg = msg + f"\n\n{info['name']} | {minute}'"
                post_fb(msg, info["tags"])
            last[fixture_id] = current_score
            save_last(last)
        print(f"Found {found} African live games")
    except Exception as e:
        print(f"African check error: {e}")

def check_big_leagues_free():
    print("--- Checking Big leagues FREE (No API count) ---")
    last = load_last()
    espn_leagues = {
        "eng.1": "Premier League",
        "esp.1": "La Liga",
        "ita.1": "Serie A",
        "ger.1": "Bundesliga",
        "uefa.champions": "Champions League"
    }
    for esp_id, league_name in espn_leagues.items():
        try:
            url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{esp_id}/scoreboard"
            res = requests.get(url, timeout=15).json()
            for event in res.get("events", []):
                state = event["status"]["type"]["state"]
                if state != "in":
                    continue
                fixture_id = event["id"]
                comp = event["competitions"][0]
                home_team = comp["competitors"][0]["team"]["displayName"]
                away_team = comp["competitors"][1]["team"]["displayName"]
                home_goals = int(comp["competitors"][0]["score"])
                away_goals = int(comp["competitors"][1]["score"])
                current_score = f"{home_goals}-{away_goals}"
                if last.get(fixture_id) == current_score:
                    continue
                if last.get(fixture_id):
                    minute = event["status"]["displayClock"]
                    scorer = f"{home_team} player"
                    msg_template = random.choice(ENGLISH_CAPS)
                    msg = msg_template.format(p=scorer, s=f"{home_team} {home_goals}-{away_goals} {away_team}", m=minute, l=league_name)
                    msg = msg + f"\n\n{league_name} | {minute}"
                    tags = f"#{league_name.replace(' ', '')} #Football #LiveScore"
                    post_fb(msg, tags)
                last[fixture_id] = current_score
                save_last(last)
        except Exception as e:
            print(f"Big league {esp_id} error: {e}")

if __name__ == "__main__":
    print("🔥 V8 PERFECT BEAST - KPL 80% English 20% Swahili! | 🟢 BRAND + FREE WEB SERVER ACTIVE")
    while True:
        try:
            hour = datetime.now().hour
            req_count = get_request_count()
            if req_count >= 95:
                print("⚠️ 95 requests used today! Sleeping 15 mins to save")
                time.sleep(900)
                continue
            if 11 <= hour <= 23:
                check_african_leagues()
                time.sleep(10)
                check_big_leagues_free()
                print("Sleeping 7 mins... (90 requests/day safe)")
                time.sleep(420)
            else:
                print(f"😴 {hour}h - Sleeping 15 mins, saving API requests")
                time.sleep(900)
        except Exception as e:
            print(f"Main loop error: {e}")
            time.sleep(60)
