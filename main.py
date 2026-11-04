import os, requests, json, re
from datetime import datetime, timedelta, timezone

FB_TOKEN = os.getenv("FB_TOKEN")
FB_PAGE_ID = os.getenv("FB_PAGE_ID") or "1293090263895541"
POSTED_FILE="posted.json"; SCORES_FILE="last_scores.json"; EVENTS_FILE="last_events.json"
EAT=timezone(timedelta(hours=3)); now_eat=datetime.now(EAT); today=now_eat.strftime("%Y-%m-%d")

LEAGUES={"eng.1":"Premier League","esp.1":"LaLiga","ita.1":"Serie A","ger.1":"Bundesliga","fra.1":"Ligue 1","ned.1":"Eredivisie","por.1":"Primeira Liga","tur.1":"Turkish Super Lig","bel.1":"Belgian Pro League","sco.1":"Scottish Premiership","aut.1":"Austrian Bundesliga","sui.1":"Swiss Super League","den.1":"Danish Superliga","sau.1":"Saudi Pro League","uefa.champions":"Champions League","uefa.europa":"Europa League","uefa.europa.conf":"Conference League"}
COUNTRY_HASHTAGS={"Premier League":"#EPL #England #PremierLeague #Arsenal #ManCity #Liverpool #Chelsea #ManUtd #FootballUK","LaLiga":"#LaLiga #Spain #RealMadrid #Barcelona","Serie A":"#SerieA #Italy #Juventus #Inter #ACMilan","Bundesliga":"#Bundesliga #Germany #Bayern #Dortmund","Ligue 1":"#Ligue1 #France #PSG #Paris","Eredivisie":"#Eredivisie #Netherlands #Ajax","Primeira Liga":"#PrimeiraLiga #Portugal #Benfica #Porto","Turkish Super Lig":"#SuperLig #Turkey #Galatasaray #Fenerbahce #Besiktas","Belgian Pro League":"#JupilerProLeague #Belgium","Scottish Premiership":"#SPFL #Scotland #Celtic #Rangers","Saudi Pro League":"#SaudiProLeague #SPL #SaudiArabia #Ronaldo #AlNassr #AlHilal #RoshnSaudiLeague","Champions League":"#UCL #ChampionsLeague #UCLLive","Europa League":"#UEL #EuropaLeague","Conference League":"#UECL #ConferenceLeague"}
NAME_FIX={"man utd":"manchester united","man city":"manchester city","spurs":"tottenham hotspur","athletic club":"athletic bilbao","inter":"inter milan","psg":"paris saint-germain","bayern":"bayern munich","dortmund":"borussia dortmund"}

def norm(n):
 s=re.sub(r'[^a-z0-9 ]','',str(n).lower().strip());s=re.sub(r'\s+',' ',s);return NAME_FIX.get(s,s)
def load(f,d):
 try:
  with open(f) as x:return json.load(x)
 except:return d
def save(f,d):
 with open(f,"w") as x:json.dump(d,x)
def fb_post(msg):
 for a in range(2):
  try:
   r=requests.post(f"https://graph.facebook.com/v20.0/{FB_PAGE_ID}/feed",data={"message":msg,"access_token":FB_TOKEN},timeout=20)
   print(f"FB {r.status_code}")
   if r.status_code==200:return True
  except:pass
 return False
def parse_min(s):
 s=str(s or "").strip()
 if "Half" in s or "HT" in s.upper():return "HT"
 m=re.search(r"(\d+)\s*\+?\s*(\d+)?",s)
 if not m:return "0'"
 return f"{m.group(1)}+{m.group(2)}'" if m.group(2) else f"{m.group(1)}'"
def parse_min_int(s):
 m=re.search(r"(\d+)",str(s));return int(m.group(1)) if m else 0
def hashtags(l):return f"#LiveScores #UnfilteredScores #FootballLive {COUNTRY_HASHTAGS.get(l,'#Football')} #FYP #ForYou #Viral #Trending #ExplorePage #NonFollowers #FootballTikTok #SoccerFans #FollowForMore"
def pick(lst,k):return lst[sum(ord(c) for c in str(k))%len(lst)]
def goal_c(h,a,hg,ag,ph,pa,ms):
 mi=parse_min_int(ms);tot=hg+ag
 if (ph<pa and hg==ag) or (pa<ph and hg==ag):return "😱 WHAT A COMEBACK! From losing to level!"
 if (ph<pa and hg>ag) or (pa<ph and ag>hg):return "🤯 FULL COMEBACK! From losing to WINNING!"
 if mi>=88:return "🚨 LATE DRAMA! 90th minute GOAL!"
 if mi<=10:return "⚡ FAST START! Goal in first 10 mins!"
 if tot>=5:return "🎢 GOAL FEST!"
 if hg==ag:return "⚖️ Level again! Who wants it more? 👇"
 if abs(hg-ag)>=3:return "😳 ROUT! Total domination!"
 return "🟢 GOAL! The net bulges again!"
def ht_c(h,a,hg,ag):
 if hg==ag==0:return "😤 0-0 at HT. Who breaks deadlock? 1 for HOME, 2 for AWAY 👇"
 if hg==ag:return "⚖️ Level at HT! Second half is a FINAL. Who wins? 👇"
 if abs(hg-ag)==1:return "😬 One goal in it at HT! Comeback or hold on? 👇"
 return "😳 Big lead at HT! Game over or comeback? 👇"
def ft_c(h,a,hg,ag,ph,pa):
 tot=hg+ag
 if hg==ag and tot>=4:return "🤯 What a game! Tag a friend who missed this! 👇"
 if hg==ag and tot==0:return "😴 0-0 FT. Boring or tactical masterclass? YES or NO 👇"
 if hg==ag:return "⚖️ FT: All square! Fair result? 👇"
 w=h if hg>ag else a
 if (ph is not None and ph<pa and hg>ag) or (ph is not None and pa<ph and ag>hg):return f"😱 WHAT A COMEBACK! {w} were LOSING and WON IT! 👇"
 if abs(hg-ag)>=3:return f"😳 {w} DESTROYED them! {hg}-{ag}! 👇"
 if tot>=5:return f"🎢 {hg}-{ag} FT! Best game of the day? 👇"
 return f"✅ FT: {w} takes it {hg}-{ag}! Did your bet win? 👇"

# === V92 - NO LINEUPS - ESPN ONLY - TODAY ONLY - NEVER MISSES ===
_SUMMARY_CACHE={}
def espn_get(url):
 try:
  r=requests.get(url,timeout=10,headers={"User-Agent":"Mozilla/5.0"})
  if r.status_code==200:return r.json()
 except:pass
 return {}
def get_summary(lk,eid):
 if eid in _SUMMARY_CACHE:return _SUMMARY_CACHE[eid]
 d=espn_get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lk}/summary?event={eid}")
 _SUMMARY_CACHE[eid]=d
 return d
def get_games():
 out=[];seen=set();date_param=today.replace('-','')
 for lk,ln in LEAGUES.items():
  data=espn_get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lk}/scoreboard?dates={date_param}")
  for ev in data.get("events",[]):
   eid=str(ev.get("id"))
   if eid in seen:continue
   seen.add(eid)
   st=ev.get("status",{}).get("type",{}).get("state");detail=ev.get("status",{}).get("type",{}).get("detail","")
   if "Halftime" in detail:st="ht"
   c=ev.get("competitions",[{}])[0].get("competitors",[])
   if len(c)<2:continue
   h=c[0]["team"]["displayName"] if c[0].get("homeAway")=="home" else c[1]["team"]["displayName"]
   a=c[1]["team"]["displayName"] if c[0].get("homeAway")=="home" else c[0]["team"]["displayName"]
   hg=int(c[0].get("score",0)) if c[0].get("homeAway")=="home" else int(c[1].get("score",0))
   ag=int(c[1].get("score",0)) if c[0].get("homeAway")=="home" else int(c[0].get("score",0))
   try:ko=datetime.fromisoformat(ev.get("date","").replace("Z","+00:00")).astimezone(EAT)
   except:ko=None
   out.append({"lk":lk,"ln":ln,"eid":eid,"h":h,"a":a,"hg":hg,"ag":ag,"st":st,"detail":detail,"ms":parse_min(ev.get("status",{}).get("displayClock","")) if st!="ht" else "HT","ko":ko,"d":date_param,"nk":f"{norm(h)}_vs_{norm(a)}"})
 print(f"ESPN TODAY {today}: {len(out)} games");return out
def parse_summary(sj):
 scorer=None;events=[]
 for ke in sj.get("keyEvents",[]):
  txt=ke.get("text","");mi=ke.get("clock",{}).get("displayValue","");ath=ke["athletesInvolved"][0].get("displayName","") if ke.get("athletesInvolved") else ""
  if "Goal" in txt and ke.get("athletesInvolved"):scorer=ath
  typ="red" if "Red Card" in txt else "penalty_miss" if "Penalty" in txt and "Goal" not in txt else "penalty_goal" if "Penalty" in txt else "var" if "VAR" in txt else None
  if typ:events.append({"type":typ,"text":txt,"minute":mi,"athlete":ath})
 return scorer,events

def main():
 posted=set(load(POSTED_FILE,[]));last=load(SCORES_FILE,{});lev=load(EVENTS_FILE,{})
 print(f"=== V92 NO LINEUPS - NEVER MISSES {now_eat} ===")
 games=get_games()
 if not games:print("ESPN 0 - ABORT, DO NOT WIPE");return
 new={};nev={}
 for g in games:
  h,a,hg,ag,st,ln,lk,ms,ko,d,nk,eid=g["h"],g["a"],g["hg"],g["ag"],g["st"],g["ln"],g["lk"],g["ms"],g["ko"],g["d"],g["nk"],g["eid"]
  key=f"espn_{eid}";ss=f"{hg}-{ag}";new[key]={"score":ss,"hg":hg,"ag":ag,"state":st};ht=hashtags(ln);prev=last.get(key);ph=prev.get("hg",0) if prev else 0;pa=prev.get("ag",0) if prev else 0;ps=prev.get("state") if prev else None
  fol="\n\nFollow @Unfiltered Scores 🔔 Turn ON notifications - You will miss BOOM if you don't!"
  is_new=prev is None;score_changed=prev and (hg!=ph or ag!=pa);state_changed=prev and ps!=st
  # SMART: Only fetch summary if game is live and something changed, or first seen live - NO lineup calls at all
  need_summary=False
  if st in ["in","ht","post"] and (score_changed or state_changed or is_new):need_summary=True
  # If game finished and FT already posted, don't call summary again
  if st=="post" and f"ft_{key}_{ss}_{d}" in posted and not score_changed:need_summary=False
  scorer=None;events=[]
  if need_summary:
   sj=get_summary(lk,eid);scorer,events=parse_summary(sj)
  # 1. KICKOFF - NEVER MISS - Even if first seen at HT or FT, still post it
  ko_now=False
  if st=="in" and ps=="pre":ko_now=True
  if st in ["in","ht","post"] and is_new:ko_now=True
  if st in ["ht","post"] and ps=="pre":ko_now=True
  if ko_now and f"kickoff_{key}_{d}" not in posted:
   if fb_post(f"⏰ KICK OFF!\n\n🔥 {h} vs {a}\n🏆 {ln}\n\n{pick(['KICK OFF! Who scores first? 👇','⏰ KICK OFF! Buckle up!','KICK OFF! Drop prediction 👇'],key)}\n\n{ht}{fol}"):posted.add(f"kickoff_{key}_{d}")
  # 2. GOAL - NEVER MISS
  goal_now=(prev and (hg>ph or ag>pa)) or (is_new and (hg+ag)>0 and st in ["in","ht","post"])
  if goal_now and f"goal_{key}_{ss}_{d}" not in posted:
   sm=goal_c(h,a,hg,ag,ph if prev else 0,pa if prev else 0,ms)
   txt=f"🟢 GOAL {ms}!\n\n🔥 {h} {ss} {a}\n⚽ {scorer} ({ms})\n🏆 {ln}\n\n{sm}\n\n{pick(['Who scores next? 👇','Foul? YES or NO 👇','Tag a friend! 👇'],key)}\n\n{ht}{fol}" if scorer else f"🟢 GOAL {ms}!\n\n🔥 {h} {ss} {a}\n🏆 {ln}\n\n{sm}\n\n{pick(['Who scores next? 👇','Foul? YES or NO 👇','Tag a friend! 👇'],key)}\n\n{ht}{fol}"
   if fb_post(txt):posted.add(f"goal_{key}_{ss}_{d}")
  # 3. RED / PENALTY / VAR - From same summary, check even at FT so never miss
  if need_summary and st in ["in","ht","post"]:
   for ev in events:
    if ev["type"] in ["goal"]:continue
    ek=f"{ev['type']}_{key}_{ev['minute']}_{ev['athlete']}_{d}"
    if ek in lev or ek in posted:continue
    m=None
    if ev["type"]=="red":m=f"🔴 RED CARD {ev['minute']}!\n\n🔥 {h} {ss} {a}\n👤 {ev['athlete']} sent off!\n🏆 {ln}\n\nHold on with 10 men? 👇\n\n{ht}{fol}"
    elif ev["type"]=="penalty_goal":m=f"⚽ PENALTY GOAL {ev['minute']}!\n\n🔥 {h} {ss} {a}\n👤 {ev['athlete']} from spot!\n🏆 {ln}\n\nCold! 🥶 👇\n\n{ht}{fol}"
    elif ev["type"]=="penalty_miss":m=f"❌ PENALTY MISSED {ev['minute']}!\n\n🔥 {h} {ss} {a}\n👤 {ev['athlete']} misses!\n🏆 {ln}\n\nWill it cost them? 👇\n\n{ht}{fol}"
    elif ev["type"]=="var":m=f"📺 VAR CHECK {ev['minute']}!\n\n🔥 {h} {ss} {a}\n{ev['text']}\n🏆 {ln}\n\nLove it or hate it? 👇\n\n{ht}{fol}"
    if m and fb_post(m):posted.add(ek);nev[ek]=True
  # 4. HT - NEVER MISS
  if st=="ht" and f"ht_{key}_{ss}_{d}" not in posted:
   if fb_post(f"⏸️ HALF TIME!\n\n🔥 {h} {ss} {a}\n🏆 {ln}\n\n{ht_c(h,a,hg,ag)}\n\n{ht}{fol}"):posted.add(f"ht_{key}_{ss}_{d}")
  # 5. FT - NEVER MISS
  if st=="post" and f"ft_{key}_{ss}_{d}" not in posted:
   if fb_post(f"✅ FULL TIME!\n\n🔥 {h} {ss} {a}\n🏆 {ln}\n\n{ft_c(h,a,hg,ag,ph if prev else None,pa if prev else None)}\n\n{ht}{fol}"):posted.add(f"ft_{key}_{ss}_{d}")
 save(POSTED_FILE,list(posted)[-5000:]);save(SCORES_FILE,new);save(EVENTS_FILE,{k:v for k,v in {**lev,**nev}.items() if today in k});print(f"V92 DONE - {len(posted)} posted, NO LINEUPS, SUMMARY CALLS: {len(_SUMMARY_CACHE)}")
if __name__=="__main__":main()
