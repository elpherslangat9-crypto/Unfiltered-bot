import os, json, time, random, requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

API_KEY=os.getenv("API_FOOTBALL_KEY")
PAGE=os.getenv("FB_PAGE_ID")
TOKEN=os.getenv("FB_PAGE_TOKEN")

def load_any(names):
    for n in names:
        try:
            if os.path.exists(n): return json.load(open(n))
        except: pass
    return {}
posted=load_any(["/tmp/p33.json","posted_v32.json","posted_v31.json","posted.json"])
scores=load_any(["/tmp/s33.json","scores_v32.json","scores.json"])
USED={"api":0}

def save():
    for f in ["/tmp/p33.json","posted_v33.json","posted.json"]:
        try: json.dump(posted,open(f,"w"))
        except: pass
    for f in ["/tmp/s33.json","scores_v33.json","scores.json"]:
        try: json.dump(scores,open(f,"w"))
        except: pass

def fb_text(txt):
    try:
        r=requests.post(f"https://graph.facebook.com/{PAGE}/feed",data={"message":txt,"access_token":TOKEN},timeout=12)
        print(f"TXT {r.status_code}")
        return r.status_code==200
    except: return False

def fb_photo(img_url, caption):
    try:
        r=requests.post(f"https://graph.facebook.com/{PAGE}/photos",data={"url":img_url,"caption":caption,"access_token":TOKEN},timeout=15)
        print(f"PHOTO {r.status_code} {r.text[:200]}")
        return r.status_code==200
    except Exception as e: print(e); return False

# HASHTAGS FOR FOLLOWERS PER COUNTRY/EVENT
def tags(lg):
    l=lg.lower()
    if "kenya" in l: return "#KPL #KenyaFootball #FootballLive"
    if "zambia" in l: return "#ZambiaSuperLeague #ZambiaFootball #FootballLive"
    if "tanzania" in l or "nbc" in l: return "#LigiKuuBara #TanzaniaFootball #FootballLive"
    if "uganda" in l: return "#UgandaPremierLeague #FootballLive"
    if "ethiopia" in l: return "#EthiopiaPremierLeague #FootballLive"
    if "nigeria" in l: return "#NPFL #NigeriaFootball #FootballLive"
    if "south africa" in l or "psl" in l: return "#PSL #SouthAfrica #FootballLive"
    if "premier league" in l or "eng.1" in l: return "#PremierLeague #EPL #FootballLive"
    if "la liga" in l: return "#LaLiga #FootballLive"
    if "serie a" in l: return "#SerieA #FootballLive"
    if "bundesliga" in l: return "#Bundesliga #FootballLive"
    if "ligue 1" in l: return "#Ligue1 #FootballLive"
    if "champions" in l: return "#ChampionsLeague #UCL #FootballLive"
    if "europa" in l: return "#EuropaLeague #FootballLive"
    if "brazil" in l: return "#Brasileirao #FootballLive"
    if "mls" in l: return "#MLS #FootballLive"
    return "#FootballLive #UnfilteredScores"

def clean_lg(lg):
    l=lg.lower()
    if "ken.1" in l: return "Kenya Premier League"
    if "zam.1" in l or "zambia" in l: return "Zambia Super League"
    if "tan.1" in l: return "Tanzania Premier League"
    return lg

def is_big(lg): return any(x in lg.lower() for x in ["premier league","la liga","serie a","bundesliga","ligue 1","champions","europa","kenya","zambia","tanzania"])

def scorer(fid):
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

def lineup_api(fid):
    if USED["api"]>=88 or not API_KEY: return False
    try:
        r=requests.get(f"https://v3.football.api-sports.io/fixtures/lineups?fixture={fid}",headers={"x-apisports-key":API_KEY},timeout=4)
        USED["api"]+=1
        return len(r.json().get("response",[]))>0
    except: return False

# SOURCES - TODAY ONLY
def get_api():
    if USED["api"]>=80 or not API_KEY: return []
    try:
        d=datetime.now().strftime("%Y-%m-%d")
        r=requests.get(f"https://v3.football.api-sports.io/fixtures?date={d}",headers={"x-apisports-key":API_KEY},timeout=6)
        USED["api"]+=1
        out=[]
        for f in r.json().get("response",[]):
            if datetime.fromtimestamp(f["fixture"]["timestamp"]).date()!=datetime.now().date(): continue
            out.append({"id":f"api-{f['fixture']['id']}","fid":f['fixture']['id'],"lg":f["league"]["name"],"h":f["teams"]["home"]["name"],"a":f["teams"]["away"]["name"],"st":f["fixture"]["status"]["short"],"m":str(f["fixture"]["status"]["elapsed"] or ""),"gh":f["goals"]["home"] or 0,"ga":f["goals"]["away"] or 0,"norm":f"{f['teams']['home']['name'].lower()} vs {f['teams']['away']['name'].lower()}"})
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
                out.append({"id":f"ls-{e.get('Eid')}","fid":e.get('Eid'),"lg":lg,"h":h,"a":a,"st":e.get("Eps",""),"m":e.get("Eps",""),"gh":int(e.get("Tr1",0) or 0),"ga":int(e.get("Tr2",0) or 0),"norm":f"{h.lower()} vs {a.lower()}"})
        return out
    except: return []

def get_espn():
    out=[]
    codes=["eng.1","esp.1","ita.1","ger.1","fra.1","uefa.champions","ken.1","tan.1","zam.1"]
    def fetch(c):
        try:
            j=requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{c}/scoreboard",timeout=4).json()
            res=[]
            for ev in j.get("events",[]):
                if ev.get("date","")[:10]!=datetime.now().strftime("%Y-%m-%d") and c in ["ken.1","tan.1","zam.1"]: continue
                comp=ev["competitions"][0]; lg=ev.get("league",{}).get("name",c)
                h=comp["competitors"][0]["team"]["displayName"]; a=comp["competitors"][1]["team"]["displayName"]
                res.append({"id":f"espn-{ev['id']}","fid":ev['id'],"lg":lg,"h":h,"a":a,"st":comp["status"]["type"]["shortDetail"],"m":comp["status"]["displayClock"] or "","gh":int(comp["competitors"][0]["score"]),"ga":int(comp["competitors"][1]["score"]),"norm":f"{h.lower()} vs {a.lower()}"})
            return res
        except: return []
    with ThreadPoolExecutor(max_workers=9) as ex:
        for r in ex.map(fetch,codes): out.extend(r)
    return out

def get_news():
    all=[]
    urls=["https://site.api.espn.com/apis/site/v2/sports/soccer/news","https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/news","https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.champions/news","https://site.api.espn.com/apis/site/v2/sports/soccer/esp.1/news"]
    for u in urls:
        try:
            for a in requests.get(u,timeout=4).json().get("articles",[])[:5]:
                if a.get("images") and len(a.get("headline",""))>20:
                    img=a["images"][0].get("url") or a["images"][0].get("url","")
                    if img: all.append({"id":a["id"],"title":a["headline"],"desc":a.get("description","")[:150],"img":img})
        except: pass
    # dedup
    seen=set(); uniq=[]
    for n in all:
        if n["id"] not in seen: seen.add(n["id"]); uniq.append(n)
    return uniq[:8]

def bot():
    print("V33 FINAL - NEVER REPEAT - KICKOFF TO FT - ZAMBIA - PHOTO NEWS")
    while True:
        try:
            if USED["api"]<80:
                with ThreadPoolExecutor(max_workers=3) as ex: games=ex.submit(get_ls).result()+ex.submit(get_espn).result()+ex.submit(get_api).result()
            else:
                with ThreadPoolExecutor(max_workers=2) as ex: games=ex.submit(get_ls).result()+ex.submit(get_espn).result()
            
            # ANTI-REPEAT: unique by norm+score
            seen={}; valid=[]
            for g in games:
                key=f"{g['norm']}-{g['gh']}-{g['ga']}"
                last=scores.get(g['norm'],{"gh":0,"ga":0})
                if g['gh']<last['gh'] or g['ga']<last['ga']: continue
                if key in posted or key in seen: continue
                seen[key]=g; valid.append(g)

            for g in valid:
                norm=g['norm']; lg=clean_lg(g['lg']); t=tags(lg)
                st=g['st']; m=str(g['m']); gh=g['gh']; ga=g['ga']
                is_ft="FT" in st or "Final" in st or "Finished" in st or m=="FT"
                is_ht="HT" in st
                is_live="1H" in st or "2H" in st or "HT" in st or ("'" in m and m.replace("'","").isdigit())

                line_key=f"lineup-{norm}"; kick_key=f"kick-{norm}"; goal_key=f"goal-{norm}-{gh}-{ga}"; ht_key=f"ht-{norm}"; ft_key=f"ft-{norm}"

                # 1. LINEUPS FOR BIG GAMES - ONLY ONCE
                if line_key not in posted and ("NS" in st or st=="" or m=="0"):
                    if is_big(lg) and "api-" in g['id'] and lineup_api(g['fid']):
                        if fb_text(f"📋 LINEUPS: {g['h']} vs {g['a']}\nLineups confirmed ✅\n{lg}\n\n{t}"):
                            posted[line_key]=True; save()

                # 2. KICKOFF - TRACK FROM START
                if kick_key not in posted and is_live and norm not in scores:
                    if fb_text(f"⚽ KICKOFF: {g['h']} vs {g['a']}\n{lg} is LIVE now!\n\n{t}"):
                        posted[kick_key]=True; scores[norm]={"gh":gh,"ga":ga}; save()

                last=scores.get(norm,{"gh":0,"ga":0})

                # 3. GOAL - WITH BALL + SCORER - NEVER IF FT
                if not is_ft and not is_ht and gh+ga>0 and goal_key not in posted and (gh>last['gh'] or ga>last['ga'] or norm not in scores):
                    sc=""
                    if is_big(lg) and "api-" in g['id']: sc=scorer(g['fid'])
                    if fb_text(f"⚽ GOOAL! {m}' {g['h']} {gh}-{ga} {g['a']}!{sc}\n{lg}\n\n{t}"):
                        posted[goal_key]=True; scores[norm]={"gh":gh,"ga":ga}; save()

                # 4. HALF TIME - ONLY IF WE TRACKED IT
                if is_ht and ht_key not in posted and norm in scores:
                    if fb_text(f"⏸️ HALF TIME: {g['h']} {gh}-{ga} {g['a']}\n{lg}\n\n{t}"):
                        posted[ht_key]=True; scores[norm]={"gh":gh,"ga":ga}; save()

                # 5. FULL TIME - ONLY IF WE TRACKED IT FROM KICKOFF/GOAL
                if is_ft and ft_key not in posted and norm in scores:
                    if fb_text(f"✅ FULL TIME: {g['h']} {gh}-{ga} {g['a']}\n{lg}\n\n{t}"):
                        posted[ft_key]=True; scores[norm]={"gh":gh,"ga":ga}; save()

            # NEWS WITH CLEAR PHOTOS - EVERY 45 MIN
            if datetime.now().minute%45<5:
                for n in get_news()[:2]:
                    nid=f"news-{n['id']}"
                    if nid not in posted:
                        cap=f"📰 {n['title']}\n\n{n['desc']}...\n\n#FootballLive #BreakingNews"
                        if fb_photo(n['img'], cap): posted[nid]=True; save(); time.sleep(4)

            time.sleep(6)
        except Exception as e: print(e); time.sleep(6)

if __name__=="__main__": bot()
