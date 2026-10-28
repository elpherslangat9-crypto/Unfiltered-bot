import os, json, time, threading, random, requests
from flask import Flask
from datetime import datetime
app = Flask(__name__)

API_KEY=os.getenv("API_FOOTBALL_KEY")
TG_TOKEN=os.getenv("TG_TOKEN")
TG_CHAT=os.getenv("TG_CHAT")
FB_PAGE_ID=os.getenv("FB_PAGE_ID")
FB_PAGE_TOKEN=os.getenv("FB_PAGE_TOKEN")

POSTED="/tmp/p23.json"
USED={"c":0}
def load():
    try: return json.load(open(POSTED))
    except: return {}
posted=load()
def save(): json.dump(posted, open(POSTED,"w"))

# ALL EUROPE TOP LEAGUES WITH MOST FOLLOWERS
FB_ALLOW=["kenya","tanzania","nbc","ligi kuu","premier league","la liga","serie a","bundesliga","ligue 1","champions","europa","conference","fa cup","carabao","efl cup","community","eredivisie","primeira","belgian","jupiler","super lig","turkey","scottish","premiership","eredevise","liga portugal","england","spain","italy","germany","france","netherlands","portugal","belgium","turkey","scotland","cup"]
TZ=["tanzania","nbc","simba","yanga"]

HASHTAGS={
 "kenya": ["#KPL #GorMahia #AFCLeopards #KenyaFootball #GreenFamily","#HarambeeStars #WanaUnfiltered #KPLLive"],
 "tanzania": ["#LigiKuu #SimbaSC #YangaSC #MpiraLive #GreenFamily","#NBCPL #SokaLaBongo #WanaUnfiltered"],
 "epl": ["#EPL #PremierLeague #Arsenal #ManUtd #GreenFamily #LiveScores","#EPLLive #Liverpool #ManCity"],
 "laliga": ["#LaLiga #RealMadrid #Barcelona #GreenFamily #LiveScores","#ElClasico #LaLigaLive"],
 "seriea": ["#SerieA #Juventus #ACMilan #Inter #GreenFamily","#Calcio #SerieALive #Napoli #Roma"],
 "bundesliga": ["#Bundesliga #BayernMunich #BVB #GreenFamily #LiveScores","#BundesligaLive #Leverkusen"],
 "ligue1": ["#Ligue1 #PSG #Mbappe #GreenFamily #LiveScores","#Ligue1Live #Marseille"],
 "ucl": ["#UCL #ChampionsLeague #GreenFamily #FasterThanTV #LiveScores","#UCLLive"],
 "europa": ["#EuropaLeague #UEL #GreenFamily #LiveScores","#UELlive #EuropaLeagueLive"],
 "conference": ["#ConferenceLeague #UECL #GreenFamily #LiveScores","#UECLlive"],
 "facup": ["#FACup #EmiratesFACup #GreenFamily #LiveScores","#FACupLive"],
 "carabao": ["#CarabaoCup #EFLCup #GreenFamily #LiveScores #FasterThanTV","#CarabaoCupLive"],
 "community": ["#CommunityShield #GreenFamily","#FACommunityShield"],
 "eredivisie": ["#Eredivisie #Ajax #PSV #Feyenoord #GreenFamily #LiveScores","#EredivisieLive #DutchFootball"],
 "primeira": ["#PrimeiraLiga #Benfica #Porto #Sporting #GreenFamily","#LigaPortugal #PrimeiraLigaLive"],
 "belgian": ["#JupilerProLeague #BelgianFootball #ClubBrugge #GreenFamily","#BelgianLeague #JupilerLeague"],
 "turkey": ["#SuperLig #Galatasaray #Fenerbahce #Besiktas #GreenFamily","#TurkishFootball #SuperLigLive"],
 "scottish": ["#ScottishPremiership #Celtic #Rangers #GreenFamily","#SPFL #ScottishFootball"],
}

def is_fb(l): return any(x in l.lower() for x in FB_ALLOW)
def is_tz(l): return any(x in l.lower() for x in TZ)
def get_tags(l):
    ll=l.lower()
    if "kenya" in ll: return random.choice(HASHTAGS["kenya"])
    if is_tz(ll): return random.choice(HASHTAGS["tanzania"])
    if "premier" in ll: return random.choice(HASHTAGS["epl"])
    if "la liga" in ll: return random.choice(HASHTAGS["laliga"])
    if "serie" in ll: return random.choice(HASHTAGS["seriea"])
    if "bundes" in ll: return random.choice(HASHTAGS["bundesliga"])
    if "ligue" in ll: return random.choice(HASHTAGS["ligue1"])
    if "champions" in ll: return random.choice(HASHTAGS["ucl"])
    if "europa league" in ll or "uefa europa" in ll and "conf" not in ll: return random.choice(HASHTAGS["europa"])
    if "conference" in ll: return random.choice(HASHTAGS["conference"])
    if "fa cup" in ll: return random.choice(HASHTAGS["facup"])
    if "carabao" in ll or "efl cup" in ll or "league cup" in ll: return random.choice(HASHTAGS["carabao"])
    if "community" in ll: return random.choice(HASHTAGS["community"])
    if "eredivisie" in ll or "netherlands" in ll or "dutch" in ll: return random.choice(HASHTAGS["eredivisie"])
    if "primeira" in ll or "portugal" in ll and "primeira" in ll or "liga portugal" in ll: return random.choice(HASHTAGS["primeira"])
    if "belgian" in ll or "jupiler" in ll or "belgium" in ll: return random.choice(HASHTAGS["belgian"])
    if "super lig" in ll or "turkey" in ll or "turkish" in ll: return random.choice(HASHTAGS["turkey"])
    if "scottish" in ll or "scotland" in ll or "premiership" in ll: return random.choice(HASHTAGS["scottish"])
    return random.choice(HASHTAGS["ucl"])

def post(text):
    if not text.startswith("🟢"): text="🟢 "+text
    print(text)
    try: requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",json={"chat_id":TG_CHAT,"text":text},timeout=10)
    except: pass
    try:
        r=requests.post(f"https://graph.facebook.com/{FB_PAGE_ID}/feed",data={"message":text,"access_token":FB_PAGE_TOKEN},timeout=15)
        if r.status_code==200:
            pid=r.json().get("id")
            time.sleep(25)
            try: requests.post(f"https://graph.facebook.com/{pid}/comments",data={"message":"📊 Full table & stats: unfilteredscores.com 👇 Follow Green Family — Faster Than TV! 🔔","access_token":FB_PAGE_TOKEN},timeout=10)
            except: pass
    except: pass

def get_api():
    if USED["c"]>=90 or not API_KEY: return []
    try:
        d=datetime.now().strftime("%Y-%m-%d")
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

def get_ls():
    try:
        d=datetime.now().strftime("%Y%m%d")
        j=requests.get(f"https://prod-public-api.livescore.com/v1/api/app/date/soccer/{d}/3?MD=1",timeout=12).json()
        out=[]
        for s in j.get("Stages",[]):
            lg=s.get("Cnm","")+" "+s.get("Snm","")
            for e in s.get("Events",[]):
                out.append({"src":"LS","id":f"ls-{e.get('Eid')}","lg":lg,"h":e.get("T1",[{}])[0].get("Nm",""),"a":e.get("T2",[{}])[0].get("Nm",""),"st":e.get("Eps",""),"m":e.get("Eps",""),"gh":int(e.get("Tr1",0) or 0),"ga":int(e.get("Tr2",0) or 0)})
        return out
    except: return []

def get_espn_all():
    out=[]
    codes=["eng.1","eng.fa","eng.league_cup","eng.community","esp.1","ita.1","ger.1","fra.1","uefa.champions","uefa.europa","uefa.europa.conf","ned.1","por.1","bel.1","tur.1","sco.1","ken.1","tan.1"]
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
    try: return requests.get("https://site.api.espn.com/apis/site/v2/sports/soccer/news",timeout=8).json().get("articles",[])[:3]
    except: return []

def bot():
    rot=0
    while True:
        try:
            now_h=datetime.now().hour
            if now_h==7 and f"gm-{datetime.now().date()}" not in posted:
                post("Good Morning Green Family 🟢 ☀️\nLeo ni siku kubwa! EPL, LaLiga, Bundesliga, Serie A, Eredivisie, Super Lig — all live today! Mko tayari? ⚡\n\n#GreenFamily #WanaUnfiltered #FasterThanTV")
                posted[f"gm-{datetime.now().date()}"]=1; save()
            if now_h==22 and f"gn-{datetime.now().date()}" not in posted:
                post("Good Night Green Family 🟢 ❤️\nThanks for today family! Kesho more football — UCL, Europa, FA Cup! Lala salama! 💚\n\n#OneFamily #GreenFamily")
                posted[f"gn-{datetime.now().date()}"]=1; save()

            games=[]
            if rot%3==0: games+=get_api()
            if rot%3==1: games+=get_ls()
            else: games+=get_espn_all()
            if rot%2==0: games+=get_ls()
            rot+=1

            for g in games:
                if not is_fb(g["lg"]): continue
                sk=f"{g['id']}-{g['gh']}-{g['ga']}"
                ft=f"ft-{g['id']}"
                if sk not in posted and (g["gh"]+g["ga"]>0):
                    t=get_tags(g["lg"])
                    if "kenya" in g["lg"].lower():
                        txt=f"GOOOAL! Dakika {g['m']} {g['h']} {g['gh']}-{g['ga']} {g['a']}!\n{g['lg']} | {g['src']}\n\nWasee wamechapa! Mambo iko aje Green Family? 👇\n\n{t}\n\n🟢 Unfiltered Scores | Faster Than TV ⚡"
                    elif is_tz(g["lg"]):
                        txt=f"GOOOL! Dakika {g['m']} {g['h']} {g['gh']}-{g['ga']} {g['a']}!\n{g['lg']} | {g['src']}\n\nSimba au Yanga leo? 👇\n\n{t}\n\n🟢 Unfiltered Scores | Haraka Kuliko TV ⚡"
                    else:
                        txt=f"GOOAL! {g['m']}' {g['h']} {g['gh']}-{g['ga']} {g['a']}\n{g['lg']} | {g['src']}\nMan of the Match? Green Family? 👇\n\n{t}\n\n🟢 Unfiltered Scores | Faster Than TV ⚡"
                    post(txt); posted[sk]=1; save()
                if ("FT" in g["st"] or "Final" in g["st"]) and ft not in posted:
                    t=get_tags(g["lg"])
                    txt=f"FULL TIME: {g['h']} {g['gh']}-{g['ga']} {g['a']}\n{g['lg']}\nThoughts Green Family? 👇\n\n{t}"
                    post(txt); posted[ft]=1; save()
            if rot%40==0:
                for a in get_news():
                    nid=f"news-{a['id']}"
                    if nid not in posted:
                        post(f"BREAKING: {a['headline']}\nGreen Family habari moto! 👇\n\n#FootballNews #GreenFamily")
                        posted[nid]=1; save(); break
            time.sleep(40)
        except: time.sleep(20)

@app.route("/")
def home():
    games=get_espn_all()+get_ls()
    html="""<html><head><meta name='viewport' content='width=device-width'><style>
    body{font-family:Arial;margin:0;background:#f5f5f5} .h{background:#0a5e2a;color:white;padding:14px;text-align:center;font-weight:bold;font-size:18px}
    .sub{background:white;padding:8px;text-align:center;border-bottom:2px solid #0a5e2a} .c{padding:10px;background:white;margin:5px;border-radius:6px;border-left:4px solid #0a5e2a}
    .live{color:red;animation:blink 1s infinite} @keyframes blink{50%{opacity:0}} .tag{color:#0a5e2a;font-size:12px}
    </style></head><body>"""
    html+=f"<div class=h>🟢 Unfiltered Scores | Faster Than TV ⚡</div><div class=sub>💚 Green Family - Wana Unfiltered | API {USED['c']}/100 | {len(games)} LIVE</div>"
    for g in games[:350]:
        live="<span class=live>● LIVE</span> " if g["gh"]+g["ga"]>0 else ""
        html+=f"<div class=c>{live}<b>{g['lg']}</b><br>{g['h']} {g['gh']}-{g['ga']} {g['a']} <span class=tag>{g['m']} [{g['src']}]</span></div>"
    return html+"</body></html>"

@app.route("/health")
def health(): return "OK"

threading.Thread(target=bot,daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.getenv("PORT",10000)))
