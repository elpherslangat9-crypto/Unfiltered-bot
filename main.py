import os, json, time, threading, random, requests
from flask import Flask
from datetime import datetime
import pytz

app = Flask(__name__)
EAT = pytz.timezone("Africa/Nairobi")

API_KEY=os.getenv("API_FOOTBALL_KEY")
TG_TOKEN=os.getenv("TG_TOKEN")
TG_CHAT=os.getenv("TG_CHAT")
FB_PAGE_ID=os.getenv("FB_PAGE_ID")
FB_PAGE_TOKEN=os.getenv("FB_PAGE_TOKEN")

POSTED="/tmp/p21.json"
USED={"c":0}
def load():
    try: return json.load(open(POSTED))
    except: return {}
posted=load()
def save(): json.dump(posted, open(POSTED,"w"))

# FB ONLY 6 leagues for 100k growth
FB_ALLOW=["kenya","tanzania","nbc","ligi kuu","premier league","la liga","serie a","bundesliga","ligue 1","champions","uefa","england","spain","italy"]
TZ=["tanzania","nbc","simba","yanga"]

TAGS={
 "ke": ["#KPL #GorMahia #KenyaFootball #LiveScores","#HarambeeStars #KPLLive #GoalAlert"],
 "tz": ["#LigiKuu #SimbaSC #YangaSC #MpiraLive","#NBCPL #SokaLaBongo #GoliLaLeo #Tanzania"],
 "eu": ["#EPL #UCL #LaLiga #LiveScores #GoalAlert","#PremierLeague #ChampionsLeague #LiveFootball #Arsenal"]
}

def is_fb(l): return any(x in l.lower() for x in FB_ALLOW)
def is_tz(l): return any(x in l.lower() for x in TZ)
def tags(l):
    if "kenya" in l.lower(): return random.choice(TAGS["ke"])
    if is_tz(l): return random.choice(TAGS["tz"])
    return random.choice(TAGS["eu"])

def post(text):
    if not text.startswith("🟢"): text="🟢 "+text
    print(text)
    try: requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",json={"chat_id":TG_CHAT,"text":text},timeout=10)
    except: pass
    try:
        r=requests.post(f"https://graph.facebook.com/{FB_PAGE_ID}/feed",data={"message":text,"access_token":FB_PAGE_TOKEN},timeout=15)
        # Auto comment after 30 sec for algo boost
        if r.status_code==200:
            pid=r.json().get("id")
            time.sleep(25)
            try: requests.post(f"https://graph.facebook.com/{pid}/comments",data={"message":f"📊 Full stats & table on website: unfilteredscores.com 👇 Follow {chr(0x1F7E2)} for faster goals!","access_token":FB_PAGE_TOKEN},timeout=10)
            except: pass
    except: pass

# --- SOURCES ROTATING ---
def get_api(): # Only Kenya/TZ, saves 100 req
    if USED["c"]>=90 or not API_KEY: return []
    try:
        d=datetime.now(EAT).strftime("%Y-%m-%d")
        r=requests.get(f"https://v3.football.api-sports.io/fixtures?date={d}",headers={"x-apisports-key":API_KEY},timeout=15)
        USED["c"]+=1
        if r.status_code==429: return []
        out=[]
        for f in r.json().get("response",[]):
            lg=f["league"]["name"]
            if not ("kenya" in lg.lower() or is_tz(lg)): continue
            out.append({"src":"API","id":f"api-{f['fixture']['id']}","lg":lg,"h":f["teams"]["home"]["name"],"a":f["teams"]["away"]["name"],"st":f["fixture"]["status"]["short"],"m":str(f["fixture"]["status"]["elapsed"] or ""),"gh":f["goals"]["home"] or 0,"ga":f["goals"]["away"] or 0})
        return out
    except: return []

def get_ls(): # Livescore main fast
    try:
        url="https://prod-public-api.livescore.com/v1/api/app/date/soccer/"+datetime.now(EAT).strftime("%Y%m%d")+"/3?MD=1"
        j=requests.get(url,timeout=12).json()
        out=[]
        for s in j.get("Stages",[]):
            lg=s.get("Cnm","")+" "+s.get("Snm","")
            for e in s.get("Events",[]):
                out.append({"src":"LS","id":f"ls-{e.get('Eid')}","lg":lg,"h":e.get("T1",[{}])[0].get("Nm",""),"a":e.get("T2",[{}])[0].get("Nm",""),"st":e.get("Eps",""),"m":e.get("Eps",""),"gh":int(e.get("Tr1",0) or 0),"ga":int(e.get("Tr2",0) or 0)})
        return out
    except: return []

def get_espn_all(): # For WEBSITE - ALL COUNTRIES
    out=[]
    codes=["eng.1","esp.1","ita.1","ger.1","fra.1","uefa.champions","uefa.europa","ken.1","tan.1","ned.1","por.1","bra.1","mex.1","usa.1","afr.1"]
    for c in codes:
        try:
            j=requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{c}/scoreboard",timeout=8).json()
            for ev in j.get("events",[]):
                comp=ev["competitions"][0]
                lg=ev.get("league",{}).get("name",c)
                out.append({"src":"ESPN","id":f"espn-{ev['id']}","lg":lg,"h":comp["competitors"][0]["team"]["displayName"],"a":comp["competitors"][1]["team"]["displayName"],"st":comp["status"]["type"]["shortDetail"],"m":comp["status"]["displayClock"] or "","gh":int(comp["competitors"][0]["score"]),"ga":int(comp["competitors"][1]["score"])})
        except: continue
    return out

def get_news():
    try:
        j=requests.get("https://site.api.espn.com/apis/site/v2/sports/soccer/news",timeout=8).json()
        return j.get("articles",[])[:3]
    except: return []

def bot():
    rot=0
    while True:
        try:
            games=[]
            if rot%3==0: games+=get_api()
            if rot%3==1: games+=get_ls()
            else: games+=get_espn_all()
            if rot%2==0: games+=get_ls()
            rot+=1

            for g in games:
                # Only post FB if allowed
                if not is_fb(g["lg"]): continue
                sk=f"{g['id']}-{g['gh']}-{g['ga']}"
                ft=f"ft-{g['id']}"
                hyp=f"hyp-{g['id']}"

                # HYPE 60 min before big game
                if "NS" in g["st"] and hyp not in posted and any(x in g["lg"].lower() for x in ["premier","champions","kenya","tanzania"]):
                    if is_tz(g["lg"]): txt=f"🔥 MECHI KALI! {g['h']} vs {g['a']} - {g['m']}\n{g['lg']}\nNani atashinda? 👇\n\n{tags(g['lg'])}"
                    else: txt=f"🔥 COMING UP: {g['h']} vs {g['a']} - {g['lg']}\nWho wins? Comment 👇 Winner gets shoutout!\n\n{tags(g['lg'])}"
                    post(txt); posted[hyp]=1; save()

                # GOAL - Tanzanian Kiswahili
                if sk not in posted and (g["gh"]+g["ga"]>0):
                    t=tags(g["lg"])
                    if is_tz(g["lg"]): txt=f"GOOOL! Dakika {g['m']} {g['h']} {g['gh']}-{g['ga']} {g['a']}!\n{g['lg']} | {g['src']}\nSimba au Yanga? 👇\n\n{t}\nFollow 🟢 for live goals!"
                    else: txt=f"GOOAL! {g['m']} {g['h']} {g['gh']}-{g['ga']} {g['a']}\n{g['lg']} | {g['src']}\nArsenal au Man City? 👇\n\n{t}\nFollow 🟢 faster than TV!"
                    post(txt); posted[sk]=1; save()

                # FT
                if ("FT" in g["st"] or "Final" in g["st"]) and ft not in posted:
                    t=tags(g["lg"])
                    if is_tz(g["lg"]): txt=f"MATOKEO: {g['h']} {g['gh']}-{g['ga']} {g['a']}\n{g['lg']}\nMaoni yako? 👇\n\n{t}"
                    else: txt=f"FULL TIME: {g['h']} {g['gh']}-{g['ga']} {g['a']}\n{g['lg']}\nThoughts? 👇\n\n{t}"
                    post(txt); posted[ft]=1; save()

            # NEWS
            if rot%40==0:
                for a in get_news():
                    nid=f"news-{a['id']}"
                    if nid not in posted:
                        post(f"BREAKING: {a['headline']}\nDetails on website 👇\n\n#FootballNews #Transfers #LiveScores")
                        posted[nid]=1; save(); break
            time.sleep(40)
        except: time.sleep(20)

@app.route("/")
def home():
    try:
        games=get_espn_all()+get_ls()
        # Flashscore style grouped
        html="<html><head><meta name='viewport' content='width=device-width'><style>body{font-family:Arial;margin:0} .h{background:#0a5e2a;color:white;padding:12px;text-align:center} .c{padding:6px;border-bottom:1px solid #eee} .live{color:red;font-weight:bold}</style></head><body>"
        html+=f"<div class=h>🟢 Unfiltered Scores - LIVE | API {USED['c']}/100 | {len(games)} games</div>"
        for g in games[:250]:
            live="<span class=live>LIVE</span> " if "1H" in g['st'] or "2H" in g['st'] or g['gh']+g['ga']>0 else ""
            html+=f"<div class=c>{live}{g['lg']} - {g['h']} {g['gh']}-{g['ga']} {g['a']} {g['m']} [{g['src']}]</div>"
        html+="</body></html>"
        return html
    except Exception as e:
        return f"🟢 Unfiltered Scores LIVE - Loading {USED['c']}/100"

@app.route("/health")
def health(): return "OK"

threading.Thread(target=bot,daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.getenv("PORT",10000)))
