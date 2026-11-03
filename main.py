import os, requests, json
from datetime import datetime, timedelta, timezone

FB_TOKEN = os.getenv("FB_TOKEN")
FB_PAGE_ID = os.getenv("FB_PAGE_ID") or "1293090263895541"
POSTED_FILE="posted.json"
SCORES_FILE="last_scores.json"
EVENTS_FILE="last_events.json"
EAT=timezone(timedelta(hours=3))
now_eat=datetime.now(EAT)
today=now_eat.strftime("%Y-%m-%d")

LEAGUES={
    "eng.1":"Premier League","esp.1":"LaLiga","ita.1":"Serie A","ger.1":"Bundesliga",
    "fra.1":"Ligue 1","ned.1":"Eredivisie","por.1":"Primeira Liga",
    "tur.1":"Turkish Super Lig","bel.1":"Belgian Pro League",
    "sco.1":"Scottish Premiership","aut.1":"Austrian Bundesliga",
    "sui.1":"Swiss Super League","den.1":"Danish Superliga",
    "sau.1":"Saudi Pro League",
    "uefa.champions":"Champions League",
    "uefa.europa":"Europa League",
    "uefa.europa.conf":"Conference League"
}

COUNTRY_HASHTAGS={
    "Premier League":"#EPL #England #PremierLeague #Arsenal #ManCity #Liverpool #Chelsea #ManUtd #FootballUK",
    "LaLiga":"#LaLiga #Spain #RealMadrid #Barcelona",
    "Serie A":"#SerieA #Italy #Juventus #Inter #ACMilan",
    "Bundesliga":"#Bundesliga #Germany #Bayern #Dortmund",
    "Ligue 1":"#Ligue1 #France #PSG #Paris",
    "Eredivisie":"#Eredivisie #Netherlands #Ajax",
    "Primeira Liga":"#PrimeiraLiga #Portugal #Benfica #Porto",
    "Turkish Super Lig":"#SuperLig #Turkey #Galatasaray #Fenerbahce #Besiktas",
    "Belgian Pro League":"#JupilerProLeague #Belgium",
    "Scottish Premiership":"#SPFL #Scotland #Celtic #Rangers",
    "Saudi Pro League":"#SaudiProLeague #SPL #SaudiArabia #Ronaldo #AlNassr #AlHilal #RoshnSaudiLeague",
    "Champions League":"#UCL #ChampionsLeague #UCLLive",
    "Europa League":"#UEL #EuropaLeague",
    "Conference League":"#UECL #ConferenceLeague",
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
def load_events():
    try:
        with open(EVENTS_FILE,"r") as f: return json.load(f)
    except: return {}
def save_events(e):
    with open(EVENTS_FILE,"w") as f: json.dump(e, f)

def fb_post(msg):
    try:
        payload={"message":msg,"access_token":FB_TOKEN,"privacy":{"value":"EVERYONE"}}
        r=requests.post(f"https://graph.facebook.com/v20.0/{FB_PAGE_ID}/feed", data=payload, timeout=20)
        print(f"FB POST {r.status_code}: {r.text[:600]}")
        return r.status_code==200
    except Exception as e:
        print(f"FB FAIL: {e}")
        return False

def parse_min(s):
    try: return int(''.join(filter(str.isdigit, str(s)))[:2] or 0)
    except: return 0

def get_hashtags(league_name):
    base="#LiveScores #UnfilteredScores #FootballLive"
    extra=COUNTRY_HASHTAGS.get(league_name, "#Football")
    return f"{base} {extra} #FYP #Viral #Trending #ForYou #Explore #NonFollowers"

def get_livescore_live():
    """Livescores.com PRIMARY - from Kick off to FT"""
    live={}
    try:
        url="https://prod-public-api.livescore.com/v1/api/app/date/soccer/all/today?MD=1&countryCode=KE"
        r=requests.get(url, timeout=6, headers={"User-Agent":"Mozilla/5.0"})
        if r.status_code!=200: return live
        data=r.json()
        for stage in data.get("Stages",[]):
            lg=stage.get("Snm","")
            for ev in stage.get("Events",[]):
                eid=str(ev.get("Eid",""))
                t1=ev.get("T1",[{}])[0].get("Nm","") if ev.get("T1") else ""
                t2=ev.get("T2",[{}])[0].get("Nm","") if ev.get("T2") else ""
                if not t1 or not t2: continue
                # Scores
                tr1=ev.get("Tr1",""); tr2=ev.get("Tr2","")
                # Status: 1H, 2H, HT, FT, etc
                es=ev.get("Es","") # 1=not started, 2=1st half, 3=HT, 4=2nd half, etc
                epr=ev.get("Epr","") # minute
                # Events - red, penalty, var
                key=f"{t1}_vs_{t2}"
                live[key]={
                    "source":"livescore",
                    "home":t1,"away":t2,
                    "hg":int(tr1) if str(tr1).isdigit() else 0,
                    "ag":int(tr2) if str(tr2).isdigit() else 0,
                    "minute":str(epr),
                    "status":str(es),
                    "raw":ev
                }
        print(f"LIVESCORE PRIMARY: {len(live)} live games from kickoff to FT")
    except Exception as e:
        print(f"Livescore fetch fail: {e}")
    return live

def get_espn_games():
    all_games=[]
    for lg_key, lg_name in LEAGUES.items():
        try:
            url=f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lg_key}/scoreboard?dates={today.replace('-','')}"
            r=requests.get(url, timeout=8, headers={"User-Agent":"Mozilla/5.0"})
            data=r.json()
            for ev in data.get("events",[]):
                status=ev.get("status",{}).get("type",{}).get("state")
                detail=ev.get("status",{}).get("type",{}).get("detail","")
                short_detail=ev.get("status",{}).get("type",{}).get("shortDetail","")
                date_str=ev.get("date","")
                comps=ev.get("competitions",[{}])[0].get("competitors",[])
                if len(comps)<2: continue
                home=comps[0]["team"]["displayName"] if comps[0].get("homeAway")=="home" else comps[1]["team"]["displayName"]
                away=comps[1]["team"]["displayName"] if comps[0].get("homeAway")=="home" else comps[0]["team"]["displayName"]
                hg=int(comps[0].get("score",0)) if comps[0].get("homeAway")=="home" else int(comps[1].get("score",0))
                ag=int(comps[1].get("score",0)) if comps[0].get("homeAway")=="home" else int(comps[0].get("score",0))
                clock=ev.get("status",{}).get("displayClock","")
                eid=ev.get("id")
                try:
                    kickoff_dt=datetime.fromisoformat(date_str.replace("Z","+00:00"))
                    kickoff_eat=kickoff_dt.astimezone(EAT)
                except:
                    kickoff_eat=None
                all_games.append({
                    "league_key":lg_key,"league_name":lg_name,"id":eid,
                    "home":home,"away":away,"hg":hg,"ag":ag,
                    "state":status,"detail":detail,"short":short_detail,
                    "clock":clock,"min_int":parse_min(clock),
                    "kickoff_eat":kickoff_eat,"date_str":date_str
                })
        except: continue
    return all_games

def get_espn_key_events(league_key, event_id):
    """Get red cards, penalties, VAR from ESPN"""
    try:
        surl=f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_key}/summary?event={event_id}"
        sr=requests.get(surl, timeout=7, headers={"User-Agent":"Mozilla/5.0"})
        sj=sr.json()
        events=[]
        for ke in sj.get("keyEvents",[]):
            text=ke.get("text","")
            minute=ke.get("clock",{}).get("displayValue","")
            athlete=""
            if ke.get("athletesInvolved"):
                athlete=ke["athletesInvolved"][0].get("displayName","")
            # Detect type
            typ="goal"
            if "Red Card" in text: typ="red"
            elif "Yellow" in text: typ="yellow"
            elif "Penalty" in text and "Goal" not in text: typ="penalty_miss"
            elif "Penalty" in text and "Goal" in text: typ="penalty_goal"
            elif "VAR" in text: typ="var"
            elif "Goal" in text: typ="goal"
            else: continue
            events.append({"type":typ,"text":text,"minute":minute,"athlete":athlete})
        return events
    except: return []

def main():
    posted=load_posted(); last_scores=load_scores(); last_events=load_events()
    print(f"=== V78 LIVESCORES PRIMARY FROM KICKOFF TO FT + RED/PENALTY/VAR {now_eat} ===")

    # 1. Get Livescores as PRIMARY from kickoff to FT
    livescore_games=get_livescore_live()
    espn_games=get_espn_games()
    new_scores={}; new_events={}

    # Build lookup for ESPN by name
    espn_lookup={}
    for g in espn_games:
        k1=f"{g['home']}_vs_{g['away']}"
        k2=f"{g['away']}_vs_{g['home']}"
        espn_lookup[k1]=g
        espn_lookup[k2]=g

    # Process all games - Livescore primary
    all_keys=set(list(livescore_games.keys()) + [f"{g['home']}_vs_{g['away']}" for g in espn_games])

    for key in all_keys:
        # Prefer Livescore data, fallback to ESPN
        ls=livescore_games.get(key)
        es=espn_lookup.get(key)

        # Determine best source - Livescore from kickoff to FT
        if ls:
            home=ls["home"]; away=ls["away"]; hg=ls["hg"]; ag=ls["ag"]
            minute=ls["minute"]; status=ls["status"]
            league_name=es["league_name"] if es else "Football"
            league_key=es["league_key"] if es else "eng.1"
            event_id=es["id"] if es else None
            kickoff_eat=es["kickoff_eat"] if es else None
            # Map livescore status to state
            if status in ["1","2"]: state="in" # not started or 1st half
            elif status in ["3"]: state="ht"
            elif status in ["4","5"]: state="in" # 2nd half
            elif status in ["6","7"]: state="post" # FT
            else: state=es["state"] if es else "in"
        elif es:
            home=es["home"]; away=es["away"]; hg=es["hg"]; ag=es["ag"]
            minute=str(es["min_int"]); league_name=es["league_name"]
            league_key=es["league_key"]; event_id=es["id"]
            kickoff_eat=es["kickoff_eat"]; state=es["state"]
        else:
            continue

        score_str=f"{hg}-{ag}"
        new_scores[key]={"score":score_str,"hg":hg,"ag":ag,"state":state}
        hashtags=get_hashtags(league_name)

        # ===== LINEUP 60 MINS BEFORE - EPL & UCL =====
        if es and league_key in ["eng.1","uefa.champions"] and es["state"]=="pre" and es["kickoff_eat"]:
            minutes_to_kick=(es["kickoff_eat"] - now_eat).total_seconds()/60
            if 55 <= minutes_to_kick <= 65:
                gk_lineup=f"lineup_{key}_{today}"
                if gk_lineup not in posted:
                    # Try get lineup
                    lineup=None
                    try:
                        surl=f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_key}/summary?event={event_id}"
                        sr=requests.get(surl, timeout=7, headers={"User-Agent":"Mozilla/5.0"})
                        sj=sr.json()
                        lineups=sj.get("lineups",[])
                        if lineups:
                            txt=[]
                            for team in lineups[:2]:
                                tname=team.get("team",{}).get("displayName","Team")
                                starters=[p.get("athlete",{}).get("displayName","") for p in team.get("roster",[]) if p.get("position","")!="Bench"][:11]
                                starters=[s for s in starters if s][:11]
                                if starters: txt.append(f"🔵 {tname}: {', '.join(starters[:7])}...")
                            if txt: lineup="\n".join(txt)
                    except: pass
                    if lineup:
                        msg=f"📋 LINEUPS ALERT - 1 HOUR TO KICK OFF!\n\n🔥 {home} vs {away}\n🏆 {league_name}\n⏰ {es['kickoff_eat'].strftime('%H:%M')} EAT\n\n{lineup}\n\nWho wins? 👇\n\n{hashtags}"
                        if fb_post(msg): posted.add(gk_lineup)
                    else:
                        print(f"Lineup not yet for {key}, retry next run")

        # ===== KICK OFF - USE LIVESCORES FROM KICKOFF =====
        if state=="in" and (minute in ["1","0"] or (es and "1st Half" in es.get("detail",""))):
            gk=f"kickoff_{key}_{today}"
            if gk not in posted:
                msg=f"⏰ KICK OFF!\n\n🔥 {home} vs {away}\n🏆 {league_name}\n\n⚽ Live from Kick Off - Updates Every Minute!\n\n{hashtags}"
                if fb_post(msg): posted.add(gk)

        # ===== GOAL - LIVESCORES PRIMARY, IF DISAGREE TRUST LIVESCORES =====
        prev=last_scores.get(key)
        if prev and (hg>prev.get("hg",0) or ag>prev.get("ag",0)):
            # Even if ESPN disagrees, trust Livescore because it's primary from kickoff to FT
            gk=f"goal_{key}_{score_str}_{today}"
            if gk not in posted:
                # Try get scorer from ESPN
                scorer=None
                if event_id and league_key:
                    try:
                        surl=f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_key}/summary?event={event_id}"
                        sr=requests.get(surl, timeout=7, headers={"User-Agent":"Mozilla/5.0"})
                        sj=sr.json()
                        for ke in reversed(sj.get("keyEvents",[])):
                            if "Goal" in ke.get("text","") and ke.get("athletesInvolved"):
                                scorer=ke["athletesInvolved"][0].get("displayName")
                                break
                    except: pass
                if scorer:
                    msg=f"🟢 GOAL {minute}'!\n\n🔥 {home} {score_str} {away}\n⚽ {scorer} ({minute}')\n🏆 {league_name}\n\n{hashtags}"
                else:
                    msg=f"🟢 GOAL {minute}'!\n\n🔥 {home} {score_str} {away}\n⚽ GOAL! Minute {minute}'\n🏆 {league_name}\n\n{hashtags}"
                if fb_post(msg): posted.add(gk)

        # ===== RED CARD, PENALTY, VAR - NEW =====
        if event_id and league_key:
            events=get_espn_key_events(league_key, event_id)
            for ev in events:
                ev_key=f"{ev['type']}_{key}_{ev['minute']}_{ev['athlete']}_{today}"
                if ev_key in last_events: continue
                if ev_key in posted: continue
                msg=None
                if ev["type"]=="red":
                    msg=f"🔴 RED CARD {ev['minute']}!\n\n🔥 {home} {score_str} {away}\n👤 {ev['athlete']} sent off!\n🏆 {league_name}\n\n{hashtags}"
                elif ev["type"]=="penalty_goal":
                    msg=f"⚽ PENALTY GOAL {ev['minute']}!\n\n🔥 {home} {score_str} {away}\n👤 {ev['athlete']} scores from spot!\n🏆 {league_name}\n\n{hashtags}"
                elif ev["type"]=="penalty_miss":
                    msg=f"❌ PENALTY MISSED {ev['minute']}!\n\n🔥 {home} {score_str} {away}\n👤 {ev['athlete']} misses!\n🏆 {league_name}\n\n{hashtags}"
                elif ev["type"]=="var":
                    msg=f"📺 VAR CHECK {ev['minute']}!\n\n🔥 {home} {score_str} {away}\n{ev['text']}\n🏆 {league_name}\n\n{hashtags}"
                if msg:
                    if fb_post(msg):
                        posted.add(ev_key)
                        new_events[ev_key]=True

        # ===== HT =====
        if state=="ht" or (es and "Halftime" in es.get("detail","")):
            gk=f"ht_{key}_{score_str}_{today}"
            if gk not in posted:
                msg=f"⏸️ HALF TIME!\n\n🔥 {home} {score_str} {away}\n🏆 {league_name}\n\n{hashtags}"
                if fb_post(msg): posted.add(gk)

        # ===== FT =====
        if state=="post":
            gk=f"ft_{key}_{score_str}_{today}"
            if gk not in posted and prev and prev.get("state")!="post":
                msg=f"✅ FULL TIME!\n\n🔥 {home} {score_str} {away}\n🏆 {league_name}\n\nFT Results! What a game 👇\n\n{hashtags}"
                if fb_post(msg): posted.add(gk)

    save_posted(posted); save_scores(new_scores); save_events({**last_events, **new_events})
    print(f"V78 DONE - Livescore primary kickoff to FT, never skip on disagree, added RED/PENALTY/VAR")

if __name__=="__main__": main()
