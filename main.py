import os, requests, json
from datetime import datetime, timedelta, timezone

FB_TOKEN = os.getenv("FB_TOKEN")
FB_PAGE_ID = os.getenv("FB_PAGE_ID") or "1293090263895541"
POSTED_FILE="posted.json"
SCORES_FILE="last_scores.json"
EAT=timezone(timedelta(hours=3))
now_eat=datetime.now(EAT)
today=now_eat.strftime("%Y-%m-%d")

LEAGUE_CLEAN={"eng.1":"Premier League","eng.2":"Championship","esp.1":"LaLiga","esp.2":"LaLiga2","ita.1":"Serie A","ger.1":"Bundesliga","fra.1":"Ligue 2","fra.2":"Ligue 2","ned.1":"Eredivisie","ned.2":"Eerste Divisie","por.1":"Primeira Liga","sco.1":"Scottish Premiership","uefa.champions":"Champions League","uefa.europa":"Europa League","ken.1":"FKF Premier League","rsa.1":"South Africa PSL","fra.3":"National"}

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
    except Exception as e: print(f"FB err {e}"); return False

def get_scorer_details(eid, lg):
    """Get scorer from ESPN details"""
    try:
        url=f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lg}/summary?event={eid}"
        r=requests.get(url, timeout=6, headers={"User-Agent":"Mozilla/5.0"})
        j=r.json()
        # 1. Try details array
        details=j.get("header",{}).get("competitions",[{}])[0].get("details",[])
        for d in details:
            # each detail has scoring
            if d.get("type",{}).get("text")=="Goal" or "Goal" in str(d):
                athletes=d.get("athletesInvolved",[])
                if athletes: return athletes[0].get("displayName","")
                # fallback text
                txt=d.get("clock",{}).get("displayValue","")+" "+d.get("team",{}).get("displayName","")
        # 2. Try keyEvents
        for ev in j.get("keyEvents",[]):
            if "Goal" in ev.get("text","") or "goal" in ev.get("type",{}).get("text","").lower():
                return ev.get("text","").split("-")[-1].strip()[:40] if "-" in ev.get("text","") else ev.get("text","")[:40]
        # 3. Commentary
        for c in j.get("commentary",[]):
            t=c.get("text","")
            if "Goal!" in t or "Goal -" in t:
                # "Goal! Troyes 1-0... (Player Name)"
                if "(" in t and ")" in t:
                    return t.split("(")[-1].split(")")[0][:35]
                return t.split("Goal!")[-1].split("-")[-1][:35].strip()
        return None
    except Exception as e:
        print(f"Scorer err {e}")
        return None

def main():
    posted=load_posted(); last_scores=load_scores()
    print(f"=== V73.4 CLEAN BRAND {now_eat} POSTED {len(posted)} ===")
    games={}
    for lg in LEAGUE_CLEAN.keys():
        try:
            url=f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lg}/scoreboard?dates={today.replace('-','')}"
            r=requests.get(url, timeout=8, headers={"User-Agent":"Mozilla/5.0"})
            data=r.json()
            for ev in data.get("events",[]):
                if ev.get("status",{}).get("type",{}).get("state")!="in": continue
                comp=ev.get("competitions",[{}])[0]
                comps=comp.get("competitors",[])
                if len(comps)<2: continue
                home=comps[0]["team"]["displayName"] if comps[0].get("homeAway")=="home" else comps[1]["team"]["displayName"]
                away=comps[1]["team"]["displayName"] if comps[0].get("homeAway")=="home" else comps[0]["team"]["displayName"]
                hg=int(comps[0].get("score",0)) if comps[0].get("homeAway")=="home" else int(comps[1].get("score",0))
                ag=int(comps[1].get("score",0)) if comps[0].get("homeAway")=="home" else int(comps[0].get("score",0))
                clock=ev.get("status",{}).get("displayClock","")
                eid=ev.get("id")
                key=f"{home}_vs_{away}"
                if key not in games or (hg+ag)> (games[key]["hg"]+games[key]["ag"]):
                    games[key]={"home":home,"away":away,"hg":hg,"ag":ag,"league":LEAGUE_CLEAN.get(lg, lg),"minute":clock,"eid":eid,"lg":lg}
        except: continue

    new_scores={}
    for k,g in games.items():
        score_str=f"{g['hg']}-{g['ag']}"
        new_scores[k]={"score":score_str,"league":g["league"],"hg":g["hg"],"ag":g["ag"]}
        prev=last_scores.get(k)
        if not prev:
            pk=f"kick_{k}_{today}"
            if pk not in posted:
                msg=f"🟢 KICK-OFF\n\n{g['home']} vs {g['away']}\n\n🏆 {g['league']}\n⏰ {g['minute']}\n\n🟢 Unfiltered Scores"
                if fb_post(msg): posted.add(pk)
        else:
            if g["hg"]>prev.get("hg",0) or g["ag"]>prev.get("ag",0):
                gk=f"goal_{k}_{score_str}_{today}"
                if gk not in posted:
                    scorer=get_scorer_details(g["eid"], g["lg"])
                    print(f"SCORER FETCH {k} eid={g['eid']} => {scorer}")
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
    print(f"V73.4 DONE posted={len(posted)}")

if __name__=="__main__": main()
