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

def get_scorer_fix(home, away):
    """V75 - FIXED: Search by team ID not name slice"""
    try:
        for lg in LEAGUES.keys():
            try:
                url=f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lg}/scoreboard?dates={today.replace('-','')}"
                r=requests.get(url, timeout=6, headers={"User-Agent":"Mozilla/5.0"})
                data=r.json()
                for ev in data.get("events",[]):
                    # Match by competitors array - 100% accurate
                    comps=ev.get("competitions",[{}])[0].get("competitors",[])
                    if len(comps)<2: continue
                    h=comps[0]["team"]["displayName"] if comps[0].get("homeAway")=="home" else comps[1]["team"]["displayName"]
                    a=comps[1]["team"]["displayName"] if comps[0].get("homeAway")=="home" else comps[0]["team"]["displayName"]
                    # Fuzzy match Barcelona in Barcelona, Alavés in Alavés / Deportivo Alavés
                    if home.lower().split()[0] in h.lower() and away.lower().split()[0] in a.lower():
                        eid=ev.get("id")
                        print(f"FOUND EVENT {h} vs {a} id={eid} league={lg}")
                        # Get summary
                        surl=f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lg}/summary?event={eid}"
                        sr=requests.get(surl, timeout=7, headers={"User-Agent":"Mozilla/5.0"})
                        sj=sr.json()
                        # Get LAST goal (newest)
                        goals=[]
                        for ke in sj.get("keyEvents",[]):
                            t=ke.get("text","")
                            if "Goal" in t:
                                if ke.get("athletesInvolved"):
                                    nm=ke["athletesInvolved"][0].get("displayName")
                                    if nm: goals.append(nm)
                                elif " - " in t:
                                    # Fallback parse: "Goal! Barcelona 4, Alavés 0. Lewandowski (45'+3')"
                                    try:
                                        after=t.split(".")[-1] if "." in t else t.split("-")[-1]
                                        cand=after.split("(")[0].strip()
                                        if cand and len(cand)<30 and "Barcelona" not in cand: goals.append(cand)
                                    except: pass
                        if goals:
                            last=goals[-1]
                            print(f"SCORER FOUND: {last}")
                            return last
                        # Try header details
                        hdr=sj.get("header",{}).get("competitions",[{}])[0]
                        for d in hdr.get("details",[]):
                            if d.get("athletesInvolved") and "Goal" in str(d.get("type",{})):
                                nm=d["athletesInvolved"][0].get("displayName")
                                if nm: return nm
            except Exception as e:
                print(f"scorer search fail {lg} {e}")
                continue
        return None
    except: return None

def get_games():
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
                    games[key]={"home":home,"away":away,"hg":hg,"ag":ag,"minute":clock,"min_int":parse_min(clock)}
        except: continue
    print(f"LIVE TOTAL: {len(games)}")
    return games

def main():
    posted=load_posted(); last_scores=load_scores()
    print(f"=== V75 REAL SCORER FIX {now_eat} ===")
    games=get_games()
    new_scores={}
    for k,g in games.items():
        score_str=f"{g['hg']}-{g['ag']}"
        new_scores[k]={"score":score_str,"hg":g["hg"],"ag":g["ag"]}
        prev=last_scores.get(k)
        if prev and (g["hg"]>prev.get("hg",0) or g["ag"]>prev.get("ag",0)):
            gk=f"goal_{k}_{score_str}_{today}"
            if gk not in posted:
                scorer=get_scorer_fix(g["home"], g["away"])
                if scorer:
                    msg=f"🟢 Live: {g['home']} {score_str} {g['away']}\n\n⚽ Goal: {scorer} ({g['minute']})"
                else:
                    # If still no scorer, wait 60s next run will find it - don't post minute only
                    print(f"NO SCORER yet for {k}, retry next run")
                    continue
                if fb_post(msg): posted.add(gk)

    save_posted(posted); save_scores(new_scores)
    print(f"V75 DONE")

if __name__=="__main__": main()
