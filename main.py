import os,time,threading,requests,json,random,hashlib,re
from flask import Flask,jsonify,request
from datetime import datetime,timezone,timedelta
from collections import defaultdict
app=Flask(__name__);P=os.environ
PID=P.get("PAGE_ID");PT=P.get("PAGE_TOKEN");KEY=P.get("FOOTBALL_API_KEY")
TB=P.get("TELEGRAM_BOT_TOKEN");TC=P.get("TELEGRAM_CHANNEL_ID","@unfiltered_scores")
H={"x-apisports-key":KEY} if KEY else {};EAT=timezone(timedelta(hours=3))
C={};LC={};MS={};PD=set()
PF="/tmp/posted.json"
try:
 if os.path.exists(PF):PD=set(json.load(open(PF)))
except:PD=set()
def save(): 
 try:json.dump(list(PD),open(PF,"w"))
 except:pass
def hsh(s):return hashlib.md5(s.encode()).hexdigest()[:10]
def mkey(h,a,d):return f"{re.sub(r'\W+','',h.lower())[:8]}_{re.sub(r'\W+','',a.lower())[:8]}_{d[:10]}"
def season():n=datetime.now();return n.year if n.month>=7 else n.year-1
def is_congo(n):return "linafoot" in n.lower() or "congo" in n.lower() or "rdc" in n.lower()

# --- DYNAMIC HASHTAGS - ROTATES EVERY POST FOR NON-FOLLOWERS REACH ---
TAG_POOLS=[
 ["#LiveScores","#FootballLive","#KenyaFootball","#KPLLive"],
 ["#FootballNews","#SoccerUpdates","#EPLLive","#LaLiga"],
 ["#Linafoot","#RDCFoot","#AfricanFootball","#CAF"],
 ["#GoalAlert","#MatchDay","#FootballKenya","#UnfilteredScores"],
 ["#UCL","#EuropaLeague","#FootballFans","#LiveMatch"],
 ["#GorMahia","#AFCLepards","#TuskerFC","#KPL"],
]
def get_tags(league):
  base=random.choice(TAG_POOLS)
  if "kenya" in league.lower() or "kpl" in league.lower():
    base+=["#Kenya","#HarambeeStars"]
  if is_congo(league):
    base+=["#LinafootRDC","#VitaClub","#TPMazembe"]
  if "england" in league.lower() or "premier" in league.lower():
    base+=["#EPL","#PremierLeague"]
  random.shuffle(base)
  return " ".join(base[:4]) # Only 4 tags - FB hates many

def post(m, league=""):
 mh=hsh(m)
 if mh in PD:return
 # TELEGRAM
 try:
  if TB and TC:requests.post(f"https://api.telegram.org/bot{TB}/sendMessage",data={"chat_id":TC,"text":m},timeout=10)
 except:pass
 # FACEBOOK - DIRECT POST - NOW ALLOWED - NO RESTRICTION
 try:
  if PID and PT:
   # Keep it clean for visibility - NO LINK IN MAIN POST
   fb=re.sub(r'https?://\S+',"",m).strip()
   hook=random.choice(["What a moment! 👇","Who will win? Predict! 💬","Are you watching? ❤️","Tag a friend! 👇","Your prediction? 👇"])
   if is_congo(league):
     hook=random.choice(["Votre pronostic? 👇","Vous regardez? ❤️","Qui va gagner? 💬","Partagez! 👇"])
   final=f"🟢 {fb}\n\n{hook}\n\n{get_tags(league)}\n\n🟢 Unfiltered Scores"
   r=requests.post(f"https://graph.facebook.com/{PID}/feed",data={"message":final,"access_token":PT},timeout=15)
   if r.status_code==200:
     PD.add(mh);save()
     # Comment with website name (not link) for reach
     try:
       pid=r.json().get("id","")
       if pid:requests.post(f"https://graph.facebook.com/{pid}/comments",data={"message":"More live scores on unfiltered-scores.vercel.app - Follow us for every goal!","access_token":PT},timeout=10)
     except:pass
     print(f"FB POSTED: {league}")
   else:print(f"FB FAIL {r.text}")
 except Exception as e:print(f"FB err {e}")

def live_all(d):
 y=d.replace("-","")
 if y in LC and time.time()-LC[y][0]<45:return LC[y][1]
 try:
  r=requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard?dates={y}",timeout=8)
  if r.status_code==200:
   F=[]
   for ev in r.json().get("events",[]):
    try:
     cp=ev.get("competitions",[{}])[0];cs=cp.get("competitors",[]);ho=next((c for c in cs if c.get("homeAway")=="home"),{});aw=next((c for c in cs if c.get("homeAway")=="away"),{})
     lg=ev.get("league",{});st=cp.get("status",{}).get("type",{});sn=st.get("name","");clock=cp.get("status",{}).get("displayClock","")
     F.append({"fixture":{"id":f"e-{ev.get('id')}","date":cp.get("date",""),"status":{"short":"HT" if "HALFTIME" in sn else "1H" if sn in ["STATUS_IN_PROGRESS"] else "FT" if sn=="STATUS_FINAL" else "NS","el":clock},"venue":cp.get("venue",{}).get("fullName","")},"league":{"name":lg.get("name","Football"),"id":lg.get("id",""),"country":"World"},"teams":{"home":{"name":ho.get("team",{}).get("displayName","Home")},"away":{"name":aw.get("team",{}).get("displayName","Away")}},"goals":{"home":int(ho.get("score")) if str(ho.get("score")).isdigit() else None,"away":int(aw.get("score")) if str(aw.get("score")).isdigit() else None}})
    except:continue
   if F:LC[y]=(time.time(),F);return F
 except:pass
 return []

def api_all(d):
 if d in C and time.time()-C[d][0]<180 and C[d][1]:return C[d][1]
 try:
  if KEY:
   r=requests.get("https://v3.football.api-sports.io/fixtures",headers=H,params={"date":d,"season":season()},timeout=12)
   if r.status_code==429:return []
   if r.status_code==200:
    D=r.json().get("response",[])
    C[d]=(time.time(),D);return D
 except:pass
 return []

def combined(d):
 api=api_all(d);espn=live_all(d);all=[];seen=set()
 for f in api+espn:
  try:
   k=mkey(f['teams']['home']['name'],f['teams']['away']['name'],f['fixture']['date'])
   if k not in seen:all.append(f);seen.add(k)
  except:all.append(f)
 return all

# --- FLASK - FLASHSCORE STYLE - NO CRASH - NO EXTRA INFO ---
@app.route('/api/day')
def day():
 try:
  d=request.args.get('date') or datetime.now(EAT).strftime("%Y-%m-%d");s=request.args.get('search','').lower()
  F=combined(d)
  if s:F=[f for f in F if s in f['teams']['home']['name'].lower() or s in f['teams']['away']['name'].lower() or s in f['league']['name'].lower()]
  F.sort(key=lambda x:x['fixture']['date'])
  G=defaultdict(list)
  for f in F:
   # Detect Kenya
   ctry=f['league'].get('country','World')
   lname=f['league']['name']
   if "kenya" in lname.lower() or f['league'].get('id')==324:ctry="Kenya"
   if is_congo(lname):ctry="DR Congo"
   if "england" in ctry.lower():ctry="England"
   G[(ctry,lname)].append(f)
  B=defaultdict(list)
  for (c,l),gm in G.items():B[c].append({"league":l,"games":gm})
  # Flashscore order: Kenya first, then DR Congo, then England, rest
  order=lambda x:0 if "kenya" in x.lower() else 1 if "congo" in x.lower() else 2 if "england" in x.lower() else 3
  out=[{"country":c,"leagues":sorted(ls,key=lambda x:x['league'])} for c,ls in B.items()]
  out.sort(key=lambda x:order(x['country']))
  return jsonify({"date":d,"countries":out,"count":len(F)})
 except Exception as e:return jsonify({"error":str(e),"countries":[],"count":0})

@app.route('/')
def home():return jsonify({"status":"V18 LIVE","fb":"DIRECT POST ALLOWED","hashtags":"ROTATING FOR REACH"})

def bot():
 print("🟢 BOT V18 - DIRECT FB POST - ROTATING TAGS - FLASHSCORE")
 while True:
  try:
   now=datetime.now(EAT);today=now.strftime("%Y-%m-%d");F=combined(today)
   for f in F:
    fid=str(f['fixture']['id']);hg=f['goals']['home'];ag=f['goals']['away'];st=f['fixture']['status'].get('short','NS');lg=f['league']['name'];ho=f['teams']['home']['name'];aw=f['teams']['away']['name'];mn=f['fixture']['status'].get('el','');venue=f['fixture'].get('venue','');date=f['fixture']['date']
    mk=mkey(ho,aw,date);pr=MS.get(mk,{})
    # KICKOFF
    if st in ['1H','2H'] and pr.get('status') not in ['1H','2H'] and f"{mk}-k" not in PD:
     PD.add(f"{mk}-k");save();post(f"🔴 KICK OFF!\n\n{ho} vs {aw}\n{lg} LIVE!\n{venue}",lg)
    # GOAL
    if hg is not None and ag is not None and (hg+ag)>0:
     gid=f"{mk}-{hg}-{ag}"
     if gid not in PD and pr.get('hg')!=hg or pr.get('ag')!=ag:
      if (pr.get('hg',0)+pr.get('ag',0))!=(hg+ag):
       PD.add(gid);save()
       post(f"⚽ GOOAL! {mn}'\n\n{ho} {hg}-{ag} {aw}\n{lg}",lg)
    # HT / FT
    if st=='HT' and f"{mk}-ht" not in PD:PD.add(f"{mk}-ht");save();post(f"⏸️ HALF TIME\n\n{ho} {hg}-{ag} {aw}\n{lg}",lg)
    if st=='FT' and f"{mk}-ft" not in PD and hg is not None:PD.add(f"{mk}-ft");save();post(f"✅ FULL TIME\n\n{ho} {hg}-{ag} {aw}\n{lg}",lg)
    MS[mk]={"status":st,"hg":hg,"ag":ag}
   time.sleep(40)
  except Exception as e:print(e);time.sleep(40)

threading.Thread(target=bot,daemon=True).start()
if __name__=="__main__":app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
