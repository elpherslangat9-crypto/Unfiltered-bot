import os, json, time, random, requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

API_KEY=os.getenv("API_FOOTBALL_KEY")
FB_PAGE_ID=os.getenv("FB_PAGE_ID")
FB_PAGE_TOKEN=os.getenv("FB_PAGE_TOKEN")

POSTED_FILE="/tmp/p29.json"
POSTED_FILE2="posted_v29.json"
USED={"api":0, "total":0}

def load():
    for f in [POSTED_FILE, POSTED_FILE2]:
        try:
            if os.path.exists(f): return json.load(open(f))
        except: continue
    return {}
posted=load()
def save():
    for f in [POSTED_FILE, POSTED_FILE2]:
        try: json.dump(posted, open(f,"w"))
        except: pass

BIG_LEAGUES=["premier league","epl","la liga","serie a","bundesliga","ligue 1","champions league","ucl","europa","fa cup","community"]

def is_big(l): return any(x in l.lower() for x in BIG_LEAGUES)
def is_recent(m):
    try: return int(''.join(filter(str.isdigit, m)) or 0) <= 135
    except: return True

def get_tags(l):
    ll=l.lower()
    if "kenya" in ll: return "#KPL #GorMahia #AFCLeopards #GreenFamily #FasterThanTV"
    if "tanzania" in ll or "nbc" in ll or "simba" in ll or "yanga" in ll: return "#LigiKuu #SimbaSC #YangaSC #GreenFamily #NBCPL"
    if "premier" in ll: return "#EPL #PremierLeague #GreenFamily #FasterThanTV"
    if "la liga" in ll: return "#LaLiga #RealMadrid #Barcelona #GreenFamily"
    if "serie a" in ll: return "#SerieA #Juventus #Inter #GreenFamily"
    if "bundesliga" in ll: return "#Bundesliga #Bayern #GreenFamily"
    if "ligue 1" in ll: return "#Ligue1 #PSG #GreenFamily"
    if "champions" in ll: return "#UCL #ChampionsLeague #GreenFamily #FasterThanTV"
    if "europa" in ll: return "#EuropaLeague #UEL #GreenFamily"
    return "#FootballLive #LiveScores #GreenFamily #FasterThanTV #WanaUnfiltered"

def post_fb(text):
    if not text.startswith("🟢"): text="🟢 "+text
    print(text[:200])
    try:
        r=requests.post(f"https://graph.facebook.com/{FB_PAGE_ID}/feed",data={"message":text,"access_token":FB_PAGE_TOKEN},timeout=12)
        print(f"FB Status {r.status_code}")
        if r.status_code==200:
            pid=r.json().get("id")
            time.sleep(10)
            try: requests.post(f"https://graph.facebook.com/{pid}/comments",data={"message":"📊 More live: Follow Green Family 💚 Turn on notifications 🔔 #FasterThanTV","access_token":FB_PAGE_TOKEN},timeout=8)
            except: pass
            return True
        else: print(r.text[:300])
    except Exception as e: print(f"FB err {e}")
    return False

# ================= SOURCES =================

def get_api_games():
    if USED["api"]>=80 or not API_KEY:
        print(f"API LIMIT REACHED {USED['api']}/100 -> SWITCHING TO LIVESCORE")
        return []
    try:
        d=datetime.now().strftime("%Y-%m-%d")
        r=requests.get(f"https://v3.football.api-sports.io/fixtures?date={d}",headers={"x-apisports-key":API_KEY},timeout=6)
        USED["api"]+=1
        if r.status_code==429: return []
        out=[]
        for f in r.json().get("response",[]):
            st=f["fixture"]["status"]["short"]
            m=str(f["fixture"]["status"]["elapsed"] or "")
            out.append({
                "src":"API","id":f"api-{f['fixture']['id']}","fid":f['fixture']['id'],
                "lg":f["league"]["name"],"h":f["teams"]["home"]["name"],"a":f["teams"]["away"]["name"],
                "st":st,"m":m,"gh":f["goals"]["home"] or 0,"ga":f["goals"]["away"] or 0,
                "norm":f"{f['teams']['home']['name'].lower().strip()}-{f['teams']['away']['name'].lower().strip()}",
                "events":[] # will fill later
            })
        # Get events for red cards/penalties if API still available
        for g in out[:15]: # only first 15 to save API
            if USED["api"]>=95: break
            try:
                re=requests.get(f"https://v3.football.api-sports.io/fixtures/events?fixture={g['fid']}",headers={"x-apisports-key":API_KEY},timeout=4)
                USED["api"]+=1
                g["events"]=re.json().get("response",[])
            except: pass
        print(f"API: {len(out)} games, used {USED['api']}/100")
        return out
    except Exception as e:
        print(f"API fail {e}"); return []

def get_ls_games():
    try:
        d=datetime.now().strftime("%Y%m%d")
        j=requests.get(f"https://prod-public-api.livescore.com/v1/api/app/date/soccer/{d}/3?MD=1",timeout=4).json()
        out=[]
        for s in j.get("Stages",[]):
            lg=s.get("Cnm","")+" "+s.get("Snm","")
            for e in s.get("Events",[]):
                h=e.get("T1",[{}])[0].get("Nm",""); a=e.get("T2",[{}])[0].get("Nm","")
                # Livescore gives red cards in Eps and lineups in other endpoint
                out.append({
                    "src":"LS","id":f"ls-{e.get('Eid')}","fid":e.get('Eid'),
                    "lg":lg,"h":h,"a":a,"st":e.get("Eps",""),"m":e.get("Eps",""),
                    "gh":int(e.get("Tr1",0) or 0),"ga":int(e.get("Tr2",0) or 0),
                    "norm":f"{h.lower().strip()}-{a.lower().strip()}",
                    "events":[],"has_red": "RC" in str(e.get("Eps","")) or e.get("Tr1RC",0)>0 or e.get("Tr2RC",0)>0
                })
        print(f"LS: {len(out)} games - FASTEST")
        return out
    except Exception as e:
        print(f"LS fail {e}"); return []

def get_espn_games():
    out=[]
    codes=["eng.1","esp.1","ita.1","ger.1","fra.1","uefa.champions","uefa.europa","uefa.europa.conf","eng.fa","eng.league_cup","ned.1","por.1","bel.1","tur.1","sco.1","ken.1","tan.1"]
    def fetch(c):
        try:
            j=requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{c}/scoreboard",timeout=3).json()
            res=[]
            for ev in j.get("events",[]):
                comp=ev["competitions"][0]
                lg=ev.get("league",{}).get("name",c)
                h=comp["competitors"][0]["team"]["displayName"]; a=comp["competitors"][1]["team"]["displayName"]
                res.append({
                    "src":"ESPN","id":f"espn-{ev['id']}","fid":ev['id'],
                    "lg":lg,"h":h,"a":a,"st":comp["status"]["type"]["shortDetail"],"m":comp["status"]["displayClock"] or "",
                    "gh":int(comp["competitors"][0]["score"]),"ga":int(comp["competitors"][1]["score"]),
                    "norm":f"{h.lower().strip()}-{a.lower().strip()}",
                    "events":comp.get("details",[]),
                    "has_red": any("red card" in str(d).lower() for d in comp.get("details",[]))
                })
            return res
        except: return []
    with ThreadPoolExecutor(max_workers=8) as ex:
        for r in ex.map(fetch, codes):
            out.extend(r)
    print(f"ESPN: {len(out)} games")
    return out

def get_lineup_any(g):
    # TRY API FIRST, IF LIMIT THEN TRY LIVESCORE & ESPN
    lg=g["lg"]
    if not is_big(lg): return ""
    # 1. API lineup
    if "api-" in g["id"] and USED["api"]<85 and API_KEY:
        try:
            fid=g["id"].replace("api-","")
            r=requests.get(f"https://v3.football.api-sports.io/fixtures/lineups?fixture={fid}",headers={"x-apisports-key":API_KEY},timeout=4)
            USED["api"]+=1
            d=r.json().get("response",[])
            if d: return f" | XI: {d[0]['team']['name']} confirmed ✅"
        except: pass
    # 2. LIVESCORE LINEUP FALLBACK (when API finished)
    if "ls-" in g["id"] or USED["api"]>=80:
        try:
            eid=g["fid"]
            r=requests.get(f"https://prod-public-api.livescore.com/v1/api/app/even/{eid}/lineups",timeout=4).json()
            if r.get("Lineups"): return f" | XI: Lineups confirmed ✅ | {r['Lineups'][0]['TeamName']}"
        except: pass
    # 3. ESPN lineup
    try:
        if "espn-" in g["id"]:
            r=requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/summary?event={g['fid']}",timeout=4).json()
            if r.get("lineups"): return f" | XI: Lineups out ✅"
    except: pass
    return ""

def get_verified_news():
    try:
        j=requests.get("https://site.api.espn.com/apis/site/v2/sports/soccer/news",timeout=5).json()
        v=[]
        for a in j.get("articles",[]):
            if any(x in a.get("headline","").lower() for x in ["rumor","gossip","could","might"]): continue
            if not a.get("images"): continue
            if len(a.get("headline",""))<20: continue
            v.append(a)
        return v[:2]
    except: return []

# ================= MAIN BOT =================

def bot():
    print(f"V29 GITHUB->FB ONLY STARTED - PAGE {FB_PAGE_ID} - ALL FEATURES")
    while True:
        try:
            now=datetime.now()
            if now.hour==7 and f"gm-{now.date()}" not in posted:
                post_fb("Good Morning Green Family 🟢 ☀️\nAll leagues live today! EPL, LaLiga, UCL, KPL, NBC — Faster Than TV! Mko tayari? ⚡\n\n#GreenFamily #WanaUnfiltered"); posted[f"gm-{now.date()}"]={"t":now.isoformat()}; save()
            if now.hour==22 and f"gn-{now.date()}" not in posted:
                post_fb("Good Night Green Family 🟢 ❤️\nThanks family for today! Kesho more football! 💚\n\n#OneFamily #GreenFamily"); posted[f"gn-{now.date()}"]={"t":now.isoformat()}; save()

            games=[]
            # SMART SWITCHING
            if USED["api"]<80:
                with ThreadPoolExecutor(max_workers=3) as ex:
                    f1=ex.submit(get_ls_games); f2=ex.submit(get_espn_games); f3=ex.submit(get_api_games)
                    games = f1.result() + f2.result() + f3.result()
                print(f"MODE ALL SOURCES - API {USED['api']}/100")
            else:
                # API FINISHED -> LIVESCORE TAKES OVER EVERYTHING
                with ThreadPoolExecutor(max_workers=2) as ex:
                    f1=ex.submit(get_ls_games); f2=ex.submit(get_espn_games)
                    games = f1.result() + f2.result()
                print(f"MODE LIVESCORE+ESPN ONLY - API DONE {USED['api']}/100 - LS is now main!")

            random.shuffle(games)
            seen={}
            unique=[]
            for g in games:
                if not is_recent(g["m"]): continue
                key=f"{g['norm']}-{g['gh']}-{g['ga']}"
                if key not in seen:
                    seen[key]=True; unique.append(g)
            print(f"Unique after dedup: {len(unique)}")

            for g in unique:
                sk=f"goal-{g['norm']}-{g['gh']}-{g['ga']}"
                ft=f"ft-{g['norm']}"
                rc=f"red-{g['norm']}-{g['gh']}-{g['ga']}"
                pen=f"pen-{g['norm']}-{g['gh']}-{g['ga']}"
                ht=f"ht-{g['norm']}"
                lineup_key=f"lineup-{g['norm']}"

                t=get_tags(g["lg"])

                # 1. LINEUP (Only once, big leagues)
                if lineup_key not in posted and is_big(g["lg"]) and ("0" in g["m"] or "NS" in g["st"] or "Pre" in g["st"]):
                    lu=get_lineup_any(g)
                    if lu:
                        txt=f"📋 LINEUP: {g['h']} vs {g['a']}{lu}\n{g['lg']} | {g['src']}\nPredictions Green Family? 👇\n\n{t}"
                        if post_fb(txt): posted[lineup_key]={"t":now.isoformat()}; save()

                # 2. GOAL
                if sk not in posted and (g["gh"]+g["ga"]>0):
                    lu=get_lineup_any(g) if is_big(g["lg"]) else ""
                    txt=f"GOOAL! {g['m']}' {g['h']} {g['gh']}-{g['ga']} {g['a']}!{lu}\n{g['lg']} | {g['src']} - Faster Than TV ⚡\nGreen Family thoughts? 👇\n\n{t}\n\n🟢 Unfiltered Scores"
                    if post_fb(txt): posted[sk]={"t":now.isoformat()}; save()

                # 3. RED CARD
                if rc not in posted and (g.get("has_red") or any("red card" in str(ev).lower() for ev in g.get("events",[]))):
                    txt=f"🟥 RED CARD! {g['h']} vs {g['a']} | {g['m']}'\n{g['lg']} | {g['src']}\nGame changer! Thoughts? 👇\n\n{t}"
                    if post_fb(txt): posted[rc]={"t":now.isoformat()}; save()

                # 4. FULL TIME
                if ("FT" in g["st"] or "Final" in g["st"] or "Finished" in g["st"]) and ft not in posted:
                    txt=f"FULL TIME: {g['h']} {g['gh']}-{g['ga']} {g['a']}\n{g['lg']} | {g['src']}\nMan of the Match? 👇\n\n{t}"
                    if post_fb(txt): posted[ft]={"t":now.isoformat()}; save()

                # 5. HALF TIME
                if ("HT" in g["st"] or "Half" in g["st"]) and ht not in posted:
                    txt=f"HALF TIME: {g['h']} {g['gh']}-{g['ga']} {g['a']}\n{g['lg']} | {g['src']}\nSecond half predictions? 👇\n\n{t}"
                    if post_fb(txt): posted[ht]={"t":now.isoformat()}; save()

            # NEWS
            if now.hour in [9,15,19]:
                for a in get_verified_news():
                    nid=f"news-{a['id']}"
                    if nid not in posted:
                        txt=f"🟢 BREAKING NEWS | VERIFIED ✅\n\n{a['headline']}\n\n{a.get('description','')[:130]}...\n\n📍 Source: ESPN Verified\n🔗 Follow Green Family for more!\n\n#BreakingNews #GreenFamily #Verified"
                        if post_fb(txt): posted[nid]={"t":now.isoformat()}; save(); break

            USED["total"]+=1
            print(f"Loop {USED['total']} done - sleep 6s - API {USED['api']}/100")
            time.sleep(6)
        except Exception as e:
            print(f"Loop error {e}"); time.sleep(5)

if __name__=="__main__":
    bot()
