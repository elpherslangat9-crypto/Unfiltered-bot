import os, requests, json
from datetime import datetime, timedelta, timezone

FB_TOKEN = os.getenv("FB_TOKEN")
FB_PAGE_ID = os.getenv("FB_PAGE_ID") or "1293090263895541"
POSTED_FILE="posted.json"
SCORES_FILE="last_scores.json"
EAT=timezone(timedelta(hours=3))
now_eat=datetime.now(EAT)
today=now_eat.strftime("%Y-%m-%d")

LEAGUES={
    "eng.1":"Premier League","esp.1":"LaLiga","ita.1":"Serie A","ger.1":"Bundesliga",
    "fra.1":"Ligue 1","ned.1":"Eredivisie","por.1":"Primeira Liga",
    "tur.1":"Turkish Super Lig","bel.1":"Belgian Pro League","gre.1":"Greek Super League",
    "sui.1":"Swiss Super League","uefa.champions":"Champions League",
    "uefa.europa":"Europa League","ken.1":"FKF Premier League"
}

def load_posted():
    try:
        with open(POSTED_FILE,"r") as f: return set(json.load(f))
    except: return set()
def save_posted(p):
    with open(POSTED_FILE,"w") as f: json.dump(list(p)[-5000:], f)
def load_scores():
    try:
        with open(SCORES_FILE,"r") as f: return json.load(f)
    except: return {}
def save_scores(s):
    with open(SCORES_FILE,"w") as f: json.dump(s, f)
def fb_post(msg):
    try:
        r=requests.post(f"https://graph.facebook.com/v20.0/{FB_PAGE_ID}/feed", data={"message":msg,"access_token":FB_TOKEN}, timeout=20)
        print(f"FB {r.status_code}: {msg}"); return r.status_code==200
    except: return False
def parse_min(s):
    try: return int(''.join(filter(str.isdigit, str(s)))[:2] or 0)
    except: return 0

def get_games_livescore():
    """FAST SOURCE - Livescore.com - 10s faster than ESPN"""
    games={}
    try:
        # Livescore public fast API
        url="https://prod-public-api.livescore.com/v1/soccer/live"
        headers={"User-Agent":"Mozilla/5.0","Accept":"application/json"}
        r=requests.get(url, timeout=8, headers=headers)
        if r.status_code==200:
            data=r.json()
            for stage in data.get("Stages",[]):
                lname=stage.get("Snm","").lower()
                # Only our 14 leagues
                if not any(x in lname for x in ["premier","laliga","serie","bundes","ligue 1","eredivisie","primeira","turk","belg","greek","swiss","champions","europa","kenya"]):
                    continue
                for ev in stage.get("Events",[]):
                    if ev.get("Eps")!="L": continue
                    try:
                        t1=ev.get("T1",[{}])[0].get("Nm","")
                        t2=ev.get("T2",[{}])[0].get("Nm","")
                        if not t1 or not t2: continue
                        tr1=ev.get("Tr1","0"); tr2=ev.get("Tr2","0")
                        hg=int(tr1) if str(tr1).isdigit() else 0
                        ag=int(tr2) if str(tr2).isdigit() else 0
                        minute=f"{ev.get('Epr',0)}'"
                        key=f"{t1}_vs_{t2}"
                        games[key]={"home":t1,"away":t2,"hg":hg,"ag":ag,"minute":minute,"min_int":parse_min(minute),"source":"LIVESCORE","eid":ev.get("Eid")}
                    except: continue
            print(f"LIVESCORE FAST: {len(games)} live games")
    except Exception as e:
        print(f"LIVESCORE fail {e}")
    return games

def get_games_espn():
    """BACKUP + Scorer names - ESPN"""
    games={}
    for lg in LEAGUES.keys():
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
                key=f"{home}_vs_{away}"
                if key not in games or (hg+ag)>(games[key]["hg"]+games[key]["ag"]):
                    games[key]={"home":home,"away":away,"hg":hg,"ag":ag,"minute":clock,"min_int":parse_min(clock),"source":"ESPN","eid":ev.get("id"),"lg":lg}
        except: continue
    print(f"ESPN BACKUP: {len(games)} live games")
    return games

def get_scorer(eid, lg):
    if not eid or not lg: return None
    try:
        url=f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lg}/summary?event={eid}"
        r=requests.get(url, timeout=7, headers={"User-Agent":"Mozilla/5.0"})
        j=r.json()
        for ev in j.get("keyEvents",[]):
            if "Goal" in ev.get("text","") and ev.get("athletesInvolved"):
                return ev["athletesInvolved"][0].get("displayName")
        return None
    except: return None

def main():
    posted=load_posted(); last_scores=load_scores()
    print(f"=== V73.9 LIVESCORE + ESPN HYBRID {now_eat} ===")
    # HYBRID: Livescore FIRST (fast), ESPN SECOND (scorer)
    ls_games=get_games_livescore()
    espn_games=get_games_espn()
    # Merge: Livescore wins for speed, ESPN adds missing
    games={**espn_games, **ls_games}
    # If livescore has game, try to enrich with ESPN data for scorer
    for k in list(games.keys()):
        if k in espn_games and k in ls_games:
            games[k]["lg"]=espn_games[k].get("lg")
            games[k]["eid_espn"]=espn_games[k].get("eid")

    print(f"TOTAL LIVE: {len(games)} (LIVESCORE {len(ls_games)} + ESPN {len(espn_games)})")
    new_scores={}
    for k,g in games.items():
        score_str=f"{g['hg']}-{g['ag']}"
        new_scores[k]={"score":score_str,"hg":g["hg"],"ag":g["ag"]}
        prev=last_scores.get(k)
        if prev and (g["hg"]>prev.get("hg",0) or g["ag"]>prev.get("ag",0)):
            gk=f"goal_{k}_{score_str}_{g['minute']}_{today}"
            if gk not in posted:
                # Get scorer from ESPN if we have it
                lg=g.get("lg") or g.get("lg_espn") or "eng.1"
                eid=g.get("eid_espn") or g.get("eid")
                scorer=get_scorer(eid, lg) if g.get("source")=="ESPN" or "eid_espn" in g else None
                if scorer:
                    msg=f"🟢 Live: {g['home']} {score_str} {g['away']}\n\n⚽ Goal: {scorer} ({g['minute']})"
                else:
                    msg=f"🟢 Live: {g['home']} {score_str} {g['away']}\n\n⚽ Goal: {g['minute']}"
                print(f"POSTING FROM {g['source']}: {msg}")
                if fb_post(msg): posted.add(gk)

    save_posted(posted); save_scores(new_scores)
    print(f"V73.9 DONE - LIVESCORE PRIMARY")

if __name__=="__main__": main()
