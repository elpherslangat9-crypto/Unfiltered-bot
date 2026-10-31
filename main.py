import os, requests, json
from datetime import datetime, timedelta, timezone

FB_TOKEN = os.getenv("FB_TOKEN") or os.getenv("FB_PAGE_TOKEN") or os.getenv("FB_PAGE_ACCESS_TOKEN")
FB_PAGE_ID = os.getenv("FB_PAGE_ID") or "1293090263895541"

POSTED_FILE="posted.json"
SCORES_FILE="last_scores.json"
EAT=timezone(timedelta(hours=3))
now_eat=datetime.now(EAT)
today=now_eat.strftime("%Y-%m-%d")
today_ls=now_eat.strftime("%Y%m%d")

ALLOWED=["premier league","la liga","bundesliga","serie a","ligue 1","eredivisie","primeira liga","championship","champions league","europa league","eng.1","esp.1","ger.1","ita.1","fra.1","ned.1","por.1","uefa","kenya","tanzania","uganda","rwanda","egypt","morocco","botola","algeria","tunisia","psl","south africa","nigeria","npfl","caf","afcon","gor mahia","simba","yanga","al ahly","zamalek","raja","wydad","fkf"]

def load_posted():
    try:
        with open(POSTED_FILE,"r") as f: return set(json.load(f))
    except: return set()
def save_posted(p):
    if len(p)==0: p.add(f"init_{today}")
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

def allowed(name): return any(w in name.lower() for w in ALLOWED)

def get_scorer_espn(event_id, league_code):
    """Try to get last scorer from ESPN summary"""
    try:
        url=f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_code}/summary?event={event_id}"
        r=requests.get(url, timeout=6, headers={"User-Agent":"Mozilla/5.0"})
        data=r.json()
        # Check scoring plays
        for play in data.get("header",{}).get("competitions",[{}])[0].get("details",[]):
            pass
        # Check commentary / keyEvents
        for item in data.get("commentary",[])[:5]:
            txt=item.get("text","")
            if "goal" in txt.lower() or "score" in txt.lower():
                # try extract name
                if "-" in txt: return txt.split("-")[-1][:40].strip()
        # Check boxscore scoring
        for team in data.get("boxscore",{}).get("players",[]):
            for pl in team.get("statistics",[]):
                for st in pl.get("keys",[]):
                    pass
        # Last scoring play from header
        plays=data.get("header",{}).get("competitions",[{}])[0].get("situation",{}).get("lastPlay",{}).get("text","")
        if plays and len(plays)>5: return plays[:50]
        return None
    except: return None

def fetch_games():
    games=[]
    try:
        for lg in ["eng.1","esp.1","ger.1","ita.1","fra.1","ned.1","por.1","uefa.champions","uefa.europa","ken.1","rsa.1","ecu.1"]:
            try:
                url=f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lg}/scoreboard?dates={today.replace('-','')}"
                r=requests.get(url, timeout=8, headers={"User-Agent":"Mozilla/5.0"})
                data=r.json()
                for ev in data.get("events",[]):
                    if ev.get("status",{}).get("type",{}).get("state")!="in": continue
                    comp=ev.get("league",{}).get("name",lg)
                    if not allowed(comp): continue
                    comps=ev.get("competitions",[{}])[0].get("competitors",[])
                    if len(comps)<2: continue
                    eid=ev.get("id","")
                    home=comps[0]["team"]["displayName"] if comps[0].get("homeAway")=="home" else comps[1]["team"]["displayName"]
                    away=comps[1]["team"]["displayName"] if comps[0].get("homeAway")=="home" else comps[0]["team"]["displayName"]
                    hg=int(comps[0].get("score",0)) if comps[0].get("homeAway")=="home" else int(comps[1].get("score",0))
                    ag=int(comps[1].get("score",0)) if comps[0].get("homeAway")=="home" else int(comps[0].get("score",0))
                    clock=ev.get("status",{}).get("displayClock","0")
                    try: min_i=int(''.join(filter(str.isdigit, clock))[:3] or 0)
                    except: min_i=0
                    # try get scorer
                    scorer=get_scorer_espn(eid, lg)
                    games.append({"key":f"{home}_vs_{away}","home":home,"away":away,"hg":hg,"ag":ag,"league":comp,"minute":min_i,"scorer":scorer,"eid":eid})
            except: continue
        print(f"GAMES LIVE: {len(games)}")
    except Exception as e: print(f"Fetch err {e}")
    return games

def main():
    posted=load_posted()
    last_scores=load_scores()
    print(f"=== V73.2 MATCH CORNER STYLE {now_eat} POSTED {len(posted)} ===")
    merged={}
    for g in fetch_games():
        k=g["key"]
        if k not in merged or (g["hg"]+g["ag"]) > (merged[k]["hg"]+merged[k]["ag"]):
            merged[k]=g
    new_scores={}
    for k,g in merged.items():
        home=g["home"]; away=g["away"]; hg=g["hg"]; ag=g["ag"]; league=g["league"]; minute=g["minute"]; scorer=g.get("scorer")
        score_str=f"{hg}-{ag}"
        new_scores[k]={"score":score_str,"league":league,"hg":hg,"ag":ag,"minute":minute}
        prev=last_scores.get(k)
        if not prev:
            pk=f"kick_{k}_{today}"
            if pk not in posted:
                msg=f"🟢 KICK-OFF: {home} vs {away}\n\n🏆 {league}\n⏰ {minute}'"
                if fb_post(msg): posted.add(pk)
        else:
            prev_hg=prev.get("hg",0); prev_ag=prev.get("ag",0)
            if hg>prev_hg or ag>prev_ag:
                gk=f"goal_{k}_{score_str}_{today}"
                if gk not in posted:
                    # MATCH CORNER STYLE
                    if hg>prev_hg and ag==prev_ag:
                        base=f"🟢 GOAL! {minute}' - {home} {score_str} {away}\n\n🏆 {league}"
                    elif ag>prev_ag and hg==prev_hg:
                        base=f"🟢 GOAL! {minute}' - {home} {score_str} {away}\n\n🏆 {league}"
                    else:
                        base=f"🟢 GOALS! {minute}' - {home} {score_str} {away}\n\n🏆 {league}"
                    if scorer and len(scorer)>3:
                        base+=f"\n⚽ Scorer: {scorer}"
                    # brand footer
                    base+=f"\n\n🟢 Live Updates"
                    if fb_post(base): posted.add(gk)
                    print(f"GOAL {k} {prev.get('score')}->{score_str} scorer={scorer}")

    # FT
    for k, prev in last_scores.items():
        if k not in new_scores:
            fk=f"ft_{k}_{prev.get('score')}_{today}"
            if fk not in posted:
                h,a=k.split("_vs_")
                msg=f"🟢 FULL-TIME: {h} {prev.get('score')} {a}\n\n🏆 {prev.get('league')}\n\n🟢 Live Updates"
                if fb_post(msg): posted.add(fk)

    save_posted(posted); save_scores(new_scores)
    print(f"V73.2 DONE posted={len(posted)} tracking={len(new_scores)}")

if __name__=="__main__": main()
