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
        with open(POSTED_FILE,"r") as f:
            d=json.load(f); print(f"Loaded {len(d)} posted from ARTIFACT"); return set(d)
    except: print("No posted.json"); return set()

def save_posted(p):
    if len(p)==0: p.add(f"init_{today}")
    try:
        with open(POSTED_FILE,"w") as f: json.dump(list(p)[-5000:], f)
        print(f"Saved {len(p)} posted")
    except Exception as e: print(f"Save err {e}")

def load_scores():
    try:
        with open(SCORES_FILE,"r") as f:
            d=json.load(f); print(f"Loaded {len(d)} last scores"); return d
    except: print("No last_scores.json"); return {}

def save_scores(s):
    try:
        with open(SCORES_FILE,"w") as f: json.dump(s, f)
        print(f"Saved {len(s)} last scores")
    except Exception as e: print(f"Score save err {e}")

def fb_post(msg):
    try:
        r=requests.post(f"https://graph.facebook.com/v20.0/{FB_PAGE_ID}/feed", data={"message":msg,"access_token":FB_TOKEN}, timeout=20)
        print(f"FB {r.status_code}: {msg[:130]}"); return r.status_code==200
    except Exception as e: print(f"FB err {e}"); return False

def allowed(name):
    return any(w in name.lower() for w in ALLOWED)

def fetch_livescore():
    games=[]
    try:
        url=f"https://prod-public-api.livescore.com/v1/api/app/date/soccer/{today_ls}/3.00?MD=1"
        r=requests.get(url, timeout=12, headers={"User-Agent":"Mozilla/5.0","Referer":"https://www.livescore.com/"})
        data=r.json()
        for stage in data.get("Stages",[]):
            comp=stage.get("Cnm","")+" "+stage.get("Snm","")
            if not allowed(comp): continue
            for ev in stage.get("Events",[]):
                eps=ev.get("Eps",""); # LIVE status
                if eps not in ["1H","2H","HT","ET"] and not (isinstance(eps,str) and eps.isdigit()): continue
                t1=ev.get("T1",[{}]); t2=ev.get("T2",[{}])
                home=t1[0].get("Nm","") if t1 else ""; away=t2[0].get("Nm","") if t2 else ""
                if not home or not away: continue
                hg=int(ev.get("Tr1",0) or 0); ag=int(ev.get("Tr2",0) or 0)
                # minute
                try: minute=int(ev.get("Esd",0) or eps or 0) if str(eps).isdigit() else int(ev.get("Esd",0) or 0)
                except: minute=0
                games.append({"key":f"{home}_vs_{away}","home":home,"away":away,"hg":hg,"ag":ag,"league":comp,"minute":minute,"source":"LIVESCORE","status":eps})
        print(f"LIVESCORE: {len(games)}")
    except Exception as e: print(f"LS err {e}")
    return games

def fetch_flashscore_backup():
    games=[]
    try:
        for lg in ["eng.1","esp.1","ger.1","ita.1","fra.1","ned.1","por.1","uefa.champions","uefa.europa","ken.1","rsa.1"]:
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
                    home=comps[0]["team"]["displayName"] if comps[0].get("homeAway")=="home" else comps[1]["team"]["displayName"]
                    away=comps[1]["team"]["displayName"] if comps[0].get("homeAway")=="home" else comps[0]["team"]["displayName"]
                    hg=int(comps[0].get("score",0)) if comps[0].get("homeAway")=="home" else int(comps[1].get("score",0))
                    ag=int(comps[1].get("score",0)) if comps[0].get("homeAway")=="home" else int(comps[0].get("score",0))
                    minute=ev.get("status",{}).get("displayClock","0")
                    try: min_i=int(''.join(filter(str.isdigit, minute))[:2] or 0)
                    except: min_i=0
                    games.append({"key":f"{home}_vs_{away}","home":home,"away":away,"hg":hg,"ag":ag,"league":comp,"minute":min_i,"source":"FLASHSCORE","status":"LIVE"})
            except: continue
        print(f"FLASHSCORE: {len(games)}")
    except Exception as e: print(f"FS err {e}")
    return games

def main():
    posted=load_posted()
    last_scores=load_scores() # dict: "Home_vs_Away" -> {"score":"1-0","league":"...","hg":1,"ag":0}
    print(f"=== V73.1 PURE LIVESCORE TIME {now_eat} POSTED {len(posted)} TRACKED {len(last_scores)} ===")

    ls=fetch_livescore()
    fs=fetch_flashscore_backup()
    all_games=ls+fs

    # Merge - keep latest score (highest total)
    merged={}
    for g in all_games:
        k=g["key"]
        if k not in merged or (g["hg"]+g["ag"]) > (merged[k]["hg"]+merged[k]["ag"]):
            merged[k]=g

    new_scores={}
    # --- LIVE TRACKING ---
    for k,g in merged.items():
        home=g["home"]; away=g["away"]; hg=g["hg"]; ag=g["ag"]; league=g["league"]; minute=g["minute"]; source=g["source"]
        score_str=f"{hg}-{ag}"
        new_scores[k]={"score":score_str,"league":league,"hg":hg,"ag":ag,"minute":minute}

        prev_data=last_scores.get(k)
        if not prev_data:
            # KICKOFF - new game
            pk=f"kick_{k}_{today}"
            if pk not in posted:
                if fb_post(f"🟢 KICKOFF: {home} vs {away}\n\n🏆 {league}\n📡 {source}"): posted.add(pk)
        else:
            prev_hg=prev_data.get("hg",0); prev_ag=prev_data.get("ag",0)
            # GOAL?
            if hg>prev_hg or ag>prev_ag:
                gk=f"goal_{k}_{score_str}_{today}"
                if gk not in posted:
                    if hg>prev_hg and ag==prev_ag:
                        msg=f"⚽ GOAL! {home} {score_str} {away} ({minute}')\n\n🏆 {league}\n📡 {source}"
                    elif ag>prev_ag and hg==prev_hg:
                        msg=f"⚽ GOAL! {away} scores! {home} {score_str} {away} ({minute}')\n\n🏆 {league}\n📡 {source}"
                    else:
                        msg=f"⚽ GOALS! {home} {score_str} {away} ({minute}')\n\n🏆 {league}\n📡 {source}"
                    if fb_post(msg): posted.add(gk)
                    print(f"GOAL {k}: {prev_data.get('score')} -> {score_str}")

    # --- FT TRACKING: was live before, now not live = finished ---
    for k, prev_data in last_scores.items():
        if k not in new_scores:
            # Match finished
            score=prev_data.get("score","0-0"); league=prev_data.get("league","")
            fk=f"ft_{k}_{score}_{today}"
            if fk not in posted:
                home, away = k.split("_vs_")
                if fb_post(f"✅ FT: {home} {score} {away}\n\n🏆 {league}"):
                    posted.add(fk)
                    print(f"FT {k} {score}")

    save_posted(posted)
    save_scores(new_scores)
    print(f"V73.1 DONE posted={len(posted)} tracking={len(new_scores)}")

if __name__=="__main__": main()
