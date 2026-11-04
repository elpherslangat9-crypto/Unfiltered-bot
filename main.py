import os, requests, json, re, random
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
NAME_FIX={"man utd":"manchester united","man city":"manchester city","spurs":"tottenham hotspur","athletic club":"athletic bilbao","inter":"inter milan","psg":"paris saint-germain","bayern":"bayern munich","dortmund":"borussia dortmund"}
def norm(n):
    s=re.sub(r'[^a-z0-9 ]','',str(n).lower().strip());s=re.sub(r'\s+',' ',s);return NAME_FIX.get(s,s)
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
    # Only keep TODAY events - no yesterday spam
    clean={k:v for k,v in e.items() if today in k}
    with open(EVENTS_FILE,"w") as f: json.dump(clean, f)
def fb_post(msg):
    for attempt in range(2):
        try:
            payload={"message":msg,"access_token":FB_TOKEN}
            r=requests.post(f"https://graph.facebook.com/v20.0/{FB_PAGE_ID}/feed", data=payload, timeout=20)
            print(f"FB POST {r.status_code}: {r.text[:600]}")
            if r.status_code==200: return True
        except Exception as e:
            print(f"FB FAIL attempt {attempt}: {e}")
    return False
def parse_min(s):
    try:
        s=str(s).strip()
        if not s: return "0'"
        if "HT" in s.upper() or "Half" in s: return "HT"
        m=re.search(r"(\d+)\s*\+?\s*(\d+)?", s)
        if not m: return "0'"
        if m.group(2): return f"{m.group(1)}+{m.group(2)}'"
        return f"{m.group(1)}'"
    except: return "0'"
def parse_min_int(s):
    try:
        m=re.search(r"(\d+)",str(s));return int(m.group(1)) if m else 0
    except: return 0
def get_hashtags(league_name):
    base="#LiveScores #UnfilteredScores #FootballLive"
    extra=COUNTRY_HASHTAGS.get(league_name, "#Football")
    return f"{base} {extra} #FYP #ForYou #Viral #Trending #ExplorePage #NonFollowers #FootballTikTok #SoccerFans #FollowForMore"
def pick(lst, key):
    h=sum(ord(c) for c in str(key))%len(lst);return lst[h]
def goal_comment(home,away,hg,ag,prev_hg,prev_ag,minute_str):
    mi=parse_min_int(minute_str)
    total=hg+ag
    was_losing_home=prev_hg<prev_ag; was_losing_away=prev_ag<prev_hg
    now_level=hg==ag; now_home_win=hg>ag; now_away_win=ag>hg
    if (was_losing_home and now_level) or (was_losing_away and now_level):
        return pick(["😱 WHAT A COMEBACK! From losing to level! This game is MAD!","🔥 COMEBACK IS ON! They refused to give up!","WHAT A GAME! Comeback complete - level again!"], f"{home}{away}{hg}{ag}")
    if (was_losing_home and now_home_win) or (was_losing_away and now_away_win):
        return pick(["🤯 FULL COMEBACK! From losing to WINNING! Unbelievable!","😱 THEY TURNED IT AROUND! From behind to in front!","WHAT A COMEBACK! This is why we love football!"], f"{home}{away}{hg}{ag}")
    if mi>=88:
        return pick(["🚨 LATE DRAMA! 90th minute GOAL! Heartbreak or Hero?!","⏰ 90' WINNER?! This league never sleeps!","🔥 LAST MINUTE GOAL! The stadium has ERUPTED!"], f"{home}{away}{hg}{ag}")
    if mi<=10:
        return pick(["⚡ FAST START! Goal in first 10 mins! Buckle up!","🚀 EARLY GOAL! We are in for a banger!"], f"{home}{away}{hg}{ag}")
    if total>=5:
        return pick(["🎢 GOAL FEST! This game has EVERYTHING!","🔥 GOALS GALORE! Defenders, go home!"], f"{home}{away}{hg}{ag}")
    if hg==ag:
        return pick(["⚖️ Level again! Who wants it more? 👇","Game on again! Level! Who scores next?"], f"{home}{away}{hg}{ag}")
    if abs(hg-ag)>=3:
        return pick(["😳 This is a ROUT! Total domination!","🔥 They are running riot! No mercy!"], f"{home}{away}{hg}{ag}")
    return pick(["🟢 GOAL! The net bulges again!","⚽ GOAL! Another one!","🔥 GOAL! This game keeps delivering!"], f"{home}{away}{hg}{ag}")
def ht_comment(home,away,hg,ag):
    if hg==0 and ag==0: return pick(["😤 0-0 at HT. Tight, tense... who breaks the deadlock? Comment 1 for HOME, 2 for AWAY 👇","⏸️ Goalless at HT. Second half will EXPLODE. Who wins? 👇"], f"{home}{away}ht")
    if hg==ag: return pick(["⚖️ Level at HT! Second half is a FINAL. Who wins? 👇","🔥 All square at HT! This is going down to the wire!"], f"{home}{away}ht")
    if abs(hg-ag)==1: return pick(["😬 One goal in it at HT! Comeback or hold on? 👇","⏸️ HT: One goal separates them. Second half = DRAMA!"], f"{home}{away}ht")
    return pick(["😳 Big lead at HT! Is it game over or is a comeback coming? 👇","🔥 HT: Dominant! Can they hold it?"], f"{home}{away}ht")
def ft_comment(home,away,hg,ag,prev_hg,prev_ag):
    total=hg+ag
    was_losing_home=prev_hg is not None and prev_hg<prev_ag
    was_losing_away=prev_hg is not None and prev_ag<prev_hg
    if hg==ag and total>=4: return "🤯 What a game! Goals, drama, everything! Tag a friend who missed this! 👇"
    if hg==ag and total==0: return "😴 0-0 FT. Defenders win today. Was it boring or tactical masterclass? 👇 YES or NO"
    if hg==ag: return "⚖️ FT: All square! Fair result or did someone bottle it? 👇"
    winner=home if hg>ag else away
    if (was_losing_home and hg>ag) or (was_losing_away and ag>hg): return f"😱 WHAT A COMEBACK! {winner} were LOSING and WON IT! This is FOOTBALL! Tag someone who gave up early! 👇"
    if abs(hg-ag)>=3: return f"😳 {winner} DESTROYED them! {hg}-{ag}! Statement win! 👇"
    if total>=5: return f"🎢 {hg}-{ag} FT! 7-goal thriller! Best game of the day? 👇"
    return f"✅ FT: {winner} takes it {hg}-{ag}! Did your bet win? 👇 Follow for tomorrow's slips 💚"
# === V91 ESPN ONLY - TODAY ONLY - ALL LEAGUES ===
def espn_get(url):
    for attempt in range(2):
        try:
            r=requests.get(url, timeout=10, headers={"User-Agent":"Mozilla/5.0"})
            if r.status_code==200: return r.json()
        except: pass
    return {}
def get_espn_games():
    all_games=[];seen=set()
    # TODAY ONLY - No yesterday, no tomorrow, no spam
    date_str_param=today.replace('-','')
    for lg_key, lg_name in LEAGUES.items():
        url=f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lg_key}/scoreboard?dates={date_str_param}"
        data=espn_get(url)
        for ev in data.get("events",[]):
            eid=str(ev.get("id"))
            if eid in seen: continue
            seen.add(eid)
            status=ev.get("status",{}).get("type",{}).get("state");detail=ev.get("status",{}).get("type",{}).get("detail","");date_str=ev.get("date","")
            if "Halftime" in detail: status="ht"
            comps=ev.get("competitions",[{}])[0].get("competitors",[])
            if len(comps)<2: continue
            home=comps[0]["team"]["displayName"] if comps[0].get("homeAway")=="home" else comps[1]["team"]["displayName"]
            away=comps[1]["team"]["displayName"] if comps[0].get("homeAway")=="home" else comps[0]["team"]["displayName"]
            hg=int(comps[0].get("score",0)) if comps[0].get("homeAway")=="home" else int(comps[1].get("score",0))
            ag=int(comps[1].get("score",0)) if comps[0].get("homeAway")=="home" else int(comps[0].get("score",0))
            clock=ev.get("status",{}).get("displayClock","")
            try:kickoff_eat=datetime.fromisoformat(date_str.replace("Z","+00:00")).astimezone(EAT)
            except:kickoff_eat=None
            all_games.append({"league_key":lg_key,"league_name":lg_name,"id":eid,"home":home,"away":away,"hg":hg,"ag":ag,"state":status,"detail":detail,"clock":clock,"minute_str":parse_min(clock) if status!="ht" else "HT","kickoff_eat":kickoff_eat,"date_param":date_str_param,"norm_key":f"{norm(home)}_vs_{norm(away)}"})
    print(f"ESPN TODAY {today}: {len(all_games)} games")
    return all_games
def get_espn_summary(league_key, event_id):
    url=f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_key}/summary?event={event_id}"
    return espn_get(url)
def get_espn_key_events(league_key, event_id):
    sj=get_espn_summary(league_key, event_id);events=[]
    for ke in sj.get("keyEvents",[]):
        text=ke.get("text","");minute=ke.get("clock",{}).get("displayValue","");athlete=ke["athletesInvolved"][0].get("displayName","") if ke.get("athletesInvolved") else ""
        if "Red Card" in text: typ="red"
        elif "Penalty" in text and "Goal" not in text: typ="penalty_miss"
        elif "Penalty" in text and "Goal" in text: typ="penalty_goal"
        elif "VAR" in text: typ="var"
        elif "Goal" in text: typ="goal"
        else: continue
        events.append({"type":typ,"text":text,"minute":minute,"athlete":athlete})
    return events
def get_scorer(league_key, event_id):
    sj=get_espn_summary(league_key, event_id)
    for ke in reversed(sj.get("keyEvents",[])):
        if "Goal" in ke.get("text","") and ke.get("athletesInvolved"): return ke["athletesInvolved"][0].get("displayName")
    return None
def get_lineups(league_key, event_id):
    sj=get_espn_summary(league_key, event_id);lineups=sj.get("lineups",[])
    if not lineups: return None
    txt=[]
    for team in lineups[:2]:
        tname=team.get("team",{}).get("displayName","Team");starters=[]
        for p in team.get("roster",[]):
            if p.get("starter") is False: continue
            if p.get("position","")=="Bench": continue
            nm=p.get("athlete",{}).get("displayName","")
            if nm: starters.append(nm)
        starters=starters[:11]
        if len(starters)>=7: txt.append(f"🔵 {tname}: {', '.join(starters[:7])}...")
    return "\n".join(txt) if txt else None
def main():
    posted=load_posted(); last_scores=load_scores(); last_events=load_events()
    print(f"=== V91 ESPN ONLY TODAY ONLY {now_eat} ===")
    espn_games=get_espn_games()
    if len(espn_games)==0:
        print("ESPN 0 TODAY - ABORT, DO NOT WIPE SCORES")
        return
    new_scores={}; new_events={}
    for g in espn_games:
        eid=g["id"];key=f"espn_{eid}";home=g["home"];away=g["away"];hg=g["hg"];ag=g["ag"];state=g["state"];league_name=g["league_name"];league_key=g["league_key"];event_id=eid;kickoff_eat=g["kickoff_eat"];match_date=g["date_param"]
        minute_str=g["minute_str"];score_str=f"{hg}-{ag}";new_scores[key]={"score":score_str,"hg":hg,"ag":ag,"state":state};hashtags=get_hashtags(league_name);prev=last_scores.get(key);prev_hg=prev.get("hg",0) if prev else 0;prev_ag=prev.get("ag",0) if prev else 0;prev_state=prev.get("state") if prev else None
        follow="\n\nFollow @Unfiltered Scores 🔔 Turn ON notifications - You will miss BOOM if you don't!"
        # === 1. LINEUPS - ALL LEAGUES, 120 mins before ===
        if state=="pre" and kickoff_eat:
            minutes_to_kick=(kickoff_eat - now_eat).total_seconds()/60
            if 0 <= minutes_to_kick <= 120:
                gk_lineup=f"lineup_{key}_{match_date}"
                if gk_lineup not in posted:
                    lineup=get_lineups(league_key, event_id)
                    if lineup:
                        msg=f"📋 LINEUPS OUT! - {int(minutes_to_kick)} MINS TO KICK OFF!\n\n🔥 {home} vs {away}\n🏆 {league_name}\n⏰ {kickoff_eat.strftime('%H:%M')} EAT\n\n{lineup}\n\nWho wins? Comment 1 for {home}, 2 for {away} 👇\n\n{hashtags}{follow}"
                        if fb_post(msg): posted.add(gk_lineup)
                    else: print(f"Lineup not yet available {home} vs {away} - {int(minutes_to_kick)} mins to go, will retry")
        # === 2. KICKOFF - NEVER MISS ===
        kickoff_now=False
        if state=="in" and prev_state=="pre": kickoff_now=True
        if state=="in" and prev is None and parse_min_int(minute_str)<=15: kickoff_now=True
        if state=="ht" and prev is None: kickoff_now=True  # First seen at HT, we missed kickoff, post it now then HT
        if kickoff_now:
            gk=f"kickoff_{key}_{match_date}"
            if gk not in posted:
                ko_pick=pick(["KICK OFF! We are LIVE! Who scores first? 👇","⏰ KICK OFF! Buckle up, this one will be spicy!","KICK OFF! Drop your score prediction 👇"], key)
                msg=f"⏰ KICK OFF!\n\n🔥 {home} vs {away}\n🏆 {league_name}\n\n{ko_pick}\n\n{hashtags}{follow}"
                if fb_post(msg): posted.add(gk)
        # === 3. GOAL - Normal + Catch-up if first seen already scored ===
        goal_to_post=False;catchup=False
        if prev and (hg>prev.get("hg",0) or ag>prev.get("ag",0)):
            goal_to_post=True
        elif not prev and (hg+ag)>0 and state in ["in","ht","post"]:
            goal_to_post=True;catchup=True;prev_hg=0;prev_ag=0
        if goal_to_post:
            gk=f"goal_{key}_{score_str}_{match_date}"
            if gk not in posted:
                scorer=get_scorer(league_key, event_id)
                smart=goal_comment(home,away,hg,ag,prev_hg,prev_ag,minute_str)
                cta=pick(["Who scores next? 👇","Was it a foul? YES or NO 👇","Tag a friend who needs to see this goal! 👇"], gk)
                prefix="🟢 GOAL" if not catchup else "🟢 GOAL - CATCH UP!"
                if scorer: msg=f"{prefix} {minute_str}!\n\n🔥 {home} {score_str} {away}\n⚽ {scorer} ({minute_str})\n🏆 {league_name}\n\n{smart}\n\n{cta}\n\n{hashtags}{follow}"
                else: msg=f"{prefix} {minute_str}!\n\n🔥 {home} {score_str} {away}\n🏆 {league_name}\n\n{smart}\n\n{cta}\n\n{hashtags}{follow}"
                if fb_post(msg): posted.add(gk)
        # === 4. RED / PENALTY / VAR - Check in, ht AND post, so never miss ===
        if state in ["in","ht","post"] and event_id and league_key:
            events=get_espn_key_events(league_key, event_id)
            for ev in events:
                if ev["type"] in ["goal","yellow"]: continue
                ev_key=f"{ev['type']}_{key}_{ev['minute']}_{ev['athlete']}_{match_date}"
                if ev_key in last_events or ev_key in posted: continue
                msg=None
                if ev["type"]=="red": msg=f"🔴 RED CARD {ev['minute']}!\n\n🔥 {home} {score_str} {away}\n👤 {ev['athlete']} sent off!\n🏆 {league_name}\n\nGame changed? Can they hold on with 10 men? 👇\n\n{hashtags}{follow}"
                elif ev["type"]=="penalty_goal": msg=f"⚽ PENALTY GOAL {ev['minute']}!\n\n🔥 {home} {score_str} {away}\n👤 {ev['athlete']} scores from spot!\n🏆 {league_name}\n\nCold from 12 yards! 🥶 👇\n\n{hashtags}{follow}"
                elif ev["type"]=="penalty_miss": msg=f"❌ PENALTY MISSED {ev['minute']}!\n\n🔥 {home} {score_str} {away}\n👤 {ev['athlete']} misses!\n🏆 {league_name}\n\nHUGE MISS! Will it cost them? 👇\n\n{hashtags}{follow}"
                elif ev["type"]=="var": msg=f"📺 VAR CHECK {ev['minute']}!\n\n🔥 {home} {score_str} {away}\n{ev['text']}\n🏆 {league_name}\n\nVAR... Love it or hate it? 👇\n\n{hashtags}{follow}"
                if msg:
                    if fb_post(msg): posted.add(ev_key);new_events[ev_key]=True
        # === 5. HT ===
        if state=="ht":
            gk=f"ht_{key}_{score_str}_{match_date}"
            if gk not in posted:
                smart=ht_comment(home,away,hg,ag)
                msg=f"⏸️ HALF TIME!\n\n🔥 {home} {score_str} {away}\n🏆 {league_name}\n\n{smart}\n\n{hashtags}{follow}"
                if fb_post(msg): posted.add(gk)
        # === 6. FT - Today only, even if first seen at FT ===
        if state=="post":
            gk=f"ft_{key}_{score_str}_{match_date}"
            if gk not in posted:
                smart=ft_comment(home,away,hg,ag,prev_hg if prev else None,prev_ag if prev else None)
                msg=f"✅ FULL TIME!\n\n🔥 {home} {score_str} {away}\n🏆 {league_name}\n\n{smart}\n\n{hashtags}{follow}"
                if fb_post(msg): posted.add(gk)
    save_posted(posted); save_scores(new_scores); save_events({**last_events, **new_events})
    print(f"V91 DONE - {len(posted)} posted, TODAY ONLY, ESPN ONLY, ALL LEAGUES")
if __name__=="__main__": main()
