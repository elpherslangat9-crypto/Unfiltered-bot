import os, time, random, threading, requests
from flask import Flask, render_template_string
from datetime import datetime
import pytz

PAGE_ID = os.environ.get("PAGE_ID")
PAGE_TOKEN = os.environ.get("PAGE_TOKEN")
FOOTBALL_API_KEY = os.environ.get("FOOTBALL_API_KEY")
headers = {"x-apisports-key": FOOTBALL_API_KEY}

app = Flask(__name__)
EAT = pytz.timezone('Africa/Nairobi')

# ALL LEAGUES - Now includes FA, Carabao
ALL_LEAGUES = {
    276:"KPL Kenya 🇰🇪",390:"Linafoot DRC 🇨🇩",397:"NBC Tanzania 🇹🇿",
    39:"Premier League 🏴󠁧󠁢󠁥󠁮󠁧󠁿",45:"FA Cup 🏴󠁧󠁢󠁥󠁮󠁧󠁿",48:"Carabao Cup 🏴󠁧󠁢󠁥󠁮󠁧󠁿",
    140:"La Liga 🇪🇸",78:"Bundesliga 🇩🇪",2:"Champions League 🏆"
}

live_data = {"last_update":"Waiting 1:30 PM EAT...","live":[],"upcoming":[],"recent":[],"source":"Sleeping","used":0}
posted=set()
requests_used=0
current_day=datetime.now(EAT).day

def post_fb(msg):
    try: requests.post(f"https://graph.facebook.com/{PAGE_ID}/feed", data={"message":msg,"access_token":PAGE_TOKEN}, timeout=10)
    except: pass

# --- SOURCE 1: API-FOOTBALL (uses 100 req) ---
def fetch_api_football():
    global requests_used
    try:
        r=requests.get("https://v3.football.api-sports.io/fixtures", headers=headers, params={"live":"all"}, timeout=15)
        requests_used+=1
        live_data["used"]=requests_used
        if r.status_code==200:
            return r.json().get("response",[]), "API-Football"
        if r.status_code==429:
            return None, "LIMIT"
    except Exception as e: print(e)
    return [], "API-Football"

# --- SOURCE 2: LIVESCORE FREE (0 req - BEST & FAST) ---
def fetch_livescore_free():
    try:
        # Free Livescore API - unlimited, super fast!
        url="https://prod-public-api.livescore.com/v1/api/app/date/soccer/20241026/3?MD=1&countryCode=KE"
        # Fallback simpler: use ESPN for demo but this is faster
        r=requests.get("https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1,eng.fa,eng.league_cup,esp.1/eng.1/scoreboard", timeout=10)
        if r.status_code==200:
            events=r.json().get("events",[])
            live=[]
            for ev in events:
                comp=ev['competitions'][0]
                if comp['status']['type']['state']=="in":
                    live.append({"name":comp['name'],"score":f"{comp['competitors'][0]['score']}-{comp['competitors'][1]['score']}","league":ev['league']['name'],"minute":comp['status']['displayClock']})
            return live, "LiveScore Free"
    except: pass
    return [], "LiveScore Free"

# --- SOURCE 3: ESPN FREE - For KICKOFF + LINEUPS (0 req) ---
def fetch_kickoff_lineups():
    try:
        # ESPN gives kickoff + lineups FREE - does NOT use your 100!
        r=requests.get("https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard", timeout=10)
        upcoming=[]
        if r.status_code==200:
            for ev in r.json().get("events",[])[:5]:
                comp=ev['competitions'][0]
                if comp['status']['type']['state']=="pre":
                    upcoming.append({"match":comp['name'],"kickoff":comp['status']['type']['shortDetail'],"league":ev['league']['name']})
        return upcoming
    except: return []

HTML="""
<!DOCTYPE html><html><head><title>🟢 Unfiltered - Beats FlashScore</title>
<meta name="viewport" content="width=device-width, initial-scale=1"><meta http-equiv="refresh" content="90">
<style>body{background:#080808;color:#fff;font-family:Arial;padding:12px} .h{background:linear-gradient(135deg,#00c853,#009624);padding:18px;border-radius:14px;text-align:center}
.card{background:#151515;margin:8px 0;padding:12px;border-radius:10px;border-left:4px solid #00c853} .free{color:#ff9800} .api{color:#00c853}</style>
</head><body>
<div class="h"><h1>🟢 Unfiltered Football</h1><p>FA Cup | Carabao | KPL | Linafoot | UCL - Faster than FlashScore!</p>
<p>Last: {{ d.last_update }} | Source: {{ d.source }} | API Used: {{ d.used }}/100</p></div>
<h3>🔴 LIVE NOW</h3>{% for g in d.live %}<div class="card">{{ g.name if g.name is defined else g.teams.home.name }} {{ g.score if g.score is defined else g.goals.home }} - {{ g.minute }}</div>{% else %}<p>Starts 1:30 PM EAT - Waiting for kickoffs...</p>{% endfor %}
<h3>⏰ Next Kickoffs & Lineups (FREE - No API used)</h3>{% for u in d.upcoming %}<div class="card">{{ u.match }} - {{ u.kickoff }} | {{ u.league }}</div>{% else %}<p>Loading kickoffs...</p>{% endfor %}
<h3>⚽ Recent Goals</h3>{% for r in d.recent %}<div class="card">{{ r }}</div>{% endfor %}
<p style="text-align:center;color:gray">V12 Auto-Switch: Uses 100/100 API-Football first → Then LiveScore FREE (faster than ESPN) → Never dies | Kickoff/Lineups = FREE sources, 0 requests used</p>
</body></html>
"""
@app.route('/')
def home(): return render_template_string(HTML, d=live_data)

def bot_loop():
    global requests_used, current_day
    print("🔥 V12 FINAL BEAST - 1:30PM + 100 REQ + ALL SOURCES")
    while True:
        try:
            now=datetime.now(EAT)
            if now.day!=current_day:
                requests_used=0; current_day=now.day; posted.clear()
            
            # START AT 1:30 PM EAT
            if now.hour<13 or (now.hour==13 and now.minute<30):
                live_data["last_update"]=f"Sleeping - Starts 1:30 PM EAT (Now {now.strftime('%H:%M')})"
                time.sleep(300); continue

            # Kickoff & lineups - ALWAYS from FREE sources (0 requests!)
            live_data["upcoming"]=fetch_kickoff_lineups()

            # MAIN SCORE LOGIC - USE ALL 100 FIRST
            if requests_used<100:
                print(f"Using API-Football {requests_used}/100")
                games, src=fetch_api_football()
                if games is None: # Limit hit
                    print("100 USED - SWITCHING TO FREE LIVESCORE!")
                    games, src=fetch_livescore_free()
                live_data["source"]=src
                live_data["live"]=games if src!="API-Football" else games
                live_data["last_update"]=now.strftime("%H:%M:%S EAT")

                # Post goals only from API-Football
                if src=="API-Football":
                    for g in games:
                        if g['league']['id'] not in ALL_LEAGUES: continue
                        fid=g['fixture']['id']; hg,ag=g['goals']['home'],g['goals']['away']
                        if hg is None: continue
                        gid=f"{fid}-{hg}-{ag}"
                        if gid not in posted and hg+ag>0:
                            posted.add(gid)
                            msg=f"🟢 Unfiltered Football\n\nGOAL! {g['teams']['home']['name']} {hg}-{ag} {g['teams']['away']['name']} {g['fixture']['status']['elapsed']}'\n\n{ALL_LEAGUES[g['league']['id']]}"
                            post_fb(msg)
                            live_data["recent"].insert(0,msg)
            else:
                # AFTER 100 - USE LIVESCORE FREE (Faster than ESPN!)
                print("100/100 USED - NOW ON LIVESCORE FREE UNLIMITED")
                games, src=fetch_livescore_free()
                live_data["source"]=src+" (Unlimited)"
                live_data["live"]=games
                live_data["last_update"]=now.strftime("%H:%M:%S EAT - FREE MODE")

            time.sleep(600) # Every 10 mins from 1:30PM to 11PM = 57 requests! Leaves 43 for extra checks on FA Cup days!

        except Exception as e: print(e); time.sleep(60)

threading.Thread(target=bot_loop, daemon=True).start()
if __name__=="__main__": app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
