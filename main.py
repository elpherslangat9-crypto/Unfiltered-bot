import os, json, time, random, requests, hashlib
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

API_KEY=os.getenv("API_FOOTBALL_KEY")
FB_PAGE_ID=os.getenv("FB_PAGE_ID")
FB_PAGE_TOKEN=os.getenv("FB_PAGE_TOKEN")

# KEEP OLD POSTED FILES TO AVOID REPOSTING WHEN YOU COMMIT
def load_any(names):
    for n in names:
        try:
            if os.path.exists(n):
                return json.load(open(n))
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
        print(f"FB {r.status_code}")
        if r.status_code==200:
            time.sleep(8)
            return True
        print(r.text[:300])
    except Exception as e: print(e)
    return False

# ONLY 2-3 HASHTAGS FOR GROWTH - NO SPAM
def get_tags(lg):
    ll=lg.lower()
    if "kenya" in ll: return "#KPL #FootballLive"
    if "tanzania" in ll or "nbc" in ll: return "#LigiKuuBara #FootballLive"
    if "premier" in ll: return "#PremierLeague #FootballLive"
    if "champions" in ll: return "#ChampionsLeague #FootballLive"
    if "la liga" in ll: return "#LaLiga #FootballLive"
    if "serie a" in ll: return "#SerieA #FootballLive"
    return "#FootballLive #UnfilteredScores"

def clean_min(m):
    try: return int(''.join(filter(str.isdigit,str(m))) or 0)
    except: return 0

def is_big(lg): return any(x in lg.lower() for x in ["premier","la liga","serie a","bundesliga","ligue 1","champions","europa","fa cup"])

def get_scorer_api(fixture_id):
    if USED["api"]>=90 or not API_KEY: return ""
    try:
        r=requests.get(f"https://v3.football.api-sports.io/fixtures/events?fixture={fixture_id}",headers={"x-apisports-key":API_KEY},timeout=4)
        USED["api"]+=1
        events=r.json().get("response",[])
        # Find last goal
        for ev in reversed(events):
            if ev.get("type")=="Goal":
                player=ev.get("player",{}).get("name","")
                team=ev.get("team",{}).get("name","")
                if player: return f" Scorer: {player} ⚽ ({team})"
        return ""
    except: return ""

# SOURCES
def get_api():
    if USED["api"]>=80 or not API_KEY: return []
    try:
        d=datetime.now().strftime("%Y-%m-%d")
        r=requests.get(f"https://v3.football.api-sports.io/fixtures?date={d}",headers={"x-apisports-key":API_KEY},timeout=5)
        USED["api"]+=1
        out=[]
        for f in r.json().get("response",[]):
            out.append({"src":"API","id":f"api-{f['fixture']['id']}","fid":f['fixture']['id'],"lg":f["league"]["name"],"h":f["teams"]["home"]["name"],"a":f["teams"]["away"]["name"],"st":f["fixture"]["status"]["short"],"m":str(f["fixture"]["status"]["elapsed"] or ""),"gh":f["goals"]["home"] or 0,"ga":f["goals"]["away"] or 0,"norm":f"{f['teams']['home']['name'].lower()} vs {f['teams']['away']['name'].lower()}"})
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
                out.append({"src":"LS","id":f"ls-{e.get('Eid')}","fid":e.get('Eid'),"lg":lg,"h":h,"a":a,"st":e.get("Eps",""),"m":e.get("Eps",""),"gh":int(e.get("Tr1",0) or 0),"ga":int(e.get("Tr2",0) or 0),"norm":f"{h.lower()} vs {a.lower()}","rc":int(e.get("Tr1RC",0) or 0)+int(e.get("Tr2RC",0) or 0)})
        return out
    except: return []

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
                res.append({"src":"ESPN","id":f"espn-{ev['id']}","fid":ev['id'],"lg":lg,"h":h,"a":a,"st":comp["status"]["type"]["shortDetail"],"m":comp["status"]["displayClock"] or "","gh":int(comp["competitors"][0]["score"]),"ga":int(comp["competitors"][1]["score"]),"norm":f"{h.lower()} vs {a.lower()}"})
            return res
        except: return []
    with ThreadPoolExecutor(max_workers=8) as ex:
        for r in ex.map(fetch,codes): out.extend(r)
    return out

def get_lineup(g):
    if not is_big(g["lg"]): return ""
    if "api-" in g["id"] and USED["api"]<85 and API_KEY:
        try:
            r=requests.get(f"https://v3.football.api-sports.io/fixtures/lineups?fixture={g['fid']}",headers={"x-apisports-key":API_KEY},timeout=4)
            USED["api"]+=1
            if r.json().get("response",[]): return " | Lineups out ✅"
        except: pass
    if USED["api"]>=70:
        try:
            r=requests.get(f"https://prod-public-api.livescore.com/v1/api/app/even/{g['fid']}/lineups",timeout=4).json()
            if r.get("Lineups") or r.get("Lineup"): return " | Lineups confirmed ✅"
        except: pass
    return ""

def get_news():
    all=[]
    for u in ["https://site.api.espn.com/apis/site/v2/sports/soccer/news","https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/news","https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.champions/news"]:
        try:
            for a in requests.get(u,timeout=4).json().get("articles",[]):
                if a.get("images") and len(a.get("headline",""))>15 and "rumor" not in a.get("headline","").lower(): all.append(a)
        except: pass
    seen=set(); uniq=[]
    for n in all:
        h=hashlib.md5(n["headline"].encode()).hexdigest()
        if h not in seen: seen.add(h); uniq.append(n)
    return uniq[:6]

# MAIN
def bot():
    print("V31 CLEAN START - 2 HASHTAGS ONLY - NO REPOST - SCORER + BALL")
    while True:
        try:
            now=datetime.now()
            # No more Good Morning spam - only 1 per day
            if now.hour==7 and f"gm-{now.date()}" not in posted:
                fb_post(f"Good Morning Family ☀️\nAll leagues live today!\n\n#FootballLive #UnfilteredScores")
                posted[f"gm-{now.date()}"]=True; save_all()

            if USED["api"]<80:
                with ThreadPoolExecutor(max_workers=3) as ex: games=ex.submit(get_ls).result()+ex.submit(get_espn).result()+ex.submit(get_api).result()
            else:
                with ThreadPoolExecutor(max_workers=2) as ex: games=ex.submit(get_ls).result()+ex.submit(get_espn).result()

            random.shuffle(games)
            seen={}; valid=[]
            for g in games:
                n=g["norm"]; gh=g["GH"]; ga=g["GA"]; key=f"{n}-{gh}-{ga}"
                last=scores.get(n,{"gh":0,"ga":0})
                if gh<last["gh"] or ga<last["ga"]: continue # BLOCK WRONG SCORE
                if key in posted or key in seen: continue # BLOCK DUPLICATE
                seen[key]=g; valid.append(g)

            for g in valid:
                n=g["norm"]; t=get_tags(g["lg"])
                st=g["ST"]
                # FIX FOR YOUR SCREENSHOT BUG - NEVER POST GOAL IF FT
                is_ft="FT" in st or "Final" in st or "Finished" in st or "FT'" in str(g["M"]) or "FT" in str(g["M"])
                is_ht="HT" in st or "Half" in st

                goal_key=f"goal-{n}-{g['GH']}-{g['GA']}"
                ft_key=f"ft-{n}"; ht_key=f"ht-{n}"; rc_key=f"red-{n}-{g['GH']}-{g['GA']}"
                lineup_key=f"lineup-{n}"

                # LINEUP
                if lineup_key not in posted and ("NS" in st or "Pre" in st or clean_min(g["M"])==0):
                    lu=get_lineup(g)
                    if lu:
                        if fb_post(f"📋 LINEUP: {g['H']} vs {g['A']}{lu}\n{g['lg']}\n\n{t}"):
                            posted[lineup_key]=True; save_all()

                last=scores.get(n,{"gh":0,"ga":0})

                # GOAL - WITH BALL AND SCORER - NEVER IF FT
                if not is_ft and not is_ht and g["GH"]+g["GA"]>0 and goal_key not in posted and (g["GH"]>last["gh"] or g["GA"]>last["ga"] or last["gh"]==0):
                    scorer=""
                    if is_big(g["lg"]): # Only big leagues fetch scorer to save API
                        if "api-" in g["id"]:
                            scorer=get_scorer_api(g["fid"])
                    txt=f"⚽ GOOAL! {g['M']}' {g['H']} {g['GH']}-{g['GA']} {g['A']}!{scorer}\n{g['lg']}\n\n{t}"
                    if fb_post(txt):
                        posted[goal_key]=True; scores[n]={"gh":g["GH"],"ga":g["GA"]}; save_all()

                # HT
                if is_ht and ht_key not in posted:
                    if fb_post(f"⏸️ HALF TIME: {g['H']} {g['GH']}-{g['GA']} {g['A']}\n{g['lg']}\n\n{t}"):
                        posted[ht_key]=True; scores[n]={"gh":g["GH"],"ga":g["GA"]}; save_all()

                # FT
                if is_ft and ft_key not in posted:
                    if fb_post(f"✅ FULL TIME: {g['H']} {g['GH']}-{g['GA']} {g['A']}\n{g['lg']}\n\n{t}"):
                        posted[ft_key]=True; scores[n]={"gh":g["GH"],"ga":g["GA"]}; save_all()

                # RED
                if g.get("rc",0)>0 and rc_key not in posted and not is_ft:
                    if fb_post(f"🟥 RED CARD! {g['H']} vs {g['A']} | {g['M']}'\n{g['lg']}\n\n{t}"):
                        posted[rc_key]=True; save_all()

            # NEWS - many but clean
            if now.minute%30<4:
                for a in get_news()[:2]:
                    nid=f"news-{a['id']}"
                    if nid not in posted:
                        if fb_post(f"📰 {a['headline']}\n\n{a.get('description','')[:120]}...\n\n#FootballLive #BreakingNews"):
                            posted[nid]=True; save_all(); time.sleep(3)

            time.sleep(4)
        except Exception as e: print(e); time.sleep(5)

if __name__=="__main__": bot()
