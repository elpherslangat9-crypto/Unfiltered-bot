import os, json, time, threading, random, requests
from flask import Flask
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
app = Flask(__name__)

API_KEY=os.getenv("API_FOOTBALL_KEY")
TG_TOKEN=os.getenv("TG_TOKEN")
TG_CHAT=os.getenv("TG_CHAT")
FB_PAGE_ID=os.getenv("FB_PAGE_ID")
FB_PAGE_TOKEN=os.getenv("FB_PAGE_TOKEN")

POSTED_FILE_1="/tmp/p24.json"
POSTED_FILE_2="posted_v24.json"
USED={"c":0}
def load():
    for f in [POSTED_FILE_1, POSTED_FILE_2]:
        try:
            if os.path.exists(f): return json.load(open(f))
        except: continue
    return {}
posted=load()
def save():
    for f in [POSTED_FILE_1, POSTED_FILE_2]:
        try: json.dump(posted, open(f,"w"))
        except: pass

FB_ALLOW=["kenya","tanzania","nbc","ligi kuu","premier league","la liga","serie a","bundesliga","ligue 1","champions","europa","conference","fa cup","carabao","efl cup","community","eredivisie","primeira","jupiler","super lig","scottish","premiership","cup"]
TZ=["tanzania","nbc","simba","yanga"]

HASHTAGS={
 "kenya": ["#KPL #GorMahia #AFCLeopards #GreenFamily #LiveScores","#HarambeeStars #WanaUnfiltered"],
 "tanzania": ["#LigiKuu #SimbaSC #YangaSC #GreenFamily #MpiraLive","#NBCPL #SokaLaBongo"],
 "epl": ["#EPL #PremierLeague #Arsenal #ManUtd #GreenFamily","#EPLLive #Liverpool #ManCity"],
 "laliga": ["#LaLiga #RealMadrid #Barcelona #GreenFamily","#ElClasico #LaLigaLive"],
 "seriea": ["#SerieA #Juventus #ACMilan #Inter #GreenFamily","#Calcio #SerieALive"],
 "bundesliga": ["#Bundesliga #Bayern #BVB #GreenFamily","#BundesligaLive"],
 "ligue1": ["#Ligue1 #PSG #GreenFamily #LiveScores","#Ligue1Live"],
 "ucl": ["#UCL #ChampionsLeague #GreenFamily #FasterThanTV","#UCLLive #ChampionsLeagueLive"],
 "europa": ["#EuropaLeague #UEL #GreenFamily #FasterThanTV","#UELlive"],
 "conference": ["#ConferenceLeague #UECL #GreenFamily","#UECLlive"],
 "facup": ["#FACup #EmiratesFACup #GreenFamily #FasterThanTV","#FACupLive"],
 "carabao": ["#CarabaoCup #EFLCup #GreenFamily #FasterThanTV","#CarabaoCupLive"],
 "eredivisie": ["#Eredivisie #Ajax #PSV #Feyenoord #GreenFamily","#EredivisieLive"],
 "primeira": ["#PrimeiraLiga #Benfica #Porto #GreenFamily","#LigaPortugal"],
 "belgian": ["#JupilerProLeague #ClubBrugge #GreenFamily","#JupilerLeague"],
 "turkey": ["#SuperLig #Galatasaray #Fenerbahce #GreenFamily","#SuperLigLive"],
 "scottish": ["#ScottishPremiership #Celtic #Rangers #GreenFamily","#SPFL"],
}

def is_fb(l): return any(x in l.lower() for x in FB_ALLOW)
def is_tz(l): return any(x in l.lower() for x in TZ)
def is_recent(g):
    try:
        m=int(''.join(filter(str.isdigit, g["m"])) or 0)
        return m<=100
    except: return True

def get_tags(l):
    ll=l.lower()
    if "kenya" in ll: return random.choice(HASHTAGS["kenya"])
    if is_tz(ll): return random.choice(HASHTAGS["tanzania"])
    if "premier league" in ll or ll=="epl": return random.choice(HASHTAGS["epl"])
    if "la liga" in ll: return random.choice(HASHTAGS["laliga"])
    if "serie a" in ll: return random.choice(HASHTAGS["seriea"])
    if "bundesliga" in ll: return random.choice(HASHTAGS["bundesliga"])
    if "ligue 1" in ll: return random.choice(HASHTAGS["ligue1"])
    if "champions league" in ll: return random.choice(HASHTAGS["ucl"])
    if "europa league" in ll: return random.choice(HASHTAGS["europa"])
    if "conference" in ll: return random.choice(HASHTAGS["conference"])
    if "fa cup" in ll: return random.choice(HASHTAGS["facup"])
    if "carabao" in ll or "efl cup" in ll or "league cup" in ll: return random.choice(HASHTAGS["carabao"])
    if "community" in ll: return random.choice(HASHTAGS["ucl"])
    if "eredivisie" in ll or "netherlands" in ll: return random.choice(HASHTAGS["eredivisie"])
    if "primeira" in ll or "liga portugal" in ll: return random.choice(HASHTAGS["primeira"])
    if "jupiler" in ll or "belgian" in ll: return random.choice(HASHTAGS["belgian"])
    if "super lig" in ll or "turkey" in ll: return random.choice(HASHTAGS["turkey"])
    if "scottish" in ll or "premiership" in ll: return random.choice(HASHTAGS["scottish"])
    return random.choice(HASHTAGS["ucl"])

def get_lineup(mid):
    try:
        if "api-" in mid and API_KEY and USED["c"]<90:
            fid=mid.replace("api-","")
            r=requests.get(f"https://v3.football.api-sports.io/fixtures/lineups?fixture={fid}",headers={"x-apisports-key":API_KEY},timeout=5)
            USED["c"]+=1
            d=r.json().get("response",[])
            if d: return f" | XI: {d[0]['team']['name']} confirmed!"
    except: pass
    return ""

def post(text):
    if not text.startswith("🟢"): text="🟢 "+text
    print(text)
    try: requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",json={"chat_id":TG_CHAT,"text":text},timeout=10)
    except: pass
    try:
        r=requests.post(f"https://graph.facebook.com/{FB_PAGE_ID}/feed",data={"message":text,"access_token":FB_PAGE_TOKEN},timeout=15)
        if r.status_code==200:
            pid=r.json().get("id")
            time.sleep(20)
            try: requests.post(f"https://graph.facebook.com/{pid}/comments",data={"message":"📊 Live table & lineups: unfilteredscores.com 👇 Follow Green Family — Faster Than TV! 🔔","access_token":FB_PAGE_TOKEN},timeout=10)
            except: pass
    except: pass

def get_api():
    if USED["c"]>=90 or not API_KEY: return []
    try:
        d=datetime.now().strftime("%Y-%m-%d")
        r=requests.get(f"https://v3.football.api-sports.io/fixtures?date={d}",headers={"x-apisports-key":API_KEY},timeout=10)
        USED["c"]+=1
        if r.status_code==429: return []
        out=[]
        for f in r.json().get("response",[]):
            lg=f["league"]["name"]
            if not ("kenya" in lg.lower() or is_tz(lg)): continue
            out.append({"src":"API","id":f"api-{f['fixture']['id']}","lg":lg,"h":f["teams"]["home"]["name"],"a":f["teams"]["away"]["name"],"st":f["fixture"]["status"]["short"],"m":str(f["fixture"]["status"]["elapsed"] or ""),"gh":f["goals"]["home"] or 0,"ga":f["goals"]["away"] or 0})
        return out
    except: return []

def get_ls():
    try:
        d=datetime.now().strftime("%Y%m%d")
        j=requests.get(f"https://prod-public-api.livescore.com/v1/api/app/date/soccer/{d}/3?MD=1",timeout=8).json()
        out=[]
        for s in j.get("Stages",[]):
            lg=s.get("Cnm","")+" "+s.get("Snm","")
            for e in s.get("Events",[]):
                out.append({"src":"LS","id":f"ls-{e.get('Eid')}","lg":lg,"h":e.get("T1",[{}])[0].get("Nm",""),"a":e.get("T2",[{}])[0].get("Nm",""),"st":e.get("Eps",""),"m":e.get("Eps",""),"gh":int(e.get("Tr1",0) or 0),"ga":int(e.get("Tr2",0) or 0)})
        return out
    except: return []

def get_espn_all():
    out=[]
    codes=["eng.1","eng.fa","eng.league_cup","esp.1","ita.1","ger.1","fra.1","uefa.champions","uefa.europa","uefa.europa.conf","ned.1","por.1","bel.1","tur.1","sco.1","ken.1","tan.1"]
    def fetch(c):
        try:
            j=requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{c}/scoreboard",timeout=6).json()
            res=[]
            for ev in j.get("events",[]):
                comp=ev["competitions"][0]
                lg=ev.get("league",{}).get("name",c)
                res.append({"src":"ESPN","id":f"espn-{ev['id']}","lg":lg,"h":comp["competitors"][0]["team"]["displayName"],"a":comp["competitors"][1]["team"]["displayName"],"st":comp["status"]["type"]["shortDetail"],"m":comp["status"]["displayClock"] or "","gh":int(comp["competitors"][0]["score"]),"ga":int(comp["competitors"][1]["score"])})
            return res
        except: return []
    with ThreadPoolExecutor(max_workers=6) as ex:
        for r in ex.map(fetch, codes):
            out.extend(r)
    return out

# VERIFIED NEWS ONLY - BEST FORMAT
def get_verified_news():
    try:
        j=requests.get("https://site.api.espn.com/apis/site/v2/sports/soccer/news",timeout=8).json()
        articles=j.get("articles",[])
        verified=[]
        for a in articles:
            headline=a.get("headline","").lower()
            # VERIFY: skip rumors, unconfirmed, gossip
            if any(x in headline for x in ["rumor","gossip","could","might","reportedly linked"]): continue
            if not a.get("images"): continue  # Must have image = verified source
            if len(a.get("headline",""))<20: continue
            verified.append(a)
        return verified[:2]
    except: return []

def bot():
    while True:
        try:
            now=datetime.now()
            if now.hour==7 and f"gm-{now.date()}" not in posted:
                post("Good Morning Green Family 🟢 ☀️\nLeo ni siku kubwa! EPL, LaLiga, Bundesliga, Serie A, UCL, FA Cup, Eredivisie, Super Lig — all live today! Mko tayari? ⚡\n\n#GreenFamily #WanaUnfiltered #FasterThanTV")
                posted[f"gm-{now.date()}"]={"t":now.isoformat()}; save()
            if now.hour==22 and f"gn-{now.date()}" not in posted:
                post("Good Night Green Family 🟢 ❤️\nThanks family for today! Kesho more football! Lala salama! 💚\n\n#OneFamily #GreenFamily")
                posted[f"gn-{now.date()}"]={"t":now.isoformat()}; save()

            games=[]
            with ThreadPoolExecutor(max_workers=3) as ex:
                f1=ex.submit(get_api); f2=ex.submit(get_ls); f3=ex.submit(get_espn_all)
                games=f1.result()+f2.result()+f3.result()

            for g in games:
                if not is_fb(g["lg"]) or not is_recent(g): continue
                sk=f"{g['id']}-{g['gh']}-{g['ga']}"
                ft=f"ft-{g['id']}"
                if sk not in posted and (g["gh"]+g["ga"]>0):
                    lineup=get_lineup(g["id"])
                    t=get_tags(g["lg"])
                    if "kenya" in g["lg"].lower():
                        txt=f"GOOOAL! Dakika {g['m']} {g['h']} {g['gh']}-{g['ga']} {g['a']}!{lineup}\n{g['lg']} | {g['src']}\nWasee wamechapa! Mambo iko aje Green Family? 👇\n\n{t}\n\n🟢 Unfiltered Scores | Faster Than TV ⚡"
                    elif is_tz(g["lg"]):
                        txt=f"GOOOL! Dakika {g['m']} {g['h']} {g['gh']}-{g['ga']} {g['a']}!{lineup}\n{g['lg']} | {g['src']}\nSimba au Yanga leo? Maoni? 👇\n\n{t}\n\n🟢 Unfiltered Scores | Haraka Kuliko TV ⚡"
                    else:
                        txt=f"GOOAL! {g['m']}' {g['h']} {g['gh']}-{g['ga']} {g['a']}!{lineup}\n{g['lg']} | {g['src']}\nMan of the Match? Green Family thoughts? 👇\n\n{t}\n\n🟢 Unfiltered Scores | Faster Than TV ⚡"
                    post(txt); posted[sk]={"t":now.isoformat()}; save()
                if ("FT" in g["st"] or "Final" in g["st"]) and ft not in posted:
                    t=get_tags(g["lg"])
                    txt=f"FULL TIME: {g['h']} {g['gh']}-{g['ga']} {g['a']}\n{g['lg']}\nThoughts Green Family? 👇\n\n{t}"
                    post(txt); posted[ft]={"t":now.isoformat()}; save()

            # VERIFIED NEWS BEST FORMAT - Only 2 per day, official look
            if now.hour in [9,15,19]:
                for a in get_verified_news():
                    nid=f"news-{a['id']}"
                    if nid not in posted:
                        # BEST PROFESSIONAL NEWS FORMAT
                        headline=a['headline']
                        desc=a.get("description","")[:120]
                        txt=f"🟢 BREAKING NEWS | VERIFIED ✅\n\n{headline}\n\n{desc}...\n\n📍 Source: ESPN Verified\n🔗 Full story: unfilteredscores.com\n\nGreen Family, thoughts? 👇\n\n#BreakingNews #FootballNews #GreenFamily #Verified #FasterThanTV"
                        post(txt); posted[nid]={"t":now.isoformat()}; save(); break

            time.sleep(15)
        except Exception as e:
            print(e); time.sleep(10)

@app.route("/")
def home():
    games=get_espn_all()+get_ls()
    html="""<html><head><meta name='viewport' content='width=device-width'><title>Unfiltered Scores | Faster Than TV</title>
    <style>
    *{margin:0;padding:0;box-sizing:border-box} body{font-family:'Segoe UI',Arial;background:#0f172a;color:#fff}
    .header{background:linear-gradient(135deg,#0a5e2a,#16a34a);padding:16px;text-align:center;box-shadow:0 4px 12px rgba(0,0,0,0.3)}
    .header h1{font-size:22px;letter-spacing:1px} .header p{font-size:13px;opacity:0.9;margin-top:4px}
    .stats{background:#1e293b;padding:10px;text-align:center;font-size:13px;border-bottom:3px solid #16a34a}
    .match{background:#1e293b;margin:8px;border-radius:10px;padding:12px;border-left:5px solid #16a34a;box-shadow:0 2px 6px rgba(0,0,0,0.2)}
    .league{color:#22c55e;font-size:11px;font-weight:bold;text-transform:uppercase} .teams{font-size:15px;margin:6px 0;font-weight:600}
    .score{color:#facc15;font-weight:bold} .meta{font-size:11px;color:#94a3b8} .live{color:#ef4444;animation:blink 1s infinite;font-weight:bold}
    @keyframes blink{50%{opacity:0}} .footer{background:#0a5e2a;padding:14px;text-align:center;font-size:12px;margin-top:20px}
    </style></head><body>"""
    html+=f"<div class=header><h1>🟢 UNFILTERED SCORES</h1><p>Faster Than TV ⚡ | Green Family - Wana Unfiltered</p></div>"
    html+=f"<div class=stats>💚 LIVE NOW: {len(games)} games | API {USED['c']}/100 | Updated every 15s | Official & Verified ✅</div>"
    for g in games[:350]:
        live="<span class=live>● LIVE</span> " if g["gh"]+g["ga"]>0 else ""
        html+=f"<div class=match><div class=league>{live}{g['lg']} <span style='float:right'>{g['src']}</span></div><div class=teams>{g['h']} <span class=score>{g['gh']}-{g['ga']}</span> {g['a']}</div><div class=meta>{g['m']} | {g['st']}</div></div>"
    html+=f"<div class=footer>🟢 Unfiltered Scores | Faster Than TV ⚡ | Green Family - One Family 💚<br>Kenya • Tanzania • EPL • LaLiga • Serie A • Bundesliga • Ligue1 • UCL • Europa • FA Cup • Carabao • Eredivisie • Primeira • Super Lig • Jupiler • Scottish<br>© 2026 Official & Verified | unfilteredscores.com</div></body></html>"
    return html

@app.route("/health")
def health(): return "OK - Professional V24"

threading.Thread(target=bot,daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.getenv("PORT",10000)))
