import os, requests, json
from datetime import datetime, timedelta, timezone

FB_TOKEN = os.getenv("FB_TOKEN") or os.getenv("FB_PAGE_TOKEN") or os.getenv("FB_PAGE_ACCESS_TOKEN")
FB_PAGE_ID = os.getenv("FB_PAGE_ID") or "1293090263895541"
FOOTBALL_KEY = os.getenv("FOOTBALL_API_KEY") or os.getenv("API_FOOTBALL_KEY") or os.getenv("API_KEY")

POSTED_FILE="posted.json"; COUNT_FILE="/tmp/api_count.json"
EAT=timezone(timedelta(hours=3))
now_eat=datetime.now(EAT)
today=now_eat.strftime("%Y-%m-%d")
today_ls=now_eat.strftime("%Y%m%d")

ALL_LEAGUES={39:"Premier League",140:"La Liga",2:"Champions League",3:"Europa League",78:"Bundesliga",135:"Serie A",61:"Ligue 1",88:"Eredivisie",94:"Primeira Liga",40:"Championship",204:"Kenya FKF",202:"Tanzania",203:"Uganda",201:"Rwanda",233:"Egypt",235:"Botola",236:"Algeria",237:"Tunisia",238:"South Africa PSL",239:"Nigeria NPFL",6:"CAF Champions",400:"AFCON"}

# ONLY THESE WORDS ALLOWED IN FREE BACKUP - NO HUNGARY!
ALLOWED_WORDS=["premier league","la liga","bundesliga","serie a","ligue 1","eredivisie","primeira liga","championship","champions league","europa league","eng.1","esp.1","ger.1","ita.1","fra.1","ned.1","por.1","uefa","kenya","tanzania","uganda","rwanda","egypt","morocco","botola","algeria","tunisia","psl","south africa","nigeria","npfl","caf","afcon","gor mahia","simba","yanga","al ahly","zamalek","raja","wydad"]

ESPN_LEAGUES=["eng.1","esp.1","ger.1","ita.1","fra.1","ned.1","por.1","uefa.champions","uefa.europa"]

def load_posted():
    try:
        with open(POSTED_FILE,"r") as f:
            d=json.load(f); print(f"Loaded {len(d)} keys from ARTIFACT"); return set(d)
    except: print("No posted.json - first artifact run"); return set()

def save_posted(p):
    if len(p)==0: p.add(f"init_{today}")
    try:
        with open(POSTED_FILE,"w") as f: json.dump(list(p)[-2000:], f)
        print(f"Saved {len(p)} keys to artifact")
    except Exception as e: print(f"Save err {e}")

def get_count():
    try:
        with open(COUNT_FILE,"r") as f:
            d=json.load(f); return 0 if d["date"]!=today else d["count"]
    except: return 0
def save_count(c):
    try:
        os.makedirs(os.path.dirname(COUNT_FILE),exist_ok=True)
        with open(COUNT_FILE,"w") as f: json.dump({"date":today,"count":c}, f)
    except: pass

def fb_post(msg):
    try:
        r=requests.post(f"https://graph.facebook.com/v20.0/{FB_PAGE_ID}/feed", data={"message":msg,"access_token":FB_TOKEN}, timeout=20)
        print(f"FB {r.status_code}: {msg[:110]}"); return r.status_code==200
    except Exception as e: print(f"FB err {e}"); return False

def fetch_fixtures():
    if not FOOTBALL_KEY: return []
    if get_count()>=85:
        print(f"API count {get_count()} >=85 - SKIP API, use FREE!")
        return []
    try:
        r=requests.get("https://v3.football.api-sports.io/fixtures", headers={"x-apisports-key":FOOTBALL_KEY}, params={"date":today}, timeout=15)
        save_count(get_count()+1); data=r.json().get("response",[]); print(f"API date={today} -> {len(data)}")
        if len(data)==0:
            r2=requests.get("https://v3.football.api-sports.io/fixtures", headers={"x-apisports-key":FOOTBALL_KEY}, params={"live":"all"}, timeout=15)
            save_count(get_count()+1); data=r2.json().get("response",[]); print(f"API live=all -> {len(data)}")
        return data
    except Exception as e: print(f"API err {e}"); return []

def fetch_events(fid):
    if get_count()>=90: return []
    try:
        r=requests.get("https://v3.football.api-sports.io/fixtures/events", headers={"x-apisports-key":FOOTBALL_KEY}, params={"fixture":fid}, timeout=12)
        save_count(get_count()+1); return r.json().get("response",[])
    except: return []

def is_allowed(league_name):
    low=league_name.lower()
    return any(w in low for w in ALLOWED_WORDS)

def fetch_free_livescore_all():
    games=[]
    try:
        url=f"https://prod-public-api.livescore.com/v1/api/app/date/soccer/{today_ls}/3.00?MD=1"
        r=requests.get(url, timeout=12, headers={"User-Agent":"Mozilla/5.0","Referer":"https://www.livescore.com/"})
        for stage in r.json().get("Stages",[]):
            comp=stage.get("Cnm","")+" "+stage.get("Snm","")
            if not is_allowed(comp): continue
            for ev in stage.get("Events",[]):
                status=ev.get("Eps","")
                if status in ["1H","2H","HT","LIVE"] or status.isdigit():
                    t1=ev.get("T1",[{}]); t2=ev.get("T2",[{}])
                    home=t1[0].get("Nm","") if t1 else ""; away=t2[0].get("Nm","") if t2 else ""
                    games.append({"home":home,"away":away,"hg":int(ev.get("Tr1",0) or 0),"ag":int(ev.get("Tr2",0) or 0),"status":status,"league":comp,"source":"livescore"})
        print(f"Livescore FREE (filtered Top+Africa): {len(games)}")
    except Exception as e: print(f"Livescore err {e}")
    return games

def fetch_free_espn():
    games=[]
    try:
        for lg in ESPN_LEAGUES:
            try:
                url=f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lg}/scoreboard?dates={today.replace('-','')}"
                r=requests.get(url, timeout=10, headers={"User-Agent":"Mozilla/5.0"})
                data=r.json()
                for ev in data.get("events",[]):
                    status=ev.get("status",{}).get("type",{}).get("state","")
                    if status!="in": continue
                    comp=ev.get("league",{}).get("name",lg)
                    if not is_allowed(comp): continue
                    competitors=ev.get("competitions",[{}])[0].get("competitors",[])
                    if len(competitors)<2: continue
                    home=competitors[0].get("team",{}).get("displayName","") if competitors[0].get("homeAway")=="home" else competitors[1].get("team",{}).get("displayName","")
                    away=competitors[1].get("team",{}).get("displayName","") if competitors[0].get("homeAway")=="home" else competitors[0].get("team",{}).get("displayName","")
                    hg=int(competitors[0].get("score",0)) if competitors[0].get("homeAway")=="home" else int(competitors[1].get("score",0))
                    ag=int(competitors[1].get("score",0)) if competitors[0].get("homeAway")=="home" else int(competitors[0].get("score",0))
                    games.append({"home":home,"away":away,"hg":hg,"ag":ag,"status":"LIVE","league":comp,"source":"espn"})
            except: continue
        print(f"ESPN FREE (filtered): {len(games)}")
    except Exception as e: print(f"ESPN err {e}")
    return games

def main():
    posted=load_posted(); print(f"=== V72 FILTERED TIME {now_eat} POSTED {len(posted)} COUNT {get_count()} ===")
    fixtures=fetch_fixtures()
    free_all=fetch_free_livescore_all()
    espn_games=fetch_free_espn()
    use_free = len(fixtures)==0 or get_count()>=85
    print(f"API {len(fixtures)} FREE_MODE={use_free} Livescore {len(free_all)} ESPN {len(espn_games)}")

    for fx in fixtures:
        if fx["league"]["id"] not in ALL_LEAGUES: continue
        home=fx["teams"]["home"]["name"]; away=fx["teams"]["away"]["name"]; hg=fx["goals"]["home"]; ag=fx["goals"]["away"]
        status=fx["fixture"]["status"]["short"]; fid=fx["fixture"]["id"]; league=ALL_LEAGUES[fx["league"]["id"]]; score=f"{hg}-{ag}"
        if status in ["1H","2H","HT","ET","P","LIVE"]:
            k=f"kickoff_{fid}_{today}"
            if k not in posted:
                if fb_post(f"🟢 KICKOFF: {home} vs {away}\n\n🏆 {league}"): posted.add(k)
        if status=="HT":
            k=f"ht_{fid}_{today}"
            if k not in posted:
                if fb_post(f"⏸️ HT: {home} {score} {away}\n\n🏆 {league}"): posted.add(k)
        if status in ["1H","2H","HT","ET","P","LIVE","FT","AET","PEN"]:
            for ev in fetch_events(fid):
                etype=ev.get("type",""); detail=ev.get("detail","") or ""; minute=ev.get("time",{}).get("elapsed",""); player=ev.get("player",{}).get("name","") or "Unknown"
                if etype=="Goal" and "Missed Penalty" in detail:
                    k=f"missed_{fid}_{minute}_{player}_{today}"
                    if k not in posted:
                        if fb_post(f"❌ MISSED PENALTY! {player} ({minute}')\n\n🟢 {home} {score} {away}\n🏆 {league}"): posted.add(k)
                elif etype=="Goal" and "Penalty" in detail:
                    k=f"pen_{fid}_{minute}_{player}_{today}"
                    if k not in posted:
                        if fb_post(f"🎯 PENALTY GOAL! {player} ({minute}')\n\n🟢 {home} {score} {away}\n🏆 {league}"): posted.add(k)
                elif etype=="Goal":
                    k=f"goal_{fid}_{minute}_{player}_{today}"
                    if k not in posted:
                        if fb_post(f"⚽ GOAL! {player} ({minute}')\n\n🟢 {home} {score} {away}\n🏆 {league}"): posted.add(k)
                elif etype=="Card" and "Red Card" in detail:
                    k=f"red_{fid}_{minute}_{player}_{today}"
                    if k not in posted:
                        if fb_post(f"🔴 RED CARD! {player} ({minute}')\n\n🟢 {home} {score} {away}\n🏆 {league}"): posted.add(k)
        if status in ["FT","AET","PEN"]:
            k=f"ft_{fid}_{today}"
            if k not in posted:
                if fb_post(f"✅ FT: {home} {hg}-{ag} {away}\n\n🏆 {league}"): posted.add(k)

    all_free=free_all+espn_games
    seen={}
    for g in all_free:
        key=f"{g['home']}_{g['away']}"
        if key not in seen or (g["hg"]+g["ag"] > seen[key]["hg"]+seen[key]["ag"]):
            seen[key]=g
    for g in seen.values():
        home=g["home"]; away=g["away"]
        if not home or not away: continue
        hg=g["hg"]; ag=g["ag"]; league=g["league"]; source=g["source"]; score=f"{hg}-{ag}"; fid=f"{home}_{away}"
        k=f"free_{fid}_{score}_{today}_{source}"
        if k not in posted and hg+ag>0:
            if fb_post(f"🟢 LIVE ({source.upper()}): {home} {score} {away}\n\n🏆 {league}"): posted.add(k)

    save_posted(posted); print(f"V72 DONE posted={len(posted)} API_count={get_count()} FREE_MODE={use_free}")

if __name__=="__main__": main()
