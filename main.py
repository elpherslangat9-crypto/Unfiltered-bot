import os, json, time, requests
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
posted=load_any(["/tmp/p38.json","posted_v37.json","posted.json"])
scores=load_any(["/tmp/s38.json","scores_v37.json","scores.json"])
sched=load_any(["/tmp/sched38.json","schedule.json"])
USED={"api":0, "reset":datetime.now().strftime("%Y-%m-%d")}

def save():
    try:
        json.dump(posted,open("/tmp/p38.json","w")); json.dump(posted,open("posted_v38.json","w")); json.dump(posted,open("posted.json","w"))
        json.dump(scores,open("/tmp/s38.json","w")); json.dump(scores,open("scores_v38.json","w")); json.dump(scores,open("scores.json","w"))
        json.dump(sched,open("/tmp/sched38.json","w")); json.dump(sched,open("schedule.json","w"))
    except: pass

def fb_text(t):
    try:
        r=requests.post(f"https://graph.facebook.com/{PAGE}/feed",data={"message":t,"access_token":TOKEN},timeout=10)
        return r.status_code==200
    except: return False

def fb_photo(img,cap):
    try:
        if "w=" in img: img=img.split("w=")[0]+"w=800"
        r=requests.post(f"https://graph.facebook.com/{PAGE}/photos",data={"url":img,"caption":cap,"access_token":TOKEN},timeout=15)
        return r.status_code==200
    except: return False

def clean_lg(lg):
    l=lg.lower()
    if "eng.1" in l or "premier" in l: return "Premier League"
    if "esp.1" in l or "laliga" in l or "la liga" in l: return "LaLiga"
    if "ita.1" in l or "serie a" in l: return "Serie A"
    if "ger.1" in l or "bundesliga" in l: return "Bundesliga"
    if "fra.1" in l or "ligue 1" in l: return "Ligue 1"
    if "uefa.champions" in l: return "Champions League"
    if "ken.1" in l or "kenya" in l: return "Kenya Premier League"
    if "zam.1" in l or "zambia" in l: return "Zambia Super League"
    if "tan.1" in l or "tanzania" in l: return "Tanzania Premier League"
    return lg

def tags(lg):
    l=lg.lower()
    if "kenya" in l: return "#KPL #KenyaFootball #FootballLive"
    if "zambia" in l: return "#ZambiaSuperLeague #ZambiaFootball #FootballLive"
    if "tanzania" in l: return "#LigiKuuBara #FootballLive"
    if "premier league" in l: return "#PremierLeague #FootballLive"
    if "laliga" in l: return "#LaLiga #FootballLive"
    if "champions" in l: return "#ChampionsLeague #FootballLive"
    return "#FootballLive #UnfilteredScores"

def is_big(lg): return any(x in lg.lower() for x in ["premier","laliga","serie a","bundesliga","champions","kenya","zambia","tanzania"])

# ========= SOURCES - LIVESCORE BETTER =========
def ls_live():
    out=[]
    try:
        # LS live = fastest, best
        j=requests.get("https://prod-public-api.livescore.com/v1/api/app/stage/soccer/live",timeout=4).json()
        for s in j.get("Stages",[]):
            lg=s.get("Cnm","")+" "+s.get("Snm","")
            for e in s.get("Events",[]):
                eps=e.get("Eps","")
                if eps in ["FT","AET","Postp."] or eps in ["","NS"]: continue
                h=e.get("T1",[{}])[0].get("Nm",""); a=e.get("T2",[{}])[0].get("Nm","")
                if h and a:
                    out.append({"src":"LS","lg":lg,"h":h,"a":a,"st":eps,"m":eps,"gh":int(e.get("Tr1",0) or 0),"ga":int(e.get("Tr2",0) or 0),"norm":f"{h.lower()} vs {a.lower()}"})
    except: pass
    return out

def espn_live():
    out=[]
    today=datetime.now().strftime("%Y%m%d")
    for code in ["ken.1","tan.1","zam.1","eng.1","esp.1"]:
        try:
            j=requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{code}/scoreboard?dates={today}",timeout=3).json()
            for ev in j.get("events",[]):
                if ev["competitions"][0]["status"]["type"]["state"]!="in": continue
                comp=ev["competitions"][0]
                h=comp["competitors"][0]["team"]["displayName"]; a=comp["competitors"][1]["team"]["displayName"]
                out.append({"src":"ESPN","lg":ev.get("league",{}).get("name",code),"h":h,"a":a,"st":"LIVE","m":comp["status"]["displayClock"] or "","gh":int(comp["competitors"][0]["score"]),"ga":int(comp["competitors"][1]["score"]),"norm":f"{h.lower()} vs {a.lower()}"})
        except: pass
    return out

def api_live():
    if USED["api"]>=75 or not API_KEY: return [] # switch to LS/ESPN before limit
    try:
        r=requests.get("https://v3.football.api-sports.io/fixtures?live=all",headers={"x-apisports-key":API_KEY},timeout=5)
        USED["api"]+=1
        out=[]
        for f in r.json().get("response",[]):
            out.append({"src":"API","fid":f['fixture']['id'],"lg":f["league"]["name"],"h":f["teams"]["home"]["name"],"a":f["teams"]["away"]["name"],"st":f["fixture"]["status"]["short"],"m":str(f["fixture"]["status"]["elapsed"] or ""),"gh":f["goals"]["home"] or 0,"ga":f["goals"]["away"] or 0,"norm":f"{f['teams']['home']['name'].lower()} vs {f['teams']['away']['name'].lower()}"})
        return out
    except: return []

def build_schedule():
    global sched
    today=datetime.now().strftime("%Y-%m-%d")
    if USED["reset"]!=today: USED["api"]=0; USED["reset"]=today
    last=sched.get("built_h",-10); cur=datetime.now().hour
    if sched.get("date")==today and cur-last<3 and len(sched.get("games",{}))>15: return
    games={}
    if API_KEY and USED["api"]<40:
        try:
            r=requests.get(f"https://v3.football.api-sports.io/fixtures?date={today}",headers={"x-apisports-key":API_KEY},timeout=6)
            USED["api"]+=1
            for f in r.json().get("response",[]):
                norm=f"{f['teams']['home']['name'].lower()} vs {f['teams']['away']['name'].lower()}"
                games[norm]={"h":f['teams']['home']['name'],"a":f['teams']['away']['name'],"lg":f['league']['name'],"fid":f['fixture']['id']}
        except: pass
    for code in ["ken.1","tan.1","zam.1","eng.1","esp.1","uefa.champions"]:
        try:
            j=requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{code}/scoreboard?dates={today.replace('-','')}",timeout=3).json()
            for ev in j.get("events",[]):
                comp=ev["competitions"][0]; h=comp["competitors"][0]["team"]["displayName"]; a=comp["competitors"][1]["team"]["displayName"]
                norm=f"{h.lower()} vs {a.lower()}"
                if norm not in games: games[norm]={"h":h,"a":a,"lg":ev.get("league",{}).get("name",code),"fid":ev['id']}
        except: pass
    sched={"date":today,"built_h":cur,"games":games}; save()

def scorer(fid):
    if USED["api"]>=90 or not API_KEY: return ""
    try:
        r=requests.get(f"https://v3.football.api-sports.io/fixtures/events?fixture={fid}",headers={"x-apisports-key":API_KEY},timeout=3)
        USED["api"]+=1
        for ev in reversed(r.json().get("response",[])):
            if ev.get("type")=="Goal": return f" Scorer: {ev.get('player',{}).get('name','')} ⚽"
        return ""
    except: return ""

def get_news():
    all=[]
    for u in ["https://site.api.espn.com/apis/site/v2/sports/soccer/news","https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/news","https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.champions/news"]:
        try:
            for a in requests.get(u,timeout=3).json().get("articles",[])[:3]:
                if a.get("images"):
                    img=a["images"][0].get("url","")
                    if img: all.append({"id":a["id"],"title":a["headline"],"desc":a.get("description","")[:120],"img":img})
        except: pass
    seen=set(); uniq=[]
    for n in all:
        if n["id"] not in seen: seen.add(n["id"]); uniq.append(n)
    return uniq[:4]

def bot():
    print("V38 LIVESCORE FIRST - NO DELAY SWITCH - ICON NEWS")
    while True:
        try:
            build_schedule()
            # LIVESCORE BETTER - TRY LS FIRST, NO DELAY SWITCH TO OTHERS
            ls=ls_live() # instant, free, best
            if len(ls)<3: # if LS has less than 3 games, add ESPN+API instantly (no delay)
                with ThreadPoolExecutor(max_workers=2) as ex:
                    espn=ex.submit(espn_live).result()
                    api=ex.submit(api_live).result()
                all_games=ls+espn+api
                print(f"SWITCH LS:{len(ls)} + ESPN:{len(espn)} + API:{len(api)} -> {len(all_games)} live")
            else:
                # LS is enough, use LS only to save API
                all_games=ls
                print(f"LS ONLY {len(ls)} live - API saved {USED['api']}/75")

            # Merge - legit check
            merged={}
            for g in all_games:
                norm=g["norm"]
                if norm not in sched.get("games",{}): continue
                if norm not in merged: merged[norm]=g
                else:
                    # If 2 sources agree, keep
                    if merged[norm]["gh"]==g["gh"] and merged[norm]["ga"]==g["ga"]:
                        pass
                    elif g["src"]=="LS": # Livescore better = trust LS
                        merged[norm]=g

            valid=[]
            for norm,g in merged.items():
                last=scores.get(norm,{"gh":0,"ga":0})
                if g["gh"]<last["gh"] or g["ga"]<last["ga"]: continue
                key=f"{norm}-{g['gh']}-{g['ga']}"
                if key in posted: continue
                valid.append(g)

            for g in valid:
                norm=g["norm"]; lg=clean_lg(g["lg"]); t=tags(lg)
                st=g["st"]; m=str(g["m"]); gh=g["gh"]; ga=g["ga"]
                is_ft="FT" in st or "AET" in st; is_ht="HT" in st

                line_k=f"lineup-{norm}"; kick_k=f"kick-{norm}"; goal_k=f"goal-{norm}-{gh}-{ga}"; ht_k=f"ht-{norm}"; ft_k=f"ft-{norm}"

                if line_k not in posted and is_big(lg) and "fid" in g:
                    if fb_text(f"📋 LINEUPS: {g['h']} vs {g['a']}\nLineups confirmed ✅\n{lg}\n\n{t}"):
                        posted[line_k]=True; save()

                if kick_k not in posted:
                    if fb_text(f"⚽ KICKOFF: {g['h']} vs {g['a']}\n{lg} is LIVE now!\n\n{t}"):
                        posted[kick_k]=True; scores[norm]={"gh":gh,"ga":ga}; save()

                last=scores.get(norm,{"gh":0,"ga":0})

                if not is_ft and not is_ht and gh+ga>0 and goal_k not in posted and (gh>last["gh"] or ga>last["ga"]):
                    sc=scorer(g["fid"]) if "fid" in g and is_big(lg) else ""
                    if fb_text(f"⚽ GOOAL! {m}' {g['h']} {gh}-{ga} {g['a']}!{sc}\n{lg}\n\n{t}"):
                        posted[goal_k]=True; scores[norm]={"gh":gh,"ga":ga}; save()

                if is_ht and ht_k not in posted:
                    if fb_text(f"⏸️ HALF TIME: {g['h']} {gh}-{ga} {g['a']}\n{lg}\n\n{t}"):
                        posted[ht_k]=True; save()

                if is_ft and ft_k not in posted and norm in scores:
                    if fb_text(f"✅ FULL TIME: {g['h']} {gh}-{ga} {g['a']}\n{lg}\n\n{t}"):
                        posted[ft_k]=True; save()

            # NEWS WITH UNFILTERED SCORES SMALL ICON DOWN THERE
            if datetime.now().minute%40<4:
                for n in get_news()[:2]:
                    nid=f"news-{n['id']}"
                    if nid not in posted:
                        # Icon down there as footer - small
                        caption=f"📰 {n['title']}\n\n{n['desc']}...\n\n━━━━━━━━━━━━━━━\n🔵 Unfiltered Scores | Live Football Worldwide\n#FootballLive #BreakingNews"
                        if fb_photo(n["img"], caption): posted[nid]=True; save(); time.sleep(2)

            time.sleep(6)
        except Exception as e: print(e); time.sleep(6)

if __name__=="__main__": bot()
