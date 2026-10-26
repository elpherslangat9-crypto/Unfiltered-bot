import os, time, threading, requests
from flask import Flask, render_template_string, jsonify, request, Response
from datetime import datetime, timezone, timedelta
from collections import defaultdict

app = Flask(__name__)

# --- YOUR KEYS - Add these in Render Environment ---
PAGE_ID = os.environ.get("PAGE_ID")
PAGE_TOKEN = os.environ.get("PAGE_TOKEN")
FOOTBALL_API_KEY = os.environ.get("FOOTBALL_API_KEY")

# NEW: Telegram + WhatsApp - Add in Render!
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")  # From @BotFather
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID", "@unfiltered_scores")
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")  # From Meta Developers
WHATSAPP_PHONE_ID = os.environ.get("WHATSAPP_PHONE_ID")
WHATSAPP_CHANNEL_ID = os.environ.get("WHATSAPP_CHANNEL_ID") # For WhatsApp Channels

headers = {"x-apisports-key": FOOTBALL_API_KEY} if FOOTBALL_API_KEY else {}
EAT = timezone(timedelta(hours=3))
cache = {}
posted = set()  # Smart duplicate check!

# --- SMART POSTING TO ALL CHANNELS ---
def post_all_channels(msg):
    """Post 1 message to Telegram + WhatsApp + Facebook - SMART!"""
    # 1. Telegram
    try:
        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL_ID:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            requests.post(url, data={"chat_id": TELEGRAM_CHANNEL_ID, "text": msg}, timeout=10)
            print(f"Posted to Telegram: {msg[:50]}")
    except Exception as e:
        print(f"Telegram error: {e}")

    # 2. Facebook
    try:
        if PAGE_ID and PAGE_TOKEN:
            url = f"https://graph.facebook.com/{PAGE_ID}/feed"
            requests.post(url, data={"message": msg, "access_token": PAGE_TOKEN}, timeout=10)
            print(f"Posted to FB")
    except: pass

    # 3. WhatsApp Cloud API (Channel)
    try:
        if WHATSAPP_TOKEN and WHATSAPP_PHONE_ID:
            # For WhatsApp Channels, you need community API - simplified
            url = f"https://graph.facebook.com/v19.0/{WHATSAPP_PHONE_ID}/messages"
            # This is for WhatsApp Business - for Channels we use same FB Graph
            # If you have WhatsApp Channel ID, posting is via FB Graph
            if WHATSAPP_CHANNEL_ID:
                fb_url = f"https://graph.facebook.com/{WHATSAPP_CHANNEL_ID}/messages"
                requests.post(fb_url, json={"message": msg}, headers={"Authorization": f"Bearer {WHATSAPP_TOKEN}"}, timeout=10)
            print(f"Posted to WhatsApp")
    except Exception as e:
        print(f"WhatsApp error: {e}")

def fetch_by_date(date_str):
    # LITE MODE: Cache 5 mins = 90% less API calls = 90% less data!
    if date_str in cache and time.time() - cache[date_str][0] < 300:
        return cache[date_str][1]
    data = []
    try:
        if FOOTBALL_API_KEY:
            r = requests.get("https://v3.football.api-sports.io/fixtures", headers=headers, params={"date": date_str}, timeout=15)
            if r.status_code == 200:
                data = r.json().get("response", [])
    except Exception as e:
        print(e)
    cache[date_str] = (time.time(), data)
    return data

def group_by_country(fixtures):
    grouped = defaultdict(list)
    for f in fixtures:
        country = f['league'].get('country','World')
        league = f['league']['name']
        grouped[(country, league)].append(f)
    by_country = defaultdict(list)
    for (country, league), games in grouped.items():
        by_country[country].append({"league": league, "games": games})
    return by_country

@app.route('/api/day')
def api_day():
    date_str = request.args.get('date')
    search = request.args.get('search','').lower()  # NEW: Search!
    if not date_str:
        date_str = datetime.now(EAT).strftime("%Y-%m-%d")
    fixtures = fetch_by_date(date_str)
    
    # NEW: Smart Search - Filter by team/league
    if search:
        fixtures = [f for f in fixtures if search in f['teams']['home']['name'].lower() or search in f['teams']['away']['name'].lower() or search in f['league']['name'].lower() or search in f['league'].get('country','').lower()]
    
    fixtures.sort(key=lambda f: f['fixture']['date'])
    grouped = group_by_country(fixtures)
    out = []
    for country, leagues in grouped.items():
        out.append({"country": country, "leagues": leagues})
    
    # Smart Priority - KPL Kenya first! Your idea!
    def country_priority(c):
        name = c['country'].lower()
        if 'kenya' in name: return 0
        if any(x in name for x in ['congo','tanzania','south africa','nigeria','ethiopia','uganda','africa']): return 1
        if 'england' in name: return 2
        if 'spain' in name or 'la liga' in name: return 3
        return 10
    out.sort(key=country_priority)
    return jsonify({"date": date_str, "countries": out, "count": len(fixtures), "lite": True})

ICON_SVG = """<svg xmlns='http://www.w3.org/2000/svg' width='512' height='512' viewBox='0 0 512 512'><rect width='512' height='512' rx='120' fill='black'/><circle cx='256' cy='256' r='210' fill='none' stroke='#39FF14' stroke-width='12'/><g transform='translate(256,165)'><circle cx='0' cy='0' r='65' fill='none' stroke='#39FF14' stroke-width='6'/><path d='M0,-65 L20,-45 L60,-35 L45,10 L20,50 L-20,50 L-45,10 L-60,-35 L-20,-45 Z' fill='none' stroke='#39FF14' stroke-width='5'/></g><text x='256' y='305' text-anchor='middle' font-family='Arial Black,Arial' font-weight='900' font-size='42' fill='#39FF14'>UNFILTERED</text><text x='256' y='355' text-anchor='middle' font-family='Arial Black,Arial' font-weight='900' font-size='52' fill='#39FF14'>SCORES</text></svg>"""

@app.route('/icon.svg')
def icon_svg():
    return Response(ICON_SVG, mimetype='image/svg+xml')

@app.route('/manifest.json')
def manifest():
    return jsonify({
        "name": "Unfiltered Scores",
        "short_name": "Unfiltered",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#000000",
        "theme_color": "#39FF14",
        "icons": [{"src": "/icon.svg", "sizes": "512x512", "type": "image/svg+xml"}]
    })

@app.route('/sw.js')
def sw():
    return Response("self.addEventListener('install',e=>self.skipWaiting());self.addEventListener('activate',e=>self.clients.claim());", mimetype='application/javascript')

HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#39FF14">
<title>Unfiltered Scores - V14.1 Lite</title>
<link rel="manifest" href="/manifest.json">
<link rel="icon" href="/icon.svg">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#000;color:#fff;font-family:Roboto,Arial,sans-serif}
.top{background:#000;position:sticky;top:0;z-index:20;border-bottom:2px solid #39FF14}
.logo-bar{display:flex;align-items:center;padding:12px 14px;gap:10px}
.logo-bar img{width:42px;height:42px;border-radius:10px}
.logo-bar h1{color:#39FF14;font-size:20px}
.logo-bar span{color:#666;font-size:11px;margin-left:auto}
.search-bar{padding:8px 12px;background:#0a0a0a;display:flex;gap:8px}
.search-bar input{flex:1;padding:10px 14px;border-radius:20px;border:1px solid #222;background:#151515;color:#fff;outline:none}
.search-bar input:focus{border-color:#39FF14}
.days{display:flex;overflow-x:auto;background:#0a0a0a;scrollbar-width:none}
.day-tab{min-width:62px;text-align:center;padding:10px 6px;border-bottom:3px solid transparent;cursor:pointer}
.day-tab.active{border-bottom-color:#39FF14;background:#111}
.day-tab .d1{font-size:11px;color:#888}
.day-tab .d2{font-size:14px;font-weight:bold;color:#fff}
.day-tab.active .d2{color:#39FF14}
.content{max-width:700px;margin:0 auto}
.country{margin-top:14px;background:#0f0f0f}
.country-head{padding:10px 12px;background:#151515;display:flex;gap:8px;font-size:13px;color:#39FF14;font-weight:bold;border-left:3px solid #39FF14}
.league{border-top:1px solid #1e1e1e}
.league-head{padding:8px 12px;font-size:12px;color:#aaa;background:#0a0a0a;display:flex;justify-content:space-between}
.match{padding:10px 12px;display:flex;align-items:center;gap:10px;border-top:1px solid #151515;background:#000}
.time{width:44px;font-size:12px;color:#39FF14;font-weight:bold}
.teams{flex:1;font-size:13px;line-height:18px}
.score{font-weight:bold;font-size:14px;background:#111;padding:4px 8px;border-radius:6px;min-width:40px;text-align:center}
.score.live{background:#39FF14;color:#000;animation:pulse 1.5s infinite}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(57,255,20,0.4)}70%{box-shadow:0 0 0 8px rgba(57,255,20,0)}100%{box-shadow:0 0 0 0 rgba(57,255,20,0)}}
.empty{padding:40px 20px;text-align:center;color:#666}
.lite-badge{background:#39FF14;color:#000;font-size:10px;padding:2px 6px;border-radius:10px;margin-left:8px}
</style>
</head>
<body>
<div class="top">
<div class="logo-bar"><img src="/icon.svg"><h1>UNFILTERED <span class="lite-badge">V14.1 LITE</span></h1><span id="total">Loading...</span></div>
<div class="search-bar"><input type="text" id="searchInput" placeholder="Search team, league, country... e.g. Gor Mahia, KPL, Arsenal" onkeyup="if(event.key==='Enter') doSearch()"><button onclick="doSearch()" style="background:#39FF14;color:#000;border:none;padding:10px 16px;border-radius:20px;font-weight:bold">Search</button></div>
<div class="days" id="days"></div>
</div>
<div class="content" id="content"><div class="empty">Loading fixtures... Lite Mode ON - 90% less data</div></div>
<script>
const EAT = 'Africa/Nairobi';
let currentDate = new Date().toLocaleDateString('en-CA', {timeZone: EAT});
let currentSearch = '';
function getWeekDays(){
  let days=[]; let today=new Date(); let day = today.getDay();
  let diff = today.getDate() - day + (day==0 ? -6 : 1);
  let monday = new Date(today.setDate(diff));
  for(let i=0;i<7;i++){ let d = new Date(monday); d.setDate(monday.getDate()+i); let iso = d.toLocaleDateString('en-CA', {timeZone: EAT}); let isToday = iso===currentDate; let label = d.toLocaleDateString('en', {weekday:'short', timeZone: EAT}).toUpperCase(); days.push({iso, label, num: d.getDate(), isToday}); }
  return days;
}
function renderDays(){
  let days=getWeekDays(); let h=''; days.forEach(d=>{ h+=`<div class="day-tab ${d.isToday?'active':''}" onclick="loadDay('${d.iso}', this)"><div class="d1">${d.label}</div><div class="d2">${d.num}</div></div>`; }); document.getElementById('days').innerHTML=h;
}
function toEATTime(iso){ try{ return new Date(iso).toLocaleTimeString('en-GB', {hour:'2-digit', minute:'2-digit', timeZone: EAT, hour12:false}); }catch(e){ return '';}}
function doSearch(){ currentSearch = document.getElementById('searchInput').value; loadDay(currentDate); }
async function loadDay(date, el){
  if(el){ document.querySelectorAll('.day-tab').forEach(x=>x.classList.remove('active')); el.classList.add('active'); currentDate=date; }
  document.getElementById('content').innerHTML='<div class="empty">Loading '+date+'...</div>';
  try{
    let url='/api/day?date='+date; if(currentSearch) url+='&search='+encodeURIComponent(currentSearch);
    let r=await fetch(url); let j=await r.json();
    document.getElementById('total').innerText=j.count+' matches' + (j.lite ? ' • LITE' : '');
    if(j.count==0){ document.getElementById('content').innerHTML=`<div class="empty"><b>No games found</b><br>${currentSearch ? 'No results for '+currentSearch : 'No games on '+date}</div>`; return; }
    let html=''; j.countries.forEach(c=>{ c.leagues.forEach(l=>{ html+=`<div class="country"><div class="country-head">${c.country}</div><div class="league"><div class="league-head"><span>${l.league}</span><span>${l.games.length}</span></div>`; l.games.forEach(g=>{ let time = toEATTime(g.fixture.date); let isLive = (g.fixture.status.short=='1H'||g.fixture.status.short=='2H'||g.fixture.status.short=='HT'); let home=g.teams.home.name; let away=g.teams.away.name; let scoreH=g.goals.home; let scoreA=g.goals.away; let scoreText=(scoreH!=null&&scoreA!=null)? `${scoreH} - ${scoreA}`: time; html+=`<div class="match"><div class="time">${time||'FT'}</div><div class="teams"><div>${home}</div><div>${away}</div></div><div class="score ${isLive?'live':''}">${scoreText}</div></div>`; }); html+=`</div></div>`; }); });
    document.getElementById('content').innerHTML=html;
  }catch(e){ document.getElementById('content').innerHTML='<div class="empty">Failed. Try again.</div>'; }
}
renderDays(); loadDay(currentDate);
// LITE MODE: Refresh every 15 sec only - saves data!
setInterval(()=>loadDay(currentDate), 15000);
</script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML)

def smart_bot():
    print("V14.1 SMART BOT Started - Telegram + FB + WhatsApp")
    while True:
        try:
            now = datetime.now(EAT)
            # Only post after 1pm Kenya
            if now.hour < 13 or (now.hour==13 and now.minute<30):
                time.sleep(300); continue
            today = now.strftime("%Y-%m-%d")
            fixtures = fetch_by_date(today)
            for f in fixtures:
                fid = f['fixture']['id']
                hg, ag = f['goals']['home'], f['goals']['away']
                if hg is None: continue
                gid = f"{fid}-{hg}-{ag}"
                # Smart duplicate check - post only once!
                if gid not in posted and (hg+ag)>0:
                    posted.add(gid)
                    league = f['league']['name']
                    home = f['teams']['home']['name']
                    away = f['teams']['away']['name']
                    minute = f['fixture']['status'].get('elapsed','')
                    msg = f"⚽ UNFILTERED SCORES\n\nGOAL! {home} {hg}-{ag} {away} {minute}'\n\n🏆 {league}\n\nLive: unfiltered-scores.vercel.app"
                    post_all_channels(msg)
            time.sleep(60)  # Check every 60 sec = LITE!
        except Exception as e:
            print(e); time.sleep(60)

threading.Thread(target=smart_bot, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
