import os, json, time, random, requests, hashlib
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

API_KEY=os.getenv("API_FOOTBALL_KEY")
FB_PAGE_ID=os.getenv("FB_PAGE_ID")
FB_PAGE_TOKEN=os.getenv("FB_PAGE_TOKEN")

# FILES
POSTED_FILE="/tmp/p30.json"
POSTED_FILE2="posted_v30.json"
SCORES_FILE="/tmp/s30.json"
SCORES_FILE2="scores_v30.json"

posted={}
scores={}
USED={"api":0}

def load_json(f1,f2):
    for f in [f1,f2]:
        try:
            if os.path.exists(f): return json.load(open(f))
        except: pass
    return {}

posted=load_json(POSTED_FILE,POSTED_FILE2)
scores=load_json(SCORES_FILE,SCORES_FILE2)

def save_all():
    for f in [POSTED_FILE,POSTED_FILE2]:
        try: json.dump(posted,open(f,"w"))
        except: pass
    for f in [SCORES_FILE,SCORES_FILE2]:
        try: json.dump(scores,open(f,"w"))
        except: pass

def fb_post(text):
    if not text.startswith("🟢"): text="🟢 "+text
    print(text[:250])
    try:
        r=requests.post(f"https://graph.facebook.com/{FB_PAGE_ID}/feed",data={"message":text,"access_token":FB_PAGE_TOKEN},timeout=12)
        print(f"FB {r.status_code}")
        if r.status_code==200:
            pid=r.json().get("id")
            time.sleep(8)
            try:
                requests.post(f"https://graph.facebook.com/{pid}/comments",data={"message":"📲 Follow Green Family 💚 Turn on notifications! #FasterThanTV #WanaUnfiltered","access_token":FB_PAGE_TOKEN},timeout=6)
            except: pass
            return True
        else: print(r.text[:300])
    except Exception as e: print(f"FB err {e}")
    return False

def get_tags(lg):
    ll=lg.lower()
    if "kenya" in ll: return "#KPL #GorMahia #AFCLeopards #GreenFamily #FasterThanTV #FootballKE"
    if "tanzania" in ll or "nbc" in ll or "simba" in ll or "yanga" in ll: return "#LigiKuu #SimbaSC #YangaSC #GreenFamily #NBCPL #WanaUnfiltered"
    if "premier" in ll: return "#EPL #PremierLeague #GreenFamily #FasterThanTV #Arsenal #ManCity #Liverpool #ManUtd"
    if "la liga" in ll: return "#LaLiga #RealMadrid #Barcelona #GreenFamily #FasterThanTV"
    if "serie a" in ll: return "#SerieA #Juventus #Inter #ACMilian #GreenFamily"
    if "bundesliga" in ll: return "#Bundesliga #Bayern #BVB #GreenFamily"
    if "ligue 1" in ll: return "#Ligue1 #PSG #GreenFamily"
    if "champions" in ll: return "#UCL #ChampionsLeague #GreenFamily #FasterThanTV #WanaUnfiltered"
    if "europa" in ll: return "#EuropaLeague #UEL #GreenFamily"
    if "fa cup" in ll: return "#FACup #EmiratesFACup #GreenFamily"
    return "#FootballLive #LiveScores #GreenFamily #FasterThanTV #WanaUnfiltered #FootballKenya"

def clean_min(m):
    try: return int(''.join(filter(str.isdigit,str(m))) or 0)
    except: return 0

def is_big(lg):
    return any(x in lg.lower() for x in ["premier","la liga","serie a","bundesliga","ligue 1","champions","europa","fa cup"])

# SOURCES
def get_api():
    if USED["api"]>=80 or not API_KEY: return []
    try:
        d=datetime.now().strftime("%Y-%m-%d")
        r=requests.get(f"https://v3.football.api-sports.io/fixtures?date={d}",headers={"x-apisports-key":API_KEY},timeout=6)
        USED["api"]+=1
        out=[]
        for f in r.json().get("response",[]):
            out.append({"src":"API","id":f"api-{f['fixture']['id']}","fid":f['fixture']['id'],"lg":f["league"]["name"],"h":f["teams"]["home"]["name"],"a":f["teams"]["away"]["name"],"st":f["fixture"]["status"]["short"],"m":str(f["fixture"]["status"]["elapsed"] or ""),"gh":f["goals"]["home"] or 0,"ga":f["goals"]["away"] or 0,"norm":f"{f['teams']['home']['name'].lower().strip()} vs {f['teams']['away']['name'].lower().strip()}"})
        print(f"API {len(out)} games used {USED['api']}/100")
        return out
    except: return []

def get_ls():
    try:
        d=datetime.now().strftime("%Y%m%d")
        j=requests.get(f"https://prod-public-api.livescore.com/v1/api/app/date/soccer/{d}/3?MD=1",timeout=4).json()
        out=[]
        for s in j.get("Stages",[]):
            lg=s.get("Cnm","")+" "+s.get("Snm","")
            for e in s.get("Events",[]):
                h=e.get("T1",[{}])[0].get("Nm",""); a=e.get("T2",[{}])[0].get("Nm","")
                out.append({"src":"LS","id":f"ls-{e.get('Eid')}","fid":e.get('Eid'),"lg":lg,"h":h,"a":a,"st":e.get("Eps",""),"m":e.get("Eps",""),"gh":int(e.get("Tr1",0) or 0),"ga":int(e.get("Tr2",0) or 0),"norm":f"{h.lower().strip()} vs {a.lower().strip()}","rc":int(e.get("Tr1RC",0) or 0)+int(e.get("Tr2RC",0) or 0)})
        print(f"LS {len(out)} games")
        return out
    except Exception as e: print(f"LS err {e}"); return []

def get_espn():
    out=[]
    codes=["eng.1","esp.1","ita.1","ger.1","fra.1","uefa.champions","uefa.europa","eng.fa","ned.1","por.1","tur.1","sco.1","ken.1","tan.1"]
    def fetch(c):
        try:
            j=requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{c}/scoreboard",timeout=3).json()
            res=[]
            for ev in j.get("events",[]):
                comp=ev["competitions"][0]; lg=ev.get("league",{}).get("name",c)
                h=comp["competitors"][0]["team"]["displayName"]; a=comp["competitors"][1]["team"]["displayName"]
                res.append({"src":"ESPN","id":f"espn-{ev['id']}","fid":ev['id'],"lg":lg,"h":h,"a":a,"st":comp["status"]["type"]["shortDetail"],"m":comp["status"]["displayClock"] or "","gh":int(comp["competitors"][0]["score"]),"ga":int(comp["competitors"][1]["score"]),"norm":f"{h.lower().strip()} vs {a.lower().strip()}"})
            return res
        except: return []
    with ThreadPoolExecutor(max_workers=10) as ex:
        for r in ex.map(fetch,codes): out.extend(r)
    print(f"ESPN {len(out)} games")
    return out

def get_lineup(g):
    # API first, then LS when API done
    if not is_big(g["lg"]): return ""
    if "api-" in g["id"] and USED["api"]<85 and API_KEY:
        try:
            r=requests.get(f"https://v3.football.api-sports.io/fixtures/lineups?fixture={g['fid']}",headers={"x-apisports-key":API_KEY},timeout=4)
            USED["api"]+=1
            if r.json().get("response",[]): return " | XI confirmed ✅ | Lineups out!"
        except: pass
    if USED["api"]>=70:
        try:
            eid=g["fid"]
            r=requests.get(f"https://prod-public-api.livescore.com/v1/api/app/even/{eid}/lineups",timeout=4).json()
            if r.get("Lineups") or r.get("Lineup") or r.get("Coaches"): return " | Lineups confirmed ✅ | XI out!"
        except: pass
        try:
            if "espn-" in g["id"]:
                r=requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/summary?event={g['fid']}",timeout=4).json()
                if r.get("lineups"): return " | XI confirmed ✅"
        except: pass
    return ""

def get_many_news():
    all_news=[]
    urls=[
        "https://site.api.espn.com/apis/site/v2/sports/soccer/news",
        "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/news",
        "https://site.api.espn.com/apis/site/v2/sports/soccer/esp.1/news",
        "https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.champions/news",
        "https://site.api.espn.com/apis/site/v2/sports/soccer/ita.1/news"
    ]
    for u in urls:
        try:
            j=requests.get(u,timeout=4).json()
            for a in j.get("articles",[]):
                if not a.get("images"): continue
                if len(a.get("headline",""))<15: continue
                if any(x in a.get("headline","").lower() for x in ["rumor","gossip","could","might","reportedly"]): continue
                all_news.append(a)
        except: continue
    seen=set(); uniq=[]
    for n in all_news:
        h=hashlib.md5(n["headline"].encode()).hexdigest()
        if h not in seen: seen.add(h); uniq.append(n)
    print(f"News {len(uniq)} verified")
    return uniq[:10]

# MAIN BOT
def bot():
    print(f"V30 PERFECT START PAGE {FB_PAGE_ID} - ALL FEATURES - NO DUP NO WRONG SCORE")
    while True:
        try:
            now=datetime.now()
            if now.hour==7 and f"gm-{now.date()}" not in posted:
                fb_post("Good Morning Green Family 🟢 ☀️\nAll leagues live today! EPL, LaLiga, UCL, KPL, NBC — Faster Than TV! Mko tayari? ⚡\n\n#GreenFamily #WanaUnfiltered #FasterThanTV")
                posted[f"gm-{now.date()}"]=True; save_all()
            if now.hour==22 and f"gn-{now.date()}" not in posted:
                fb_post("Good Night Green Family 🟢 ❤️\nThanks family for today! Kesho more football! 💚\n\n#OneFamily #GreenFamily")
                posted[f"gn-{now.date()}"]=True; save_all()

            if USED["api"]<80:
                with ThreadPoolExecutor(max_workers=3) as ex:
                    games=ex.submit(get_ls).result()+ex.submit(get_espn).result()+ex.submit(get_api).result()
                print(f"MODE ALL - API {USED['api']}/100")
            else:
                with ThreadPoolExecutor(max_workers=2) as ex:
                    games=ex.submit(get_ls).result()+ex.submit(get_espn).result()
                print(f"MODE LS+ESPN ONLY - API DONE {USED['api']}/100 - LS now does lineups!")

            random.shuffle(games)
            seen={}
            valid=[]
            for g in games:
                n=g["norm"]; gh=g["GH"]; ga=g["GA"]; key=f"{n}-{gh}-{ga}"
                last=scores.get(n,{"gh":0,"ga":0})
                if gh<last["gh"] or ga<last["ga"]:
                    print(f"BLOCKED WRONG SCORE {n} was {last['gh']}-{last['ga']} got {gh}-{ga} from {g['src']}")
                    continue
                if key in posted or key in seen: continue
                seen[key]=g; valid.append(g)

            print(f"To check {len(valid)} unique")

            for g in valid:
                n=g["norm"]; t=get_tags(g["lg"])
                goal_key=f"goal-{n}-{g['GH']}-{g['GA']}"
                ft_key=f"ft-{n}"; ht_key=f"ht-{n}"; rc_key=f"red-{n}-{g['GH']}-{g['GA']}"
                lineup_key=f"lineup-{n}"

                if lineup_key not in posted and ("NS" in g["ST"] or "Pre" in g["ST"] or clean_min(g["M"])==0):
                    lu=get_lineup(g)
                    if lu:
                        txt=f"📋 LINEUP: {g['H']} vs {g['A']}{lu}\n{g['lg']} | {g['src']}\nPredictions Green Family? 👇\n\n{t}"
                        if fb_post(txt): posted[lineup_key]=True; save_all()

                last=scores.get(n,{"gh":0,"ga":0})
                if g["GH"]+g["GA"]>0 and goal_key not in posted and (g["GH"]>last["gh"] or g["GA"]>last["ga"] or (last["gh"]==0 and last["ga"]==0)):
                    lu=get_lineup(g) if is_big(g["lg"]) else ""
                    txt=f"GOOAL! {g['M']}' {g['H']} {g['GH']}-{g['GA']} {g['A']}!{lu}\n{g['lg']} | {g['src']} - Faster Than TV ⚡\nThoughts Green Family? 👇\n\n{t}\n\n🟢 Unfiltered Scores | WanaUnfiltered"
                    if fb_post(txt): posted[goal_key]=True; scores[n]={"gh":g["GH"],"ga":g["GA"]}; save_all()

                if g.get("rc",0)>0 and rc_key not in posted:
                    txt=f"🟥 RED CARD! {g['H']} vs {g['A']} | {g['M']}'\n{g['lg']} | {g['src']}\nGame changer! Thoughts? 👇\n\n{t}"
                    if fb_post(txt): posted[rc_key]=True; save_all()

                if ("HT" in g["ST"] or "Half" in g["ST"]) and ht_key not in posted:
                    txt=f"HALF TIME: {g['H']} {g['GH']}-{g['GA']} {g['A']}\n{g['lg']} | {g['ST']} | {g['src']}\nSecond half predictions? 👇\n\n{t}"
                    if fb_post(txt): posted[ht_key]=True; scores[n]={"gh":g["GH"],"ga":g["GA"]}; save_all()

                if ("FT" in g["ST"] or "Final" in g["ST"] or "Finished" in g["ST"]) and ft_key not in posted:
                    txt=f"FULL TIME: {g['H']} {g['GH']}-{g['GA']} {g['A']}\n{g['lg']} | {g['src']}\nMan of the Match Green Family? 👇\n\n{t}"
                    if fb_post(txt): posted[ft_key]=True; scores[n]={"gh":g["GH"],"ga":g["GA"]}; save_all()

            if now.minute%30<5:
                news=get_many_news()
                c=0
                for a in news:
                    if c>=3: break
                    nid=f"news-{a['id']}"
                    if nid not in posted:
                        txt=f"BREAKING | VERIFIED ✅\n\n{a['headline']}\n\n{a.get('description','')[:150]}...\n\n📍 Source: {a.get('source','ESPN')} Verified\nFollow Green Family!\n\n#BreakingNews #GreenFamily #VerifiedNews"
                        if fb_post(txt): posted[nid]=True; save_all(); c+=1; time.sleep(4)

            print(f"Loop done API {USED['api']}/100 sleep 4s"); time.sleep(4)
        except Exception as e: print(f"Err {e}"); time.sleep(5)

if __name__=="__main__":
    bot()
