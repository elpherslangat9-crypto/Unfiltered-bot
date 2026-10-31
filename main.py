import os, requests, json
from datetime import datetime, timedelta, timezone

FB_TOKEN = os.getenv("FB_TOKEN")
FB_PAGE_ID = os.getenv("FB_PAGE_ID") or "1293090263895541"
POSTED_FILE="posted.json"
SCORES_FILE="last_scores.json"
EAT=timezone(timedelta(hours=3))
now_eat=datetime.now(EAT)
today=now_eat.strftime("%Y-%m-%d")

# V73.5 CLEAN LEAGUES - 17 Total
LEAGUE_CLEAN={
    "eng.1":"Premier League",
    "eng.2":"Championship",
    "esp.1":"LaLiga",
    "ita.1":"Serie A",
    "ger.1":"Bundesliga",
    "fra.1":"Ligue 1", # Only Ligue 1 now, L2/L3 removed
    "ned.1":"Eredivisie",
    "por.1":"Primeira Liga",
    "sco.1":"Scottish Premiership",
    "tur.1":"Turkish Super Lig", # NEW
    "bel.1":"Belgian Pro League", # NEW
    "gre.1":"Greek Super League", # NEW
    "sui.1":"Swiss Super League", # NEW
    "uefa.champions":"Champions League",
    "uefa.europa":"Europa League",
    "ken.1":"FKF Premier League",
    "rsa.1":"PSL"
}

def load_posted():
    try:
        with open(POSTED_FILE,"r") as f: return set(json.load(f))
    except: return set()
def save_posted(p):
    try:
        with open(POSTED_FILE,"w") as f: json.dump(list(p)[-5000:], f)
    except: pass
def load_scores():
    try:
        with open(SCORES_FILE,"r") as f: return json.load(f)
    except: return {}
def save_scores(s):
    try:
        with open(SCORES_FILE,"w") as f: json.dump(s, f)
    except: pass
def fb_post(msg):
    try:
        r=requests.post(f"https://graph.facebook.com/v20.0/{FB_PAGE_ID}/feed", data={"message":msg,"access_token":FB_TOKEN}, timeout=20)
        print(f"FB {r.status_code}: {msg[:150]}"); return r.status_code==200
    except: return False
def parse_minute(clock_str):
    try:
        if not clock_str: return 0
        num=''.join(filter(str.isdigit, clock_str))
        return int(num) if num else 0
    except: return 0

def get_scorer(eid, lg):
    try:
        url=f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lg}/summary?event={eid}"
        r=requests.get(url, timeout=6)
        j=r.json()
        for ev in j.get("keyEvents",[]):
            txt=ev.get("text","")
            if "Goal" in txt:
                if "-" in txt: return txt.split("-")[-1].strip()[:35]
                return txt[:35]
        for c in j.get("commentary",[]):
            t=c.get("text","")
            if "Goal -" in t: return t.split("Goal -")[-1].split("(")[0].strip()[:35]
        return None
    except: return None

def get_games_livescore():
    """LIVESCORE FAST SOURCE - Primary"""
    games={}
    try:
        # Livescore fast public endpoint
        url="https://prod-public-api.livescore.com/v1/soccer/live"
        headers={"User-Agent":"Mozilla/5.0","Accept":"application/json"}
        r=requests.get(url, timeout=8, headers=headers)
        if r.status_code==200:
            data=r.json()
            for stage in data.get("Stages",[]):
                lname=stage.get("Snm","")
                # Map livescore league to our clean names
                for ev in stage.get("Events",[]):
                    try:
                        if ev.get("Eps")!="L": continue # Only live
                        home=ev.get("T1",[{}])[0].get("Nm","")
                        away=ev.get("T2",[{}])[0].get("Nm","")
                        if not home or not away: continue
                        tr1=ev.get("Tr1","0"); tr2=ev.get("Tr2","0")
                        hg=int(tr1) if str(tr1).isdigit() else 0
                        ag=int(tr2) if str(tr2).isdigit() else 0
                        minute=str(ev.get("Epr",0))+"'"
                        key=f"{home}_vs_{away}"
                        # Map league name
                        clean_league=lname
                        if "turkey" in lname.lower(): clean_league="Turkish Super Lig"
                        if "belgium" in lname.lower(): clean_league="Belgian Pro League"
                        if "greece" in lname.lower(): clean_league="Greek Super League"
                        if "switzerland" in lname.lower(): clean_league="Swiss Super League"
                        games[key]={"home":home,"away":away,"hg":hg,"ag":ag,"league":clean_league,"minute":minute,"eid":ev.get("Eid"),"lg":"tur.1","min_int":parse_minute(minute),"source":"LIVESCORE"}
                    except: continue
            print(f"LIVESCORE source found {len(games)} games")
    except Exception as e:
        print(f"LIVESCORE fail {e}")
    return games

def get_games_espn():
    """ESPN SOURCE - Backup + Main for 17 leagues"""
    games={}
    for lg in LEAGUE_CLEAN.keys():
        try:
            url=f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lg}/scoreboard?dates={today.replace('-','')}"
            r=requests.get(url, timeout=8, headers={"User-Agent":"Mozilla/5.0"})
            data=r.json()
            for ev in data.get("events",[]):
                if ev.get("status",{}).get("type",{}).get("state")!="in": continue
                comps=ev.get("competitions",[{}])[0].get("competitors",[])
                if len(comps)<2: continue
                home=comps[0]["team"]["displayName"] if comps[0].get("homeAway")=="home" else comps[1]["team"]["displayName"]
                away=comps[1]["team"]["displayName"] if comps[0].get("homeAway")=="home" else comps[0]["team"]["displayName"]
                hg=int(comps[0].get("score",0)) if comps[0].get("homeAway")=="home" else int(comps[1].get("score",0))
                ag=int(comps[1].get("score",0)) if comps[0].get("homeAway")=="home" else int(comps[0].get("score",0))
                clock=ev.get("status",{}).get("displayClock","")
                eid=ev.get("id")
                key=f"{home}_vs_{away}"
                if key not in games or (hg+ag)> (games[key]["hg"]+games[key]["ag"]):
                    games[key]={"home":home,"away":away,"hg":hg,"ag":ag,"league":LEAGUE_CLEAN.get(lg, lg),"minute":clock,"eid":eid,"lg":lg,"min_int":parse_minute(clock),"source":"ESPN"}
        except: continue
    print(f"ESPN source found {len(games)} games")
    return games

def main():
    posted=load_posted(); last_scores=load_scores()
    print(f"=== V73.5 HYBRID {now_eat} ===")
    # HYBRID: Livescore first (fast), ESPN second (covers all)
    games_ls=get_games_livescore()
    games_espn=get_games_espn()
    # Merge - Livescore wins if same match (faster)
    games={**games_espn, **games_ls}
    if not games_ls: games=games_espn # If livescore down, use ESPN
    print(f"TOTAL MERGED LIVE: {len(games)} from LIVESCORE={len(games_ls)} ESPN={len(games_espn)}")

    new_scores={}
    for k,g in games.items():
        score_str=f"{g['hg']}-{g['ag']}"
        new_scores[k]={"score":score_str,"league":g["league"],"hg":g["hg"],"ag":g["ag"]}
        prev=last_scores.get(k)
        if not prev:
            if g["min_int"] <= 15: # No fake kick-off at 63'
                pk=f"kick_{k}_{today}"
                if pk not in posted:
                    msg=f"🟢 KICK-OFF\n\n{g['home']} vs {g['away']}\n\n🏆 {g['league']}\n⏰ {g['minute']}\n\n🟢 Unfiltered Scores"
                    if fb_post(msg): posted.add(pk)
        else:
            if g["hg"]>prev.get("hg",0) or g["ag"]>prev.get("ag",0):
                gk=f"goal_{k}_{score_str}_{today}"
                if gk not in posted:
                    scorer=get_scorer(g.get("eid"), g.get("lg","eng.1")) if g.get("source")=="ESPN" else None
                    base=f"🟢 GOAL! {g['minute']}\n\n{g['home']} {score_str} {g['away']}\n\n🏆 {g['league']}"
                    if scorer: base+=f"\n⚽ {scorer}"
                    base+=f"\n\n🟢 Unfiltered Scores"
                    if fb_post(base): posted.add(gk)

    for k, prev in last_scores.items():
        if k not in games:
            fk=f"ft_{k}_{prev.get('score')}_{today}"
            if fk not in posted:
                h,a=k.split("_vs_")
                msg=f"🟢 FULL-TIME\n\n{h} {prev.get('score')} {a}\n\n🏆 {prev.get('league')}\n\n🟢 Unfiltered Scores"
                if fb_post(msg): posted.add(fk)

    save_posted(posted); save_scores(new_scores)
    print(f"V73.5 DONE")

if __name__=="__main__": main()
