import os, json, time, random, requests, hashlib
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

API_KEY=os.getenv("API_FOOTBALL_KEY")
FB_PAGE_ID=os.getenv("FB_PAGE_ID")
FB_PAGE_TOKEN=os.getenv("FB_PAGE_TOKEN")

def load_any(names):
    for n in names:
        try:
            if os.path.exists(n): return json.load(open(n))
        except: pass
    return {}

posted=load_any(["/tmp/p31.json","posted_v31.json","posted_v30.json","posted.json","/tmp/p30.json"])
scores=load_any(["/tmp/s31.json","scores_v31.json","scores_v30.json","scores.json","/tmp/s30.json"])
USED={"api":0}

def save_all():
    for f in ["/tmp/p31.json","posted_v31.json","posted.json"]:
        try: json.dump(posted,open(f,"w"))
        except: pass
    for f in ["/tmp/s31.json","scores_v31.json","scores.json"]:
        try: json.dump(scores,open(f,"w"))
        except: pass

def fb_post(text):
    print(text[:250])
    try:
        r=requests.post(f"https://graph.facebook.com/{FB_PAGE_ID}/feed",data={"message":text,"access_token":FB_PAGE_TOKEN},timeout=12)
        print(f"FB {r.status_code} {r.text[:200]}")
        return r.status_code==200
    except Exception as e: print(f"FB err {e}"); return False

def get_tags(lg):
    ll=lg.lower()
    if "kenya" in ll: return "#KPL #FootballLive"
    if "tanzania" in ll or "nbc" in ll: return "#LigiKuuBara #FootballLive"
    if "premier" in ll: return "#PremierLeague #FootballLive"
    if "champions" in ll: return "#ChampionsLeague #FootballLive"
    if "la liga" in ll: return "#LaLiga #FootballLive"
    return "#FootballLive #UnfilteredScores"

def is_big(lg): return any(x in lg.lower() for x in ["premier","la liga","serie a","bundesliga","ligue 1","champions","europa","fa cup"])

def get_scorer_api(fid):
    if USED["api"]>=90 or not API_KEY: return ""
    try:
        r=requests.get(f"https://v3.football.api-sports.io/fixtures/events?fixture={fid}",headers={"x-apisports-key":API_KEY},timeout=4)
        USED["api"]+=1
        for ev in reversed(r.json().get("response",[])):
            if ev.get("type")=="Goal":
                p=ev.get("player",{}).get("name","")
                if p: return f" Scorer: {p} ⚽"
        return ""
    except: return ""

def get_api():
    if USED["api"]>=80 or not API_KEY: return []
    try:
        d=datetime.now().strftime("%Y-%m-%d")
        r=requests.get(f"https://v3.football.api-sports.io/fixtures?date={d}",headers={"x-apisports-key":API_KEY},timeout=5)
        USED["api"]+=1
        out=[]
        for f in r.json().get("response",[]):
            out.append({"id":f"api-{f['fixture']['id']}","fid":f['fixture']['id'],"lg":f["league"]["name"],"h":f["teams"]["home"]["name"],"a":f["teams"]["away"]["name"],"st":f["fixture"]["status"]["short"],"m":str(f["fixture"]["status"]["elapsed"] or ""),"gh":f["goals"]["home"] or 0,"ga":f["goals"]["away"] or 0,"norm":f"{f['teams']['home']['name'].lower()} vs {f['teams']['away']['name'].lower()}"})
        return out
    except Exception as e: print(f"API err {e}"); return []

def get_ls():
    try:
        d=datetime.now().strftime("%Y%m%d")
        j=requests.get(f"https://prod-public-api.livescore.com/v1/api/app/date/soccer/{d}/3?MD=1",timeout=4).json()
        out=[]
        for s in j.get("Stages",[]):
            lg=s.get("Cnm","")+" "+s.get("Snm","")
            for e in s.get("Events",[]):
                h=e.get("T1",[{}])[0].get("Nm",""); a=e.get("T2",[{}])[0].get("Nm","")
                out.append({"id":f"ls-{e.get('Eid')}","fid":e.get('Eid'),"lg":lg,"h":h,"a":a,"st":e.get("Eps",""),"m":e.get("Eps",""),"gh":int(e.get("Tr1",0) or 0),"ga":int(e.get("Tr2",0) or 0),"norm":f"{h.lower()} vs {a.lower()}","rc":int(e.get("Tr1RC",0) or 0)+int(e.get("Tr2RC",0) or 0)})
        return out
    except Exception as e: print(f"LS err {e}"); return []

def get_espn():
    out=[]
    codes=["eng.1","esp.1","ita.1","ger.1","fra.1","uefa.champions","ken.1","tan.1"]
    def fetch(c):
        try:
            j=requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{c}/scoreboard",timeout=3).json()
            res=[]
            for ev in j.get("events",[]):
                comp=ev["competitions"][0]; lg=ev.get("league",{}).get("name",c)
                h=comp["competitors"][0]["team"]["displayName"]; a=comp["competitors"][1]["team"]["displayName"]
                res.append({"id":f"espn-{ev['id']}","fid":ev['id'],"lg":lg,"h":h,"a":a,"st":comp["status"]["type"]["shortDetail"],"m":comp["status"]["displayClock"] or "","gh":int(comp["competitors"][0]["score"]),"ga":int(comp["competitors"][1]["score"]),"norm":f"{h.lower()} vs {a.lower()}"})
            return res
        except: return []
    with ThreadPoolExecutor(max_workers=8) as ex:
        for r in ex.map(fetch,codes): out.extend(r)
    return out

def bot():
    print("V31 FIXED START - gh ga small letters fixed - WILL POST NOW")
    # TEST POST TO CONFIRM TOKEN WORKS
    if f"test-{datetime.now().date()}" not in posted:
        ok=fb_post(f"⚽ TEST V31 FIXED - Bot is live again! API {USED['api']}/100\n\n#FootballLive #UnfilteredScores")
        if ok: posted[f"test-{datetime.now().date()}"]=True; save_all()
    
    while True:
        try:
            now=datetime.now()
            if USED["api"]<80:
                with ThreadPoolExecutor(max_workers=3) as ex: games=ex.submit(get_ls).result()+ex.submit(get_espn).result()+ex.submit(get_api).result()
            else:
                with ThreadPoolExecutor(max_workers=2) as ex: games=ex.submit(get_ls).result()+ex.submit(get_espn).result()
            print(f"Fetched {len(games)} total | API used {USED['api']}/100")
            random.shuffle(games)
            seen={}; valid=[]
            for g in games:
                gh=g["gh"]; ga=g["ga"]; n=g["norm"]; key=f"{n}-{gh}-{ga}"
                last=scores.get(n,{"gh":0,"ga":0})
                if gh<last["gh"] or ga<last["ga"]: continue
                if key in posted or key in seen: continue
                seen[key]=g; valid.append(g)
            print(f"Checking {len(valid)} unique games")

            for g in valid:
                n=g["norm"]; t=get_tags(g["lg"]); st=g["st"]; m=str(g["m"])
                is_ft="FT" in st or "Final" in st or "Finished" in st or "FT" in m
                is_ht="HT" in st or "Half" in st
                gh=g["gh"]; ga=g["ga"]
                
                goal_key=f"goal-{n}-{gh}-{ga}"; ft_key=f"ft-{n}"; ht_key=f"ht-{n}"; rc_key=f"red-{n}-{gh}-{ga}"
                
                last=scores.get(n,{"gh":0,"ga":0})
                if not is_ft and not is_ht and gh+ga>0 and goal_key not in posted and (gh>last["gh"] or ga>last["ga"]):
                    scorer=""
                    if is_big(g["lg"]) and "api-" in g["id"]: scorer=get_scorer_api(g["fid"])
                    txt=f"⚽ GOOAL! {m}' {g['h']} {gh}-{ga} {g['a']}!{scorer}\n{g['lg']}\n\n{t}"
                    if fb_post(txt): posted[goal_key]=True; scores[n]={"gh":gh,"ga":ga}; save_all()

                if is_ht and ht_key not in posted:
                    if fb_post(f"⏸️ HALF TIME: {g['h']} {gh}-{ga} {g['a']}\n{g['lg']}\n\n{t}"):
                        posted[ht_key]=True; scores[n]={"gh":gh,"ga":ga}; save_all()

                if is_ft and ft_key not in posted:
                    if fb_post(f"✅ FULL TIME: {g['h']} {gh}-{ga} {g['a']}\n{g['lg']}\n\n{t}"):
                        posted[ft_key]=True; scores[n]={"gh":gh,"ga":ga}; save_all()

                if g.get("rc",0)>0 and rc_key not in posted and not is_ft:
                    if fb_post(f"🟥 RED CARD! {g['h']} vs {g['a']} | {m}'\n{g['lg']}\n\n{t}"):
                        posted[rc_key]=True; save_all()

            time.sleep(5)
        except Exception as e: print(f"LOOP ERR {e}"); time.sleep(5)

if __name__=="__main__": bot()
