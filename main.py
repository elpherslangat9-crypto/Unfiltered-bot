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
AFRICA_WORDS=["kenya","tanzania","uganda","rwanda","egypt","morocco","botola","algeria","tunisia","psl","south africa","nigeria","npfl","caf","afcon","ethiopia","zambia","gor mahia","simba","yanga"]

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
        print(f"FB {r.status_code}: {msg[:100]}"); return r.status_code==200
    except Exception as e: print(f"FB err {e}"); return False

def fetch_fixtures():
    if not FOOTBALL_KEY: return []
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

def fetch_free_africa():
    games=[]
    try:
        url=f"https://prod-public-api.livescore.com/v1/api/app/date/soccer/{today_ls}/3.00?MD=1"
        r=requests.get(url, timeout=12, headers={"User-Agent":"Mozilla/5.0","Referer":"https://www.livescore.com/"})
        for stage in r.json().get("Stages",[]):
            comp=stage.get("Cnm","")+" "+stage.get("Snm","")
            if not any(w in comp.lower() for w in AFRICA_WORDS): continue
            for ev in stage.get("Events",[]):
                status=ev.get("Eps","")
                if status in ["1H","2H","HT","LIVE"] or status.isdigit():
                    games.append({"home":ev.get("T1",[{}])[0].get("Nm",""),"away":ev.get("T2",[{}])[0].get("Nm",""),"hg":int(ev.get("Tr1",0) or 0),"ag":int(ev.get("Tr2",0) or 0),"status":status,"league":comp})
        print(f"Free Africa (Africa only): {len(games)}")
    except Exception as e: print(f"Free err {e}")
    return games

def main():
    posted=load_posted(); print(f"=== V70 ARTIFACT TIME {now_eat} POSTED {len(posted)} ===")
    fixtures=fetch_fixtures(); free_games=fetch_free_africa()
    print(f"API {len(fixtures)} + Free Africa {len(free_games)} count {get_count()}")
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
    for g in free_games:
        home=g["home"]; away=g["away"]
        if not home or not away: continue
        hg=g["hg"]; ag=g["ag"]; league=g["league"]; score=f"{hg}-{ag}"; fid=f"{home}_{away}"
        k=f"free_{fid}_{score}_{today}"
        if k not in posted and hg+ag>0:
            if fb_post(f"🟢 Live: {home} {score} {away}\n\n🏆 {league}"): posted.add(k)
    save_posted(posted); print(f"V70 DONE posted={len(posted)}")

if __name__=="__main__": main()
