import os, requests, json
from datetime import datetime, timedelta, timezone

FB_TOKEN = os.getenv("FB_TOKEN") or os.getenv("FB_PAGE_ACCESS_TOKEN") or os.getenv("FB_PAGE_TOKEN") or os.getenv("FB_PAGE_ACCESS_TOKEN")
FB_PAGE_ID = os.getenv("FB_PAGE_ID") or os.getenv("PAGE_ID") or "1293090263895541"
FOOTBALL_KEY = os.getenv("FOOTBALL_API_KEY") or os.getenv("API_FOOTBALL_KEY") or os.getenv("API_KEY") or os.getenv("FOOTBALL_KEY")

POSTED_FILE="posted.json"; COUNT_FILE="/tmp/api_count.json"
EAT=timezone(timedelta(hours=3))
now_eat=datetime.now(EAT)
today=now_eat.strftime("%Y-%m-%d")
today_ls=now_eat.strftime("%Y%m%d")

ALL_LEAGUES={39:"Premier League",140:"La Liga",2:"Champions League",3:"Europa League",78:"Bundesliga",135:"Serie A",61:"Ligue 1",88:"Eredivisie",94:"Primeira Liga",40:"Championship",204:"Kenya FKF",202:"Tanzania",203:"Uganda",201:"Rwanda",233:"Egypt",235:"Botola",236:"Algeria",237:"Tunisia",238:"South Africa PSL",239:"Nigeria NPFL",6:"CAF Champions",400:"AFCON"}

def load_posted():
    try:
        with open(POSTED_FILE,"r") as f: return set(json.load(f))
    except: return set()
def save_posted(p):
    try:
        with open(POSTED_FILE,"w") as f: json.dump(list(p)[-2000:], f)
    except: pass

def get_count():
    try:
        with open(COUNT_FILE,"r") as f:
            d=json.load(f)
            if d["date"]!=today: return 0
            # FIX: if count stuck at 90, reset to 0 at midnight
            if d["count"]>=95: 
                print("Resetting stuck API count")
                return 0
            return d["count"]
    except: return 0

def save_count(c):
    try:
        os.makedirs(os.path.dirname(COUNT_FILE),exist_ok=True)
        with open(COUNT_FILE,"w") as f: json.dump({"date":today,"count":c}, f)
    except: pass

def fb_post(msg):
    try:
        r=requests.post(f"https://graph.facebook.com/v20.0/{FB_PAGE_ID}/feed", data={"message":msg,"access_token":FB_TOKEN}, timeout=20)
        print(f"FB {r.status_code}: {msg[:120]}")
        return r.status_code==200
    except Exception as e:
        print(f"FB err {e}"); return False

def is_old_game(fixture_date_str):
    try:
        dt_utc=datetime.fromisoformat(fixture_date_str.replace("Z","+00:00"))
        dt_eat=dt_utc.astimezone(EAT)
        age=(now_eat-dt_eat).total_seconds()/3600
        return age>3.5
    except: return False

def fetch_fixtures():
    if not FOOTBALL_KEY:
        print(f"NO FOOTBALL_KEY! Found env: FOOTBALL_API_KEY={bool(os.getenv('FOOTBALL_API_KEY'))} API_FOOTBALL_KEY={bool(os.getenv('API_FOOTBALL_KEY'))}")
        return []
    if get_count()>=90:
        print(f"API limit {get_count()}/90 - using free only")
        return []
    try:
        r=requests.get("https://v3.football.api-sports.io/fixtures", headers={"x-apisports-key":FOOTBALL_KEY}, params={"date":today}, timeout=15)
        print(f"API-Football status {r.status_code} count {get_count()}")
        save_count(get_count()+1)
        if r.status_code!=200:
            print(r.text[:500])
            return []
        return r.json().get("response",[])
    except Exception as e:
        print(f"Fetch fixtures err {e}"); return []

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
            if any(k in comp.lower() for k in ["kenya","tanzania","uganda","rwanda","psl","south africa","egypt","morocco","botola","nigeria","caf","gor","simba","yanga"]):
                for ev in stage.get("Events",[]):
                    status=ev.get("Eps","")
                    # ONLY LIVE games, ignore FT for free to avoid spam
                    if status in ["1H","2H","HT","LIVE"] or status.isdigit():
                        games.append({
                            "home":ev.get("T1",[{}])[0].get("Nm",""),
                            "away":ev.get("T2",[{}])[0].get("Nm",""),
                            "hg":int(ev.get("Tr1",0) or 0),
                            "ag":int(ev.get("Tr2",0) or 0),
                            "status":status,
                            "league":comp
                        })
        print(f"Free Africa LIVE only: {len(games)} games")
    except Exception as e: print(f"Free Africa err {e}")
    return games

def main():
    posted=load_posted()
    is_first_run = len(posted)==0
    print(f"=== V66 NO-SPAM KICKOFF->FT POSTED {len(posted)} FIRST_RUN={is_first_run} TIME {now_eat} ===")
    
    if is_first_run:
        print("FIRST RUN - Will populate posted.json silently to avoid spamming old FTs!")

    fixtures=fetch_fixtures()
    free_games=fetch_free_africa()
    print(f"API fixtures {len(fixtures)} + Free Africa LIVE {len(free_games)} + API count {get_count()}")
    new=False

    for fx in fixtures:
        lid=fx["league"]["id"]
        if lid not in ALL_LEAGUES: continue
        home=fx["teams"]["home"]["name"]; away=fx["teams"]["away"]["name"]
        hg=fx["goals"]["home"]; ag=fx["goals"]["away"]
        status=fx["fixture"]["status"]["short"]; fid=fx["fixture"]["id"]
        fixture_date=fx["fixture"]["date"]; league=ALL_LEAGUES[lid]; score=f"{hg}-{ag}"

        # SAFETY: Skip old games completely
        if is_old_game(fixture_date):
            posted.add(f"ft_{fid}_{today}")
            posted.add(f"kickoff_{fid}_{today}")
            posted.add(f"ht_{fid}_{today}")
            print(f"SKIP OLD (>{3.5}h): {home} vs {away}")
            continue

        # If first run, don't post, just mark as seen
        if is_first_run and status in ["FT","AET","PEN","HT"]:
            posted.add(f"ft_{fid}_{today}")
            posted.add(f"ht_{fid}_{today}")
            posted.add(f"kickoff_{fid}_{today}")
            continue

        # KICKOFF
        if status in ["1H","2H","HT","ET","P","LIVE"]:
            key=f"kickoff_{fid}_{today}"
            if key not in posted:
                if not is_first_run:
                    if fb_post(f"🟢 KICKOFF: {home} vs {away}\n\n🏆 {league}\n⏰ LIVE now!\n\n#UnfilteredScores #Live"):
                        posted.add(key); new=True
                else:
                    posted.add(key)

        # HT
        if status=="HT":
            key=f"ht_{fid}_{today}"
            if key not in posted:
                if not is_first_run:
                    if fb_post(f"⏸️ HT: {home} {score} {away}\n\n🏆 {league}\n\n#UnfilteredScores #HalfTime"):
                        posted.add(key); new=True
                else:
                    posted.add(key)

        # LIVE EVENTS
        if status in ["1H","2H","HT","ET","P","LIVE","FT","AET","PEN"]:
            events=fetch_events(fid)
            for ev in events:
                etype=ev.get("type",""); detail=ev.get("detail","") or ""
                minute=ev.get("time",{}).get("elapsed",""); player=ev.get("player",{}).get("name","") or "Unknown"

                if etype=="Goal" and "Missed Penalty" in detail:
                    key=f"missed_{fid}_{minute}_{player}_{today}"
                    if key not in posted and not is_first_run:
                        if fb_post(f"❌ MISSED PENALTY! {player} ({minute}')\n\n🟢 {home} {score} {away}\n🏆 {league}"): posted.add(key); new=True
                elif etype=="Goal" and "Penalty" in detail:
                    key=f"pen_{fid}_{minute}_{player}_{today}"
                    if key not in posted and not is_first_run:
                        if fb_post(f"🎯 PENALTY GOAL! {player} ({minute}')\n\n🟢 {home} {score} {away}\n🏆 {league}"): posted.add(key); new=True
                elif etype=="Goal":
                    key=f"goal_{fid}_{minute}_{player}_{today}"
                    if key not in posted and not is_first_run:
                        if fb_post(f"⚽ GOAL! {player} ({minute}')\n\n🟢 {home} {score} {away}\n🏆 {league}"): posted.add(key); new=True
                elif etype=="Card" and "Red Card" in detail:
                    key=f"red_{fid}_{minute}_{player}_{today}"
                    if key not in posted and not is_first_run:
                        if fb_post(f"🔴 RED CARD! {player} ({minute}')\n\n🟢 {home} {score} {away}\n🏆 {league}"): posted.add(key); new=True

        # FT
        if status in ["FT","AET","PEN"]:
            key=f"ft_{fid}_{today}"
            if key not in posted:
                if not is_first_run:
                    if fb_post(f"✅ FT: {home} {hg}-{ag} {away}\n\n🏆 {league}"):
                        posted.add(key); new=True
                else:
                    posted.add(key); print(f"First run skip FT: {home} vs {away}")

    # FREE AFRICA LIVE ONLY
    for g in free_games:
        home=g["home"]; away=g["away"]
        if not home or not away: continue
        hg=g["hg"]; ag=g["ag"]; status=str(g["status"]); league=g["league"]; score=f"{hg}-{ag}"; fid=f"{home}_{away}"
        key=f"live_free_{fid}_{score}_{today}"
        if key not in posted and not is_first_run and hg+ag>0:
            if fb_post(f"🟢 Live: {home} {score} {away}\n\n🏆 {league}"):
                posted.add(key); new=True

    if len(posted)>0:
        save_posted(posted)
        if is_first_run:
            print(f"FIRST RUN DONE - Saved {len(posted)} old games as seen, no spam! Next run will post only NEW live events!")
        else:
            print(f"Saved {len(posted)}")
    print("V66 DONE - Safe No Spam!")

if __name__=="__main__": main()
