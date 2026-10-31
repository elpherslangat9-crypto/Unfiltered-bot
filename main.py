import os, requests, json
from datetime import datetime, timedelta, timezone

# --- CONFIG ---
FB_TOKEN = os.getenv("FB_TOKEN") or os.getenv("FB_PAGE_ACCESS_TOKEN") or os.getenv("FB_PAGE_TOKEN")
FB_PAGE_ID = os.getenv("FB_PAGE_ID") or "1293090263895541"
FOOTBALL_KEY = os.getenv("FOOTBALL_API_KEY") or os.getenv("API_FOOTBALL_KEY")

POSTED_FILE = "posted.json"
COUNT_FILE = "/tmp/api_count.json"

EAT = timezone(timedelta(hours=3))
now_eat = datetime.now(EAT)
today = now_eat.strftime("%Y-%m-%d")
today_ls = now_eat.strftime("%Y%m%d")

# 24 Leagues
ALL_LEAGUES = {
    39:"Premier League",140:"La Liga",2:"Champions League",3:"Europa League",
    78:"Bundesliga",135:"Serie A",61:"Ligue 1",88:"Eredivisie",94:"Primeira Liga",
    40:"Championship",204:"Kenya FKF Premier",202:"Tanzania Premier",203:"Uganda Premier",
    201:"Rwanda Premier",233:"Egypt Premier",235:"Botola",236:"Algeria Ligue 1",
    237:"Tunisia Ligue 1",238:"South Africa PSL",239:"Nigeria NPFL",6:"CAF Champions League",400:"AFCON"
}

# --- HELPERS ---
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
            d=json.load(f); return d["count"] if d["date"]==today else 0
    except: return 0

def save_count(c):
    try:
        os.makedirs(os.path.dirname(COUNT_FILE),exist_ok=True)
        with open(COUNT_FILE,"w") as f: json.dump({"date":today,"count":c}, f)
    except: pass

def fb_post(msg):
    if not FB_TOKEN or not FB_PAGE_ID: return False
    try:
        r=requests.post(f"https://graph.facebook.com/v20.0/{FB_PAGE_ID}/feed",
                        data={"message":msg,"access_token":FB_TOKEN}, timeout=20)
        print(f"FB {r.status_code}: {msg[:120]}")
        return r.status_code==200
    except Exception as e:
        print(f"FB err {e}"); return False

def is_old_game(fixture_date_str):
    """Check if game started more than 4 hours ago - don't post if old"""
    try:
        # API date like 2025-11-07T13:00:00+00:00
        dt_utc = datetime.fromisoformat(fixture_date_str.replace("Z","+00:00"))
        dt_eat = dt_utc.astimezone(EAT)
        age_hours = (now_eat - dt_eat).total_seconds() / 3600
        return age_hours > 4  # Older than 4 hours = skip
    except:
        return False

# --- FETCHERS ---
def fetch_fixtures():
    if not FOOTBALL_KEY or get_count()>=90: 
        print("API limit or no key")
        return []
    try:
        r=requests.get("https://v3.football.api-sports.io/fixtures",
                       headers={"x-apisports-key":FOOTBALL_KEY},
                       params={"date":today}, timeout=15)
        save_count(get_count()+1)
        return r.json().get("response",[])
    except Exception as e:
        print(f"Fetch fixtures err {e}"); return []

def fetch_events(fid):
    if get_count()>=90: return []
    try:
        r=requests.get("https://v3.football.api-sports.io/fixtures/events",
                       headers={"x-apisports-key":FOOTBALL_KEY},
                       params={"fixture":fid}, timeout=12)
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
                    games.append({
                        "home":ev.get("T1",[{}])[0].get("Nm",""),
                        "away":ev.get("T2",[{}])[0].get("Nm",""),
                        "hg":int(ev.get("Tr1",0) or 0),
                        "ag":int(ev.get("Tr2",0) or 0),
                        "status":ev.get("Eps",""),
                        "league":comp
                    })
    except Exception as e: print(f"Free Africa err {e}")
    return games

# --- MAIN LOGIC ---
def main():
    posted=load_posted()
    print(f"=== V65 SAFE KICKOFF->FT POSTED {len(posted)} TIME {now_eat} ===")
    fixtures=fetch_fixtures()
    free_games=fetch_free_africa()
    print(f"API fixtures {len(fixtures)} + Free Africa {len(free_games)}")
    new=False

    for fx in fixtures:
        lid=fx["league"]["id"]
        if lid not in ALL_LEAGUES: continue
        
        home=fx["teams"]["home"]["name"]
        away=fx["teams"]["away"]["name"]
        hg=fx["goals"]["home"]; ag=fx["goals"]["away"]
        status=fx["fixture"]["status"]["short"]
        fid=fx["fixture"]["id"]
        fixture_date=fx["fixture"]["date"]
        league=ALL_LEAGUES[lid]
        score=f"{hg}-{ag}"

        # SAFETY: Don't post old games if you run now!
        if is_old_game(fixture_date):
            # Mark as posted silently, don't post to FB
            posted.add(f"ft_{fid}_{today}")
            posted.add(f"kickoff_{fid}_{today}")
            posted.add(f"ht_{fid}_{today}")
            print(f"SKIP OLD: {home} vs {away} - started >4h ago")
            continue

        # 1. KICKOFF
        if status in ["1H","2H","HT","ET","P","LIVE"]:
            key=f"kickoff_{fid}_{today}"
            if key not in posted:
                if fb_post(f"🟢 KICKOFF: {home} vs {away}\n\n🏆 {league}\n⏰ LIVE now!\n\n#UnfilteredScores #Live"):
                    posted.add(key); new=True

        # 2. HT
        if status=="HT":
            key=f"ht_{fid}_{today}"
            if key not in posted:
                if fb_post(f"⏸️ HT: {home} {score} {away}\n\n🏆 {league}\n\n#UnfilteredScores #HalfTime"):
                    posted.add(key); new=True

        # 3. ALL LIVE EVENTS (Goals, Red, Penalties)
        if status in ["1H","2H","HT","ET","P","LIVE","FT","AET","PEN"]:
            events=fetch_events(fid)
            for ev in events:
                etype=ev.get("type",""); detail=ev.get("detail","") or ""
                minute=ev.get("time",{}).get("elapsed","")
                player=ev.get("player",{}).get("name","") or "Unknown"

                # Missed Penalty
                if etype=="Goal" and "Missed Penalty" in detail:
                    key=f"missed_{fid}_{minute}_{player}_{today}"
                    if key not in posted:
                        msg=f"❌ MISSED PENALTY! {player} ({minute}')\n\n🟢 {home} {score} {away}\n🏆 {league}\n\n#UnfilteredScores #MissedPenalty"
                        if fb_post(msg): posted.add(key); new=True

                # Penalty Goal
                elif etype=="Goal" and "Penalty" in detail:
                    key=f"pen_{fid}_{minute}_{player}_{today}"
                    if key not in posted:
                        msg=f"🎯 PENALTY GOAL! {player} ({minute}')\n\n🟢 {home} {score} {away}\n🏆 {league}\n\n#UnfilteredScores #Penalty"
                        if fb_post(msg): posted.add(key); new=True

                # Normal Goal
                elif etype=="Goal":
                    key=f"goal_{fid}_{minute}_{player}_{today}"
                    if key not in posted:
                        msg=f"⚽ GOAL! {player} ({minute}')\n\n🟢 {home} {score} {away}\n🏆 {league}\n\n#UnfilteredScores #Goal"
                        if fb_post(msg): posted.add(key); new=True

                # Red Card
                elif etype=="Card" and "Red Card" in detail:
                    key=f"red_{fid}_{minute}_{player}_{today}"
                    if key not in posted:
                        msg=f"🔴 RED CARD! {player} ({minute}')\n\n🟢 {home} {score} {away}\n🏆 {league}\n\n#UnfilteredScores #RedCard"
                        if fb_post(msg): posted.add(key); new=True

        # 4. FT
        if status in ["FT","AET","PEN"]:
            key=f"ft_{fid}_{today}"
            if key not in posted:
                if fb_post(f"✅ FT: {home} {hg}-{ag} {away}\n\n🏆 {league}\n\n#UnfilteredScores #FT"):
                    posted.add(key); new=True

    # FREE AFRICA (basic kickoff + goals + FT)
    for g in free_games:
        home=g["home"]; away=g["away"]
        if not home or not away: continue
        hg=g["hg"]; ag=g["ag"]; status=str(g["status"]); league=g["league"]
        score=f"{hg}-{ag}"; fid=f"{home}_{away}"

        if status in ["1H","2H","LIVE"] or status.isdigit():
            k1=f"kickoff_free_{fid}_{today}"
            if k1 not in posted:
                if fb_post(f"🟢 KICKOFF: {home} vs {away}\n\n🏆 {league}"): posted.add(k1); new=True
            if hg+ag>0:
                k2=f"live_free_{fid}_{score}_{today}"
                if k2 not in posted:
                    if fb_post(f"🟢 Live: {home} {score} {away}\n\n🏆 {league}"): posted.add(k2); new=True
        if "FT" in status:
            k3=f"ft_free_{fid}_{today}"
            if k3 not in posted:
                if fb_post(f"✅ FT: {home} {hg}-{ag} {away}\n\n🏆 {league}"): posted.add(k3); new=True

    if new: save_posted(posted)
    else: print("No new posts - all up to date")
    print("V65 DONE - Safe!")

if __name__=="__main__": main()
