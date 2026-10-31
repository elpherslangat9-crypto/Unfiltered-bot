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
        print(f"FB {r.status_code}: {msg[:150]}"); return r.status_code==200
    except: return False
def parse_min(s):
    try: return int(''.join(filter(str.isdigit, s))[:2] or 0)
    except: return 0

def get_real_scorer(eid, lg):
    """V73.7 - Get REAL player name, not commentary"""
    try:
        url=f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lg}/summary?event={eid}"
        r=requests.get(url, timeout=7, headers={"User-Agent":"Mozilla/5.0"})
        j=r.json()
        # METHOD 1: keyEvents with athletes
        for ev in j.get("keyEvents",[]):
            if "Goal" in ev.get("text","") or ev.get("type",{}).get("text")=="Goal":
                # Try athletesInvolved
                if ev.get("athletesInvolved"):
                    name=ev["athletesInvolved"][0].get("displayName")
                    if name and len(name)<30 and "AC Milan" not in name and "Inter" not in name:
                        return name
                # Try text after dash
                txt=ev.get("text","")
                if " - " in txt:
                    cand=txt.split(" - ")[-1].split("(")[0].strip()
                    if cand and len(cand)<30 and "Milan" not in cand: return cand
        # METHOD 2: header details athletesInvolved
        comp=j.get("header",{}).get("competitions",[{}])[0]
        for det in comp.get("details",[]):
            if "Goal" in str(det.get("type",{})):
                ath=det.get("athletesInvolved",[])
                if ath: 
                    name=ath[0].get("displayName")
                    if name and len(name)<30: return name
        return None # If no real name, return None - don't show fake line
    except: return None

def main():
    posted=load_posted(); last_scores=load_scores()
    print(f"=== V73.7 REAL SCORER FIX {now_eat} ===")
    games={}
    for lg, clean_name in LEAGUES.items():
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
                if key not in games or (hg+ag)>(games[key]["hg"]+games[key]["ag"]):
                    games[key]={"home":home,"away":away,"hg":hg,"ag":ag,"league":clean_name,"minute":clock,"eid":eid,"lg":lg,"min_int":parse_min(clock)}
        except: continue

    new_scores={}
    for k,g in games.items():
        score_str=f"{g['hg']}-{g['ag']}"
        new_scores[k]={"score":score_str,"league":g["league"],"hg":g["hg"],"ag":g["ag"]}
        prev=last_scores.get(k)
        if not prev and g["min_int"]<=15:
            pk=f"kick_{k}_{today}"
            if pk not in posted:
                if fb_post(f"🟢 KICK-OFF\n\n{g['home']} vs {g['away']}\n\n🏆 {g['league']}\n⏰ {g['minute']}\n\n🟢 Unfiltered Scores"): posted.add(pk)
        elif prev and (g["hg"]>prev.get("hg",0) or g["ag"]>prev.get("ag",0)):
            gk=f"goal_{k}_{score_str}_{today}"
            if gk not in posted:
                scorer=get_real_scorer(g["eid"], g["lg"])
                print(f"SCORER {k} -> {scorer}")
                base=f"🟢 GOAL! {g['minute']}\n\n{g['home']} {score_str} {g['away']}\n\n🏆 {g['league']}"
                if scorer: base+=f"\n⚽ {scorer}" # Only if real name found
                base+=f"\n\n🟢 Unfiltered Scores"
                if fb_post(base): posted.add(gk)

    save_posted(posted); save_scores(new_scores)
    print(f"V73.7 DONE")

if __name__=="__main__": main()
