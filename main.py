import os, requests, json, re
from datetime import datetime, timedelta, timezone
FB_TOKEN=os.getenv("FB_TOKEN");FB_PAGE_ID=os.getenv("FB_PAGE_ID") or "1293090263895541"
POSTED_FILE="posted.json";SCORES_FILE="last_scores.json";EVENTS_FILE="last_events.json"
EAT=timezone(timedelta(hours=3));now_eat=datetime.now(EAT);today=now_eat.strftime("%Y-%m-%d")
LEAGUES={"eng.1":"Premier League","esp.1":"LaLiga","ita.1":"Serie A","ger.1":"Bundesliga","fra.1":"Ligue 1","ned.1":"Eredivisie","por.1":"Primeira Liga","tur.1":"Turkish Super Lig","bel.1":"Belgian Pro League","sco.1":"Scottish Premiership","aut.1":"Austrian Bundesliga","sui.1":"Swiss Super League","den.1":"Danish Superliga","sau.1":"Saudi Pro League","uefa.champions":"Champions League","uefa.europa":"Europa League","uefa.europa.conf":"Conference League"}
LS_MAP={"Premier League":"Premier League","LaLiga":"LaLiga","Serie A":"Serie A","Bundesliga":"Bundesliga","Ligue 1":"Ligue 1","Eredivisie":"Eredivisie","Primeira Liga":"Primeira Liga","Super Lig":"Turkish Super Lig","First Division A":"Belgian Pro League","Premiership":"Scottish Premiership","Bundesliga Austria":"Austrian Bundesliga","Super League":"Swiss Super League","Superliga":"Danish Superliga","Saudi Pro League":"Saudi Pro League","Pro League":"Saudi Pro League","UEFA Champions League":"Champions League","UEFA Europa League":"Europa League","UEFA Conference League":"Conference League"}
TO_ESPN={v:k for k,v in LEAGUES.items()}
TAGS={"Premier League":"#EPL #England #PremierLeague #Arsenal #ManCity #Liverpool #Chelsea #ManUtd #FootballUK","LaLiga":"#LaLiga #Spain #RealMadrid #Barcelona","Serie A":"#SerieA #Italy #Juventus #Inter #ACMilan","Bundesliga":"#Bundesliga #Germany #Bayern #Dortmund","Ligue 1":"#Ligue1 #France #PSG #Paris","Eredivisie":"#Eredivisie #Netherlands #Ajax","Primeira Liga":"#PrimeiraLiga #Portugal #Benfica #Porto","Turkish Super Lig":"#SuperLig #Turkey #Galatasaray #Fenerbahce #Besiktas","Belgian Pro League":"#JupilerProLeague #Belgium","Scottish Premiership":"#SPFL #Scotland #Celtic #Rangers","Saudi Pro League":"#SaudiProLeague #SPL #SaudiArabia #Ronaldo #AlNassr #AlHilal #RoshnSaudiLeague","Champions League":"#UCL #ChampionsLeague #UCLLive","Europa League":"#UEL #EuropaLeague","Conference League":"#UECL #ConferenceLeague"}
FIX={"man utd":"manchester united","man city":"manchester city","spurs":"tottenham hotspur","athletic club":"athletic bilbao","inter":"inter milan","psg":"paris saint-germain","bayern":"bayern munich","dortmund":"borussia dortmund"}
def norm(n):
 s=re.sub(r'[^a-z0-9 ]','',str(n).lower().strip());s=re.sub(r'\s+',' ',s);return FIX.get(s,s)
def load(f,d):
 try:
  with open(f) as x:return json.load(x)
 except:return d
def save(f,d):
 with open(f,"w") as x:json.dump(d,x)
def fb(msg):
 try:
  r=requests.post(f"https://graph.facebook.com/v20.0/{FB_PAGE_ID}/feed",data={"message":msg,"access_token":FB_TOKEN},timeout=20);print(f"FB {r.status_code} {r.text[:300]}");return r.status_code==200
 except Exception as e:print(e);return False
def pmin(s):
 m=re.search(r"(\d+)\s*\+?\s*(\d+)?",str(s))
 if not m:return "0'"
 return f"{m.group(1)}+{m.group(2)}'" if m.group(2) else f"{m.group(1)}'"
def pint(s):
 m=re.search(r"(\d+)",str(s));return int(m.group(1)) if m else 0
def hashtags(l):return f"#LiveScores #UnfilteredScores #FootballLive {TAGS.get(l,'#Football')} #FYP #ForYou #Viral #Trending #ExplorePage #NonFollowers #FootballTikTok #SoccerFans #FollowForMore"
def pick(lst,k):return lst[sum(ord(c) for c in str(k))%len(lst)]
def goal_c(h,a,hg,ag,ph,pa,ms):
 mi=pint(ms);tot=hg+ag
 if (ph<pa and hg==ag) or (pa<ph and hg==ag):return pick(["😱 WHAT A COMEBACK! From losing to level! This game is MAD!","🔥 COMEBACK IS ON! They refused to give up!"],f"{h}{a}{hg}{ag}")
 if (ph<pa and hg>ag) or (pa<ph and ag>hg):return pick(["🤯 FULL COMEBACK! From losing to WINNING! Unbelievable!","😱 THEY TURNED IT AROUND! From behind to in front!"],f"{h}{a}{hg}{ag}")
 if mi>=88:return pick(["🚨 LATE DRAMA! 90th minute GOAL! Heartbreak or Hero?!","🔥 LAST MINUTE GOAL! The stadium has ERUPTED!"],f"{h}{a}{hg}{ag}")
 if mi<=10:return "⚡ FAST START! Goal in first 10 mins! Buckle up!"
 if tot>=5:return "🎢 GOAL FEST! This game has EVERYTHING!"
 if hg==ag:return "⚖️ Level again! Who wants it more? 👇"
 if abs(hg-ag)>=3:return "😳 This is a ROUT! Total domination!"
 return pick(["🟢 GOAL! The net bulges again!","⚽ GOAL! Another one!","🔥 GOAL! This game keeps delivering!"],f"{h}{a}{hg}{ag}")
def ht_c(h,a,hg,ag):
 if hg==ag==0:return "😤 0-0 at HT. Who breaks the deadlock? Comment 1 for HOME, 2 for AWAY 👇"
 if hg==ag:return "⚖️ Level at HT! Second half is a FINAL. Who wins? 👇"
 if abs(hg-ag)==1:return "😬 One goal in it at HT! Comeback or hold on? 👇"
 return "😳 Big lead at HT! Is it game over or comeback coming? 👇"
def ft_c(h,a,hg,ag,ph,pa):
 tot=hg+ag
 if hg==ag and tot>=4:return "🤯 What a game! Goals, drama, everything! Tag a friend who missed this! 👇"
 if hg==ag and tot==0:return "😴 0-0 FT. Boring or tactical masterclass? 👇 YES or NO"
 if hg==ag:return "⚖️ FT: All square! Fair result or did someone bottle it? 👇"
 w=h if hg>ag else a
 if (ph is not None and ph<pa and hg>ag) or (ph is not None and pa<ph and ag>hg):return f"😱 WHAT A COMEBACK! {w} were LOSING and WON IT! Tag someone who gave up early! 👇"
 if abs(hg-ag)>=3:return f"😳 {w} DESTROYED them! {hg}-{ag}! Statement win! 👇"
 if tot>=5:return f"🎢 {hg}-{ag} FT! 7-goal thriller! Best game of the day? 👇"
 return f"✅ FT: {w} takes it {hg}-{ag}! Did your bet win? 👇 Follow for tomorrow's slips 💚"
# === FIXED: LIVESCORE FIRST + ESPN FALLBACK ===
def ls_games():
 out=[];seen=set()
 try:
  r=requests.get("https://prod-public-api.livescore.com/v1/api/app/date/soccer/all/today?MD=1&countryCode=KE",timeout=8,headers={"User-Agent":"Mozilla/5.0"})
  print(f"LS STATUS {r.status_code} LEN {len(r.text)}")
  for st in r.json().get("Stages",[]):
   raw=" ".join([str(st.get(k,"") or "") for k in ["Sdn","Cnm","Snm","Ctn","Sdm"]])
   ln=None
   for k,v in LS_MAP.items():
    if k.lower() in raw.lower():ln=v;break
   if not ln:
    rl=raw.lower()
    if "champion" in rl:ln="Champions League"
    elif "europa" in rl:ln="Europa League"
    elif "conference" in rl:ln="Conference League"
    elif "premier" in rl:ln="Premier League"
    elif "laliga" in rl or "la liga" in rl:ln="LaLiga"
    elif "serie" in rl:ln="Serie A"
    elif "bundesliga" in rl:ln="Bundesliga"
    elif "ligue" in rl:ln="Ligue 1"
    elif "eredivisie" in rl:ln="Eredivisie"
    elif "primeira" in rl:ln="Primeira Liga"
    elif "super lig" in rl:ln="Turkish Super Lig"
    elif "saudi" in rl or "pro league" in rl:ln="Saudi Pro League"
    else:ln=raw.strip() or "Football"
   for ev in st.get("Events",[]):
    t1=ev.get("T1",[{}])[0].get("Nm","") if ev.get("T1") else "";t2=ev.get("T2",[{}])[0].get("Nm","") if ev.get("T2") else ""
    if not t1 or not t2:continue
    nk=f"{norm(t1)}_vs_{norm(t2)}"
    if nk in seen:continue
    seen.add(nk)
    es=str(ev.get("Es",""));stt="pre" if es=="1" else "in" if es in ["2","4","5","8","9"] else "ht" if es=="3" else "post" if es in ["6","7","10"] else "pre"
    eps=str(ev.get("Eps","") or "");ms="HT" if stt=="ht" else "FT" if stt=="post" else pmin(eps) if any(c.isdigit() for c in eps) else "0'"
    ko=None
    try:
     raw2=str(ev.get("Esd","") or "")
     if len(raw2)>=14 and raw2.isdigit():ko=datetime.strptime(raw2[:14],"%Y%m%d%H%M%S").replace(tzinfo=timezone.utc).astimezone(EAT)
    except:pass
    out.append({"lk":TO_ESPN.get(ln,""),"ln":ln,"h":t1,"a":t2,"hg":int(ev.get("Tr1",0)) if str(ev.get("Tr1","")).isdigit() else 0,"ag":int(ev.get("Tr2",0)) if str(ev.get("Tr2","")).isdigit() else 0,"st":stt,"ms":ms,"ko":ko,"d":today.replace('-',''),"nk":nk})
 except Exception as e:print(f"LS FAIL: {e}")
 print(f"LIVESCORE GAMES: {len(out)}")
 if not out:
  print("LIVESCORE 0 -> ESPN FALLBACK")
  for lk,ln in LEAGUES.items():
   try:
    r=requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lk}/scoreboard?dates={today.replace('-','')}",timeout=8,headers={"User-Agent":"Mozilla/5.0"})
    print(f"ESPN {lk} {len(r.json().get('events',[]))} games")
    for ev in r.json().get("events",[]):
     c=ev.get("competitions",[{}])[0].get("competitors",[])
     if len(c)<2:continue
     h=c[0]["team"]["displayName"] if c[0].get("homeAway")=="home" else c[1]["team"]["displayName"];a=c[1]["team"]["displayName"] if c[0].get("homeAway")=="home" else c[0]["team"]["displayName"]
     hg=int(c[0].get("score",0)) if c[0].get("homeAway")=="home" else int(c[1].get("score",0));ag=int(c[1].get("score",0)) if c[0].get("homeAway")=="home" else int(c[0].get("score",0))
     stt=ev.get("status",{}).get("type",{}).get("state","pre");ms=pmin(ev.get("status",{}).get("displayClock",""))
     if stt=="post":ms="FT"
     out.append({"lk":lk,"ln":ln,"h":h,"a":a,"hg":hg,"ag":ag,"st":stt,"ms":ms,"ko":None,"d":today.replace('-',''),"nk":f"{norm(h)}_vs_{norm(a)}"})
   except Exception as e:print(f"ESPN FAIL {lk}: {e}")
 print(f"FINAL GAMES: {len(out)}");return out
_CACHE={}
def espn_id(lk,nk,d):
 if not lk:return None
 if f"{lk}_{d}" not in _CACHE:
  try:
   r=requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lk}/scoreboard?dates={d}",timeout=6,headers={"User-Agent":"Mozilla/5.0"});m={}
   for ev in r.json().get("events",[]):
    c=ev.get("competitions",[{}])[0].get("competitors",[])
    if len(c)<2:continue
    h=c[0]["team"]["displayName"] if c[0].get("homeAway")=="home" else c[1]["team"]["displayName"];a=c[1]["team"]["displayName"] if c[0].get("homeAway")=="home" else c[0]["team"]["displayName"];m[f"{norm(h)}_vs_{norm(a)}"]=str(ev.get("id"))
   _CACHE[f"{lk}_{d}"]=m
  except:_CACHE[f"{lk}_{d}"]={}
 return _CACHE[f"{lk}_{d}"].get(nk)
def espn_sum(lk,eid):
 try:
  r=requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lk}/summary?event={eid}",timeout=6,headers={"User-Agent":"Mozilla/5.0"});return r.json()
 except:return {}
def scorer(lk,eid):
 if not eid:return None
 for ke in reversed(espn_sum(lk,eid).get("keyEvents",[])):
  if "Goal" in ke.get("text","") and ke.get("athletesInvolved"):return ke["athletesInvolved"][0].get("displayName")
 return None
def key_events(lk,eid):
 out=[]
 for ke in espn_sum(lk,eid).get("keyEvents",[]):
  t=ke.get("text","");ath=ke["athletesInvolved"][0].get("displayName","") if ke.get("athletesInvolved") else "";mi=ke.get("clock",{}).get("displayValue","")
  typ="red" if "Red Card" in t else "penalty_miss" if "Penalty" in t and "Goal" not in t else "penalty_goal" if "Penalty" in t else "var" if "VAR" in t else "goal" if "Goal" in t else None
  if typ and typ!="goal":out.append({"type":typ,"text":t,"minute":mi,"athlete":ath})
 return out
def lineups(lk,eid):
 txt=[]
 for tm in espn_sum(lk,eid).get("lineups",[])[:2]:
  st=[p.get("athlete",{}).get("displayName","") for p in tm.get("roster",[]) if p.get("starter") is not False and p.get("position")!="Bench" and p.get("athlete",{}).get("displayName")]
  if len(st)>=7:txt.append(f"🔵 {tm.get('team',{}).get('displayName','Team')}: {', '.join(st[:7])}...")
 return "\n".join(txt) if txt else None
def main():
 posted=set(load(POSTED_FILE,[]));last=load(SCORES_FILE,{});lev=load(EVENTS_FILE,{});print(f"=== V85 FIXED ALL {now_eat} ===")
 new={};nev={}
 for g in ls_games():
  h,a,hg,ag,st,ln,lk,ms,ko,d,nk=g["h"],g["a"],g["hg"],g["ag"],g["st"],g["ln"],g["lk"],g["ms"],g["ko"],g["d"],g["nk"]
  key=f"ls_{nk}_{d}";ss=f"{hg}-{ag}";new[key]={"score":ss,"hg":hg,"ag":ag,"state":st};ht=hashtags(ln);prev=last.get(key);ph=prev.get("hg",0) if prev else 0;pa=prev.get("ag",0) if prev else 0;ps=prev.get("state") if prev else None;fol="\n\nFollow @Unfiltered Scores 🔔 Turn ON notifications - You will miss BOOM if you don't!"
  if lk in ["eng.1","uefa.champions"] and st=="pre" and ko:
   mk=(ko-now_eat).total_seconds()/60
   if 0<=mk<=90 and f"lineup_{key}" not in posted:
    eid=espn_id(lk,nk,d);lp=lineups(lk,eid) if eid else None
    if lp and fb(f"📋 LINEUPS OUT! - {int(mk)} MINS TO KICK OFF!\n\n🔥 {h} vs {a}\n🏆 {ln}\n⏰ {ko.strftime('%H:%M')} EAT\n\n{lp}\n\nWho wins? Comment 1 for {h}, 2 for {a} 👇\n\n{ht}{fol}"):posted.add(f"lineup_{key}")
  if st=="in" and ps=="pre" and f"kickoff_{key}" not in posted:
   if fb(f"⏰ KICK OFF!\n\n🔥 {h} vs {a}\n🏆 {ln}\n\n{pick(['KICK OFF! We are LIVE! Who scores first? 👇','⏰ KICK OFF! Buckle up, this one will be spicy!','KICK OFF! Drop your score prediction 👇'],key)}\n\n{ht}{fol}"):posted.add(f"kickoff_{key}")
  if prev and (hg>ph or ag>pa) and f"goal_{key}_{ss}" not in posted:
   eid=espn_id(lk,nk,d);sc=scorer(lk,eid) if eid else None;sm=goal_c(h,a,hg,ag,ph,pa,ms)
   txt=f"🟢 GOAL {ms}!\n\n🔥 {h} {ss} {a}\n⚽ {sc} ({ms})\n🏆 {ln}\n\n{sm}\n\n{pick(['Who scores next? 👇','Was it a foul? YES or NO 👇','Tag a friend who needs to see this goal! 👇'],key)}\n\n{ht}{fol}" if sc else f"🟢 GOAL {ms}!\n\n🔥 {h} {ss} {a}\n🏆 {ln}\n\n{sm}\n\n{pick(['Who scores next? 👇','Was it a foul? YES or NO 👇','Tag a friend who needs to see this goal! 👇'],key)}\n\n{ht}{fol}"
   if fb(txt):posted.add(f"goal_{key}_{ss}")
  if st in ["in","ht"]:
   eid=espn_id(lk,nk,d)
   if eid:
    for ev in key_events(lk,eid):
     ek=f"{ev['type']}_{key}_{ev['minute']}_{ev['athlete']}"
     if ek in lev or ek in posted:continue
     m=None
     if ev["type"]=="red":m=f"🔴 RED CARD {ev['minute']}!\n\n🔥 {h} {ss} {a}\n👤 {ev['athlete']} sent off!\n🏆 {ln}\n\nGame changed? Can they hold on with 10 men? 👇\n\n{ht}{fol}"
     elif ev["type"]=="penalty_goal":m=f"⚽ PENALTY GOAL {ev['minute']}!\n\n🔥 {h} {ss} {a}\n👤 {ev['athlete']} scores from spot!\n🏆 {ln}\n\nCold from 12 yards! 🥶 👇\n\n{ht}{fol}"
     elif ev["type"]=="penalty_miss":m=f"❌ PENALTY MISSED {ev['minute']}!\n\n🔥 {h} {ss} {a}\n👤 {ev['athlete']} misses!\n🏆 {ln}\n\nHUGE MISS! Will it cost them? 👇\n\n{ht}{fol}"
     elif ev["type"]=="var":m=f"📺 VAR CHECK {ev['minute']}!\n\n🔥 {h} {ss} {a}\n{ev['text']}\n🏆 {ln}\n\nVAR... Love it or hate it? 👇\n\n{ht}{fol}"
     if m and fb(m):posted.add(ek);nev[ek]=True
  # FIXED: HT also fires if first seen at HT
  if st=="ht" and ps in ["in",None] and f"ht_{key}_{ss}" not in posted:
   if fb(f"⏸️ HALF TIME!\n\n🔥 {h} {ss} {a}\n🏆 {ln}\n\n{ht_c(h,a,hg,ag)}\n\n{ht}{fol}"):posted.add(f"ht_{key}_{ss}")
  # FIXED: FT also fires if first seen at FT
  if st=="post" and ps in ["in","ht","pre",None] and f"ft_{key}_{ss}" not in posted:
   if fb(f"✅ FULL TIME!\n\n🔥 {h} {ss} {a}\n🏆 {ln}\n\n{ft_c(h,a,hg,ag,ph if prev else None,pa if prev else None)}\n\n{ht}{fol}"):posted.add(f"ft_{key}_{ss}")
 save(POSTED_FILE,list(posted)[-5000:]);save(SCORES_FILE,new);save(EVENTS_FILE,{**lev,**nev});print(f"V85 DONE - {len(posted)} posted")
if __name__=="__main__":main()
