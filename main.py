import os
import time
import threading
import requests
from flask import Flask, render_template_string, jsonify
from datetime import datetime, timezone, timedelta

PAGE_ID = os.environ.get("PAGE_ID")
PAGE_TOKEN = os.environ.get("PAGE_TOKEN")
FOOTBALL_API_KEY = os.environ.get("FOOTBALL_API_KEY")
headers = {"x-apisports-key": FOOTBALL_API_KEY}

app = Flask(__name__)
# EAT is UTC+3 - No pytz needed!
EAT = timezone(timedelta(hours=3))

ALL_LEAGUES = {
    276: "KPL Kenya",
    390: "Linafoot DRC",
    397: "NBC Tanzania",
    288: "PSL South Africa",
    332: "NPFL Nigeria",
    39: "Premier League",
    45: "FA Cup",
    48: "Carabao Cup",
    140: "La Liga",
    135: "Serie A",
    78: "Bundesliga",
    61: "Ligue 1",
    2: "Champions League",
    3: "Europa League"
}

live_data = {
    "last_update": "Waiting 1:30 PM EAT...",
    "live": [],
    "upcoming": [],
    "recent": [],
    "source": "Sleeping",
    "used": 0,
    "status": "Waiting"
}

posted = set()
requests_used = 0
current_day = datetime.now(EAT).day

def post_fb(msg):
    try:
        url = f"https://graph.facebook.com/{PAGE_ID}/feed"
        requests.post(url, data={"message": msg, "access_token": PAGE_TOKEN}, timeout=10)
    except Exception as e:
        print(e)

def fetch_api_football():
    global requests_used
    try:
        r = requests.get("https://v3.football.api-sports.io/fixtures", headers=headers, params={"live": "all"}, timeout=15)
        requests_used += 1
        live_data["used"] = requests_used
        if r.status_code == 200:
            return r.json().get("response", []), "API-Football"
        if r.status_code == 429:
            return None, "LIMIT_REACHED"
    except Exception as e:
        print(f"API error {e}")
    return [], "API-Football"

def fetch_livescore_free():
    try:
        r = requests.get("https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1,eng.fa,eng.league_cup,esp.1,ita.1,ger.1/scoreboard", timeout=12)
        if r.status_code == 200:
            events = r.json().get("events", [])
            live = []
            for ev in events:
                comp = ev['competitions'][0]
                state = comp['status']['type']['state']
                if state == "in":
                    live.append({
                        "name": comp.get('name', 'Match'),
                        "score": f"{comp['competitors'][0].get('score','0')}-{comp['competitors'][1].get('score','0')}",
                        "league": ev.get('league', {}).get('name','League'),
                        "minute": comp['status'].get('displayClock','LIVE'),
                        "home": comp['competitors'][0]['team']['displayName'],
                        "away": comp['competitors'][1]['team']['displayName'],
                        "status": "LIVE"
                    })
            return live, "LiveScore Free"
    except Exception as e:
        print(f"Free source error {e}")
    return [], "LiveScore Free"

def fetch_kickoff_lineups():
    try:
        r = requests.get("https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard", timeout=10)
        upcoming = []
        if r.status_code == 200:
            for ev in r.json().get("events", [])[:8]:
                comp = ev['competitions'][0]
                if comp['status']['type']['state'] == "pre":
                    upcoming.append({
                        "match": comp.get('name','Match'),
                        "kickoff": comp['status']['type'].get('shortDetail','Soon'),
                        "league": ev.get('league', {}).get('name','League'),
                        "time": comp.get('date','')
                    })
        return upcoming
    except:
        return []

@app.route('/manifest.json')
def manifest():
    return jsonify({
        "name": "Unfiltered Football - Live African & World Scores",
        "short_name": "Unfiltered",
        "description": "Fastest live scores for KPL, Linafoot, FA Cup, Carabao, Champions League",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0a0a0a",
        "theme_color": "#00c853",
        "icons": [
            {"src": "https://cdn-icons-png.flaticon.com/512/53/53283.png", "sizes": "512x512", "type": "image/png"}
        ]
    })

@app.route('/sw.js')
def service_worker():
    sw = """
    self.addEventListener('install', e => self.skipWaiting());
    self.addEventListener('activate', e => self.clients.claim());
    self.addEventListener('fetch', e => {
        e.respondWith(fetch(e.request).catch(() => caches.match(e.request)));
    });
    """
    return sw, 200, {'Content-Type': 'application/javascript'}

HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Unfiltered Football - Live Scores Faster Than FlashScore</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#00c853">
<meta name="description" content="Live scores for KPL Kenya, Linafoot DRC, Premier League, FA Cup, Carabao Cup, Champions League">
<link rel="manifest" href="/manifest.json">
<link rel="apple-touch-icon" href="https://cdn-icons-png.flaticon.com/512/53/53283.png">
<meta http-equiv="refresh" content="90">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#080808;color:#fff;font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Arial; padding:0}
.header{background: linear-gradient(135deg, #00c853 0%, #009624 100%); padding:22px 15px; text-align:center; position:sticky; top:0; z-index:10; box-shadow:0 4px 20px rgba(0,200,83,0.3)}
.header h1{font-size:26px; letter-spacing:1px}
.header p{opacity:0.95; font-size:13px; margin-top:6px}
.badge{display:inline-block; background:rgba(0,0,0,0.3); padding:4px 10px; border-radius:20px; font-size:11px; margin:2px}
.container{max-width:700px; margin:0 auto; padding:12px}
.card{background:#151515; margin:10px 0; padding:14px; border-radius:12px; border-left:4px solid #00c853; display:flex; justify-content:space-between; align-items:center; transition:0.2s}
.card:hover{background:#1e1e1e; transform:translateX(3px)}
.card.live{border-left-color:#ff1744; animation: pulse 2s infinite}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(255,23,68,0.4)} 70%{box-shadow:0 0 0 8px rgba(255,23,68,0)} 100%{box-shadow:0 0 0 0 rgba(255,23,68,0)}}
.league-tag{font-size:10px; background:#222; padding:3px 7px; border-radius:4px; color:#aaa}
.score{font-weight:bold; font-size:18px; color:#00c853}
.minute{font-size:12px; background:#ff1744; color:#fff; padding:2px 6px; border-radius:4px}
.section-title{margin:18px 0 8px 4px; font-size:15px; color:#00c853; letter-spacing:1px; text-transform:uppercase}
.install-btn{background:#fff; color:#00c853; border:none; padding:10px 18px; border-radius:20px; font-weight:bold; cursor:pointer; margin-top:10px}
.footer{text-align:center; color:#666; font-size:11px; padding:20px; margin-top:20px; border-top:1px solid #222}
</style>
</head>
<body>
<div class="header">
<h1>UNFILTERED FOOTBALL</h1>
<p>FA Cup | Carabao Cup | KPL | Linafoot | UCL | Premier League</p>
<p>
<span class="badge">Last: {{ d.last_update }}</span>
<span class="badge">Source: {{ d.source }}</span>
<span class="badge">API Used: {{ d.used }}/100</span>
<span class="badge">{{ d.status }}</span>
</p>
<button class="install-btn" onclick="installApp()">Install as App</button>
</div>

<div class="container">
<div class="section-title">Live Now</div>
{% for g in d.live %}
<div class="card live">
<div>
<div style="font-size:14px">{{ g.name if g.name is defined else g.teams.home.name + ' vs ' + g.teams.away.name }}</div>
<div class="league-tag">{{ g.league if g.league is defined else g.league.name }}</div>
</div>
<div style="text-align:right">
<div class="score">{{ g.score if g.score is defined else g.goals.home|string + '-' + g.goals.away|string }}</div>
<div class="minute">{{ g.minute if g.minute is defined else g.fixture.status.elapsed|string + "'" }}</div>
</div>
</div>
{% else %}
<div class="card"><div>Starts 1:30 PM EAT - Checking fixtures...</div></div>
{% endfor %}

<div class="section-title">Next Kickoffs and Lineups (Free - 0 requests)</div>
{% for u in d.upcoming %}
<div class="card">
<div>{{ u.match }} <br><span class="league-tag">{{ u.league }}</span></div>
<div class="minute" style="background:#333">{{ u.kickoff }}</div>
</div>
{% else %}
<div class="card"><div>Loading kickoffs...</div></div>
{% endfor %}

<div class="section-title">Recent Goals</div>
{% for r in d.recent %}
<div class="card"><div style="font-size:13px">{{ r }}</div></div>
{% else %}
<div class="card"><div>No goals yet today - Starts 1:30 PM</div></div>
{% endfor %}

<div class="footer">
<p>V13.1 Final - No pytz - Auto Switch: 100 API-Football then LiveScore Free</p>
<p>Kickoff and Lineups use FREE sources - 0 requests from your 100</p>
<p>Install this site as App: Chrome menu > Add to Home Screen</p>
</div>
</div>

<script>
if ('serviceWorker' in navigator) { navigator.serviceWorker.register('/sw.js'); }
let deferredPrompt;
window.addEventListener('beforeinstallprompt', (e) => { e.preventDefault(); deferredPrompt = e; });
function installApp() {
  if (deferredPrompt) { deferredPrompt.prompt(); }
  else { alert('To install: Open Chrome menu (3 dots) > Add to Home Screen / Install App'); }
}
</script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_PAGE, d=live_data)

def bot_loop():
    global requests_used, current_day
    print("V13.1 FINAL BEAST STARTED - NO PYTZ - 1:30 PM EAT")
    while True:
        try:
            now = datetime.now(EAT)
            if now.day != current_day:
                requests_used = 0
                current_day = now.day
                posted.clear()

            if now.hour < 13 or (now.hour == 13 and now.minute < 30):
                live_data["last_update"] = f"Sleeping - Starts 1:30 PM EAT (Now {now.strftime('%H:%M')})"
                live_data["status"] = "Sleeping - Saves requests"
                time.sleep(300)
                continue

            live_data["upcoming"] = fetch_kickoff_lineups()

            if requests_used < 100:
                live_data["status"] = f"Using API-Football {requests_used}/100"
                games, src = fetch_api_football()
                if games is None:
                    print("100 USED - SWITCHING TO LIVESCORE FREE")
                    games, src = fetch_livescore_free()
                live_data["source"] = src
                live_data["live"] = games
                live_data["last_update"] = now.strftime("%H:%M:%S EAT")

                if src == "API-Football":
                    for g in games:
                        if g['league']['id'] not in ALL_LEAGUES:
                            continue
                        fid = g['fixture']['id']
                        hg, ag = g['goals']['home'], g['goals']['away']
                        if hg is None:
                            continue
                        gid = f"{fid}-{hg}-{ag}"
                        if gid not in posted and hg + ag > 0:
                            posted.add(gid)
                            league = ALL_LEAGUES[g['league']['id']]
                            home = g['teams']['home']['name']
                            away = g['teams']['away']['name']
                            minute = g['fixture']['status']['elapsed']
                            msg = f"Unfiltered Football\n\nGOAL! {home} {hg}-{ag} {away} {minute}'\n\n{league}"
                            post_fb(msg)
                            live_data["recent"].insert(0, msg)
            else:
                live_data["status"] = "FREE MODE - 100 used"
                games, src = fetch_livescore_free()
                live_data["source"] = src + " (Unlimited)"
                live_data["live"] = games
                live_data["last_update"] = now.strftime("%H:%M:%S EAT - FREE MODE")

            time.sleep(600)

        except Exception as e:
            print(e)
            time.sleep(60)

threading.Thread(target=bot_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
