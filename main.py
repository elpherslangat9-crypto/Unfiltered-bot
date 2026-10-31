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

def load_posted():
    try:
        with open(POSTED_FILE,"r") as f: 
            data=json.load(f)
            print(f"Loaded posted.json: {len(data)} keys")
            return set(data)
    except Exception as e:
        print(f"No posted.json: {e}")
        return set()

def save_posted(p):
    try:
        with open(POSTED_FILE,"w") as f: json.dump(list(p)[-2000:], f)
        print(f"Saved posted.json: {len(p)} keys")
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
        print(f"FB {r.status_code}: {msg[:100]}")
        return r.status_code==200
    except Exception as e: print(f"FB err {e}"); return False

def is_old_game(fixture_date_str):
    try:
        dt_utc=datetime.fromisoformat(fixture_date_str.replace("Z","+00:00"))
        dt_eat=dt_utc.astimezone(EAT)
        return (now_eat-dt_eat).total_seconds()/3600>4
    except: return False

def fetch_fixtures():
    if not FOOTBALL_KEY: return []
    if get_count()>=85: return []
    try:
        # Try 1: date=today
        r=requests.get("https://v3.football.api-sports.io/fixtures", headers={"x-apisports-key":FOOTBALL_KEY}, params={"date":today}, timeout=15)
        save_count(get_count()+1)
        data=r.json().get("response",[])
        print(f"API date={today} returned {len(data)}")
        # Try 2: if 0, try live=all
        if len(data)==0:
            r2=requests.get("https://v3.football.api-sports.io/fixtures", headers={"x-apisports-key":FOOTBALL_KEY}, params={"live":"all"}, timeout=15)
            save_count(get_count()+1)
            data=r2.json().get("response",[])
            print(f"API live=all returned {len(data)}")
        return data
    except Exception as e:
        print(f"Fetch err {e}"); return []

def fetch_events(fid):
    if get_count()>=90: return []
    try:
        r=requests.get("https://v3.football.api-sports.io/fixtures/events", headers={"x-apisports-key":FOOTBALL_KEY}, params={"fixture":fid}, timeout=12)
        save_count(get_count()+1)
        return r.json().get("response",[])
    except: return []

def fetch_free_africa():
    games=[]
    try:
        url=f"https://prod-public-api.livescore.com/v1/api/app/date/soccer/{today_ls}/3.00?MD=1"
        r=requests.get(url, timeout=12, headers={"User-Agent":"Mozilla/5.0","Referer":"https://www.livescore.com/"})
        for stage in r.json().get("Stages",[]):
            comp=stage.get("Cnm","")+" "+stage.get("Snm","")
            for ev in stage.get("Events",[]):
                status=ev.get("Eps","")
                if status in ["1H","2H","HT","LIVE"] or status.isdigit():
                    games.append({"home":ev.get("T1",[{}])[0].get("Nm",""),"away":ev.get("T2",[{}])[0].get("Nm",""),"hg":int(ev.get("Tr1",0) or 0),"ag":int(ev.get("Tr2",0) or 0),"status":status,"league":comp})
        print(f"Free Africa LIVE: {len(games)}")
    except Exception as e: print(f"Free err {e}")
    return games

def main():
    posted=load_posted()
    is_first=len(posted)==0
    print(f"=== V67 FIX POSTED {len(posted)} FIRST={is_first} TIME {now_eat} ===")
    fixtures=fetch_fixtures()
    free_games=fetch_free_africa()
    print(f"API {len(fixtures)} + Free {len(free_games)} + count {get_count()}")
    new=False

    for fx in fixtures:
        if fx["league"]["id"] not in ALL_LEAGUES: continue
        home=fx["teams"]["home"]["name"]; away=fx["teams"]["away"]["name"]
        hg=fx["goals"]["home"]; ag=fx["goals"]["away"]; status=fx["fixture"]["status"]["short"]
        fid=fx["fixture"]["id"]; fdate=fx["fixture"]["date"]; league=ALL_LEAGUES[fx["league"]["id"]]; score=f"{hg}-{ag}"

        if is_old_game(fdate):
            posted.add(f"ft_{fid}_{today}"); posted.add(f"kickoff_{fid}_{today}"); posted.add(f"ht_{fid}_{today}")
            continue

        if is_first:
            posted.add(f"ft_{fid}_{today}"); posted.add(f"kickoff_{fid}_{today}"); posted.add(f"ht_{fid}_{today}")
            # also add event keys to avoid spam
            for ev in fetch_events(fid):
                posted.add(f"goal_{fid}_{ev.get('time',{}).get('elapsed','')}_{ev.get('player',{}).get('name','')}_{today}")
            continue

        if status in ["1H","2H","HT","ET","P","LIVE"]:
            k=f"kickoff_{fid}_{today}"
            if k not in posted:
                if fb_post(f"🟢 KICKOFF: {home} vs {away}\n\n🏆 {league}"): posted.add(k); new=True
        if status=="HT":
            k=f"ht_{fid}_{today}"
            if k not in posted:
                if fb_post(f"⏸️ HT: {home} {score} {away}\n\n🏆 {league}"): posted.add(k); new=True

        if status in ["1H","2H","HT","ET","P","LIVE","FT","AET","PEN"]:
            for ev in fetch_events(fid):
                etype=ev.get("type",""); detail=ev.get("detail","") or ""; minute=ev.get("time",{}).get("elapsed",""); player=ev.get("player",{}).get("name","") or "Unknown"
                if etype=="Goal" and "Missed Penalty" in detail:
                    k=f"missed_{fid}_{minute}_{player}_{today}"
                    if k not in posted:
                        if fb_post(f"❌ MISSED PENALTY! {player} ({minute}')\n\n🟢 {home} {score} {away}\n🏆 {league}"): posted.add(k); new=True
                elif etype=="Goal" and "Penalty" in detail:
                    k=f"pen_{fid}_{minute}_{player}_{today}"
                    if k not in posted:
                        if fb_post(f"🎯 PENALTY GOAL! {player} ({minute}')\n\n🟢 {home} {score} {away}\n🏆 {league}"): posted.add(k); new=True
                elif etype=="Goal":
                    k=f"goal_{fid}_{minute}_{player}_{today}"
                    if k not in posted:
                        if fb_post(f"⚽ GOAL! {player} ({minute}')\n\n🟢 {home} {score} {away}\n🏆 {league}"): posted.add(k); new=True
                elif etype=="Card" and "Red Card" in detail:
                    k=f"red_{fid}_{minute}_{player}_{today}"
                    if k not in posted:
                        if fb_post(f"🔴 RED CARD! {player} ({minute}')\n\n🟢 {home} {score} {away}\n🏆 {league}"): posted.add(k); new=True

        if status in ["FT","AET","PEN"]:
            k=f"ft_{fid}_{today}"
            if k not in posted:
                if fb_post(f"✅ FT: {home} {hg}-{ag} {away}\n\n🏆 {league}"): posted.add(k); new=True

    # Always save, even on first run!
    save_posted(posted)
    if is_first:
        print("FIRST RUN - No spam, saved all old games. Next run will post LIVE only!")
    print("V67 DONE")

if __name__=="__main__": main()
