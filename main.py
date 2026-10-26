import os,time,threading,requests,json,random
from flask import Flask,render_template_string as R,jsonify,request,Response
from datetime import datetime,timezone,timedelta
from collections import defaultdict
app=Flask(__name__);P=os.environ
PID=P.get("PAGE_ID");PT=P.get("PAGE_TOKEN");KEY=P.get("FOOTBALL_API_KEY")
TB=P.get("TELEGRAM_BOT_TOKEN");TC=P.get("TELEGRAM_CHANNEL_ID","@unfiltered_scores")
H={"x-apisports-key":KEY} if KEY else {};EAT=timezone(timedelta(hours=3))
C={};LC={};LT=[];LE={"t":"","e":""};NW=[];MS={};PF="/tmp/posted.json"
try:PD=set(json.load(open(PF)) if os.path.exists(PF) else [])
except:PD=set()
def save_pd():
 try:json.dump(list(PD),open(PF,"w"))
 except:pass
def post(m, league=""):
 # TELEGRAM - KEEP VERCEL LINK - FAST EVERY GOAL
 try:
  if TB and TC:
   requests.post(f"https://api.telegram.org/bot{TB}/sendMessage",data={"chat_id":TC,"text":m},timeout=10)
   LT.insert(0,{"t":datetime.now(EAT).strftime("%H:%M"),"m":m})
   if len(LT)>30:LT.pop()
 except Exception as e:LE["e"]=str(e)[:80]
 # FACEBOOK - 100% CLEAN - NO VERCEL, NO LINK, NO HTTP - ONLY BIG PAGE STYLE
 try:
  if PID and PT:
   # Remove EVERYTHING Facebook hates
   fb=m
   fb=fb.replace("unfiltered-scores.vercel.app","").replace("https://","").replace("http://","").replace("Live:","").replace("FAST","").replace("⚡","").strip()
   # Clean for FB - only teams, score, league, minute
   hooks=["What a moment! Who saw it? Comment below! 👇","Live update! Who will win this? Drop your prediction! 💬","Unfiltered action! Are you watching this game? ❤️","Big moment! Tag a friend who missed it! 👇","Incredible! What's your score prediction? 👇","Live now! Follow for every goal!"]
   fb=fb+f"\n\n{random.choice(hooks)}"
   # Only 2-3 hashtags - Facebook hates many hashtags
   fb=fb+"\n\n#LiveScores #Football"
   # Post as pure text - no link = Facebook shows to followers like big pages
   r=requests.post(f"https://graph.facebook.com/{PID}/feed",data={"message":fb,"access_token":PT},timeout=15)
   if r.status_code==200:
    try:
     pid=r.json().get("id","")
     if pid:
      time.sleep(1)
      # Link ONLY in comment - Facebook allows this, big pages do same
      # Telegram keeps link, FB comment has no vercel mention - just page name
      requests.post(f"https://graph.facebook.com/{pid}/comments",data={"message":f"More live scores and lineups on our website and WhatsApp channel. Follow for every goal!","access_token":PT},timeout=10)
    except:pass
 except Exception as e:LE["e"]=str(e)[:80]
def live(d):
 try:
  y=d.replace("-","")
  if y in LC and time.time()-LC[y][0]<60:return LC[y][1]
  r=requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard?dates={y}",timeout=8)
  if r.status_code==200:
   F=[]
   for ev in r.json().get("events",[]):
    try:
     cp=ev.get("competitions",[{}])[0];cs=cp.get("competitors",[]);ho=next((c for c in cs if c.get("homeAway")=="home"),{});aw=next((c for c in cs if c.get("homeAway")=="away"),{});lg=ev.get("league",{});st=cp.get("status",{}).get("type",{});sn=st.get("name","");sv=st.get("state","");lv=sn in ["STATUS_IN_PROGRESS","STATUS_HALFTIME"] or sv=="in";ft=sn=="STATUS_FINAL";clock=cp.get("status",{}).get("displayClock","") or str(cp.get("status",{}).get("clock",0))
     F.append({"fixture":{"id":f"e-{ev.get('id')}","date":cp.get("date"),"status":{"short":"HT" if "HALFTIME" in sn else "1H" if lv else "FT" if ft else "NS","long":sn,"el":clock}},"league":{"name":lg.get("name","Football"),"country":"World"},"teams":{"home":{"name":ho.get("team",{}).get("displayName","Home")},"away":{"name":aw.get("team",{}).get("displayName","Away")}},"goals":{"home":int(ho.get("score",0)) if str(ho.get("score","")).isdigit() else None,"away":int(aw.get("score",0)) if str(aw.get("score","")).isdigit() else None}})
    except:continue
   if F:LC[y]=(time.time(),F);return F
 except:pass
 return []
def api(d):
 if d in C and time.time()-C[d][0]<300 and len(C[d][1])>0:return C[d][1]
 try:
  if KEY:
   r=requests.get("https://v3.football.api-sports.io/fixtures",headers=H,params={"date":d},timeout=12)
   if r.status_code==200:
    D=r.json().get("response",[])
    if D:C[d]=(time.time(),D);return D
 except Exception as e:LE["e"]=str(e);LE["t"]=datetime.now(EAT).strftime("%H:%M")
 return []
def get(d):
 x=live(d)
 return x if x else api(d)
@app.route('/api/day')
def ad():
 d=request.args.get('date') or datetime.now(EAT).strftime("%Y-%m-%d");s=request.args.get('search','').lower()
 F=get(d)
 if s:F=[f for f in F if s in f['teams']['home']['name'].lower() or s in f['teams']['away']['name'].lower() or s in f['league']['name'].lower()]
 F.sort(key=lambda f:f['fixture']['date']);G=defaultdict(list)
 for f in F:G[(f['league'].get('country','World'),f['league']['name'])].append(f)
 B=defaultdict(list)
 for (c,l),gm in G.items():B[c].append({"league":l,"games":gm})
 O=[{"country":c,"leagues":l} for c,l in B.items()];O.sort(key=lambda c:0 if 'kenya' in c['country'].lower() else 1 if 'england' in c['country'].lower() else 10)
 return jsonify({"date":d,"countries":O,"count":len(F),"source":"FAST" if any("e-" in str(f['fixture']['id']) for f in F) else "API","error":LE})
@app.route('/api/news')
def an():return jsonify({"news":NW})
@app.route('/api/match/<fid>')
def am(fid):
 L=[]
 try:
  if KEY and not str(fid).startswith("e-"):
   r=requests.get("https://v3.football.api-sports.io/fixtures/lineups",headers=H,params={"fixture":fid},timeout=10)
   if r.status_code==200:L=r.json().get("response",[])
 except:pass
 D=None
 try:
  if KEY and not str(fid).startswith("e-"):
   r=requests.get("https://v3.football.api-sports.io/fixtures",headers=H,params={"id":fid},timeout=10)
   if r.status_code==200:
    Rs=r.json().get("response",[])
    if Rs:D=Rs[0]
 except:pass
 return jsonify({"id":fid,"lineups":L,"detail":D})
def fetch_news():
 n=[]
 try:n.append({"id":"ballon","title":"Ballon d'Or TONIGHT! London 8PM GMT","desc":"Mbappe vs Yamal vs Kane! Winner 10PM EAT! Live on V16","time":datetime.now(EAT).strftime("%H:%M"),"type":"BALLON D'OR"})
 except:pass
 try:
  r=requests.get("https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/news?limit=4",timeout=6)
  if r.status_code==200:
   for a in r.json().get("articles",[])[:4]:n.append({"id":f"espn-{a.get('id')}","title":a.get("headline","")[:90],"desc":a.get("description","")[:110],"time":"Now","type":"EPL"})
 except:pass
 n.append({"id":"kpl","title":"KPL Live FAST Every goal","desc":"Gor Mahia,AFC,Tusker - All goals minute by minute","time":datetime.now(EAT).strftime("%H:%M"),"type":"LIVE"})
 return n
IC="<svg xmlns='http://www.w3.org/2000/svg' width='512' height='512'><rect width='512' height='512' rx='120' fill='black'/><text x='256' y='300' text-anchor='middle' font-weight='900' font-size='42' fill='#39FF14'>UNFILTERED</text><text x='256' y='350' text-anchor='middle' font-weight='900' font-size='52' fill='#39FF14'>SCORES</text></svg>"
@app.route('/icon.svg')
def ic():return Response(IC,mimetype='image/svg+xml')
@app.route('/manifest.json')
def mf():return jsonify({"name":"Unfiltered","short_name":"Unfiltered","start_url":"/","display":"standalone","background_color":"#000","theme_color":"#39FF14","icons":[{"src":"/icon.svg","sizes":"512x512"}]})
@app.route('/sw.js')
def sw():return Response("self.addEventListener('install',e=>self.skipWaiting());",mimetype='application/javascript')
@app.route('/debug')
def dbg():
 d=datetime.now(EAT).strftime("%Y-%m-%d");f=live(d);a=api(d)
 return f"<html><body style=background:#000;color:#fff;padding:20px;font-family:monospace><h2 style=color:#39FF14>V16.4 FB CLEAN - NO VERCEL</h2><p>FAST:{len(f)} | API:{len(a)} | POSTED:{len(PD)}</p><p>FB: NO LINK NO VERCEL NO HTTP - Like big pages</p><p>TG: Keeps vercel link FAST</p><p>Categories: Country > League</p></body></html>"
HTML="""<!DOCTYPE html><html><head><meta charset=UTF-8><meta name=viewport content=width=device-width,initial-scale=1><meta name=theme-color content=#39FF14><title>V16.4 CLEAN FB</title><link rel=manifest href=/manifest.json><link rel=icon href=/icon.svg><style>*{margin:0;padding:0;box-sizing:border-box}body{background:#000;color:#fff;font-family:Arial}.top{background:#000;position:sticky;top:0;z-index:20;border-bottom:2px solid #39FF14}.lb{display:flex;align-items:center;padding:12px;gap:10px}.lb img{width:42px;height:42px;border-radius:10px}.lb h1{color:#39FF14;font-size:16px}.sb{padding:8px 12px;background:#0a0a0a;display:flex;gap:8px}.sb input{flex:1;padding:10px 14px;border-radius:20px;border:1px solid #222;background:#151515;color:#fff;outline:none}.ds{display:flex;overflow-x:auto;background:#0a0a0a}.dt{min-width:60px;text-align:center;padding:10px 6px;border-bottom:3px solid transparent;cursor:pointer}.dt.active{border-bottom-color:#39FF14;background:#111}.co{max-width:700px;margin:0 auto}.ct{margin-top:12px;background:#0f0f0f}.ch{padding:10px 12px;background:#151515;font-size:13px;color:#39FF14;font-weight:bold;border-left:3px solid #39FF14}.lh{padding:8px 12px;font-size:12px;color:#aaa;background:#0a0a0a;display:flex;justify-content:space-between}.ma{padding:10px 12px;display:flex;align-items:center;gap:10px;border-top:1px solid #151515;background:#000;cursor:pointer}.ti{width:50px;font-size:11px;color:#39FF14;font-weight:bold;text-align:center}.te{flex:1;font-size:13px}.sc{font-weight:bold;font-size:13px;background:#111;padding:5px 8px;border-radius:6px;min-width:45px;text-align:center}.sc.live{background:#39FF14;color:#000;animation:pu 1.2s infinite}.sc.ht{background:#FFD700;color:#000}.ld{width:6px;height:6px;background:#39FF14;border-radius:50%;display:inline-block;animation:pu 1s infinite;margin-right:4px}@keyframes pu{0%{box-shadow:0 0 0 0 rgba(57,255,20,.7)}70%{box-shadow:0 0 0 6px rgba(57,255,20,0)}100%{box-shadow:0 0 0 0 rgba(57,255,20,0)}}.em{padding:40px 20px;text-align:center;color:#666}.nb{background:linear-gradient(90deg,#FFD700,#FFA500);color:#000;padding:8px 12px;font-size:11px;font-weight:bold;text-align:center;cursor:pointer}.bn{position:fixed;bottom:0;left:0;right:0;background:#0a0a0a;border-top:1px solid #1a1a1a;display:flex;justify-content:space-around;padding:8px 0}.bn div{font-size:10px;color:#666;text-align:center}.bn div.active{color:#39FF14}</style></head><body><div class=top><div class=lb><img src=/icon.svg><h1>UNFILTERED <span style=background:#39FF14;color:#000;font-size:8px;padding:2px 5px;border-radius:8px>V16.4 CLEAN FB</span></h1><span id=total style=color:#666;font-size:9px;margin-left:auto>...</span></div><div class=nb id=nb onclick=showNews()>Ballon d'Or TONIGHT! Tap news</div><div class=sb><input id=si placeholder="Search team..." onkeyup="if(event.key==='Enter') doSearch()"><button onclick=doSearch() style=background:#39FF14;color:#000;border:none;padding:10px 16px;border-radius:20px;font-weight:bold>Search</button></div><div class=ds id=ds></div></div><div class=co id=co><div class=em>Loading FAST...</div></div><div style=height:70px></div><div class=bn><div class=active>Scores</div><div style=color:#FFD700 onclick=showNews()>News</div><div style=color:#39FF14 onclick=window.open('/debug','_blank')>Debug</div></div><script>const EAT='Africa/Nairobi';let CD=new Date().toLocaleDateString('en-CA',{timeZone:EAT});let CS='';function gwd(){let d=[];let t=new Date();let day=t.getDay();let diff=t.getDate()-day+(day==0?-6:1);let m=new Date(t.setDate(diff));for(let i=0;i<7;i++){let dd=new Date(m);dd.setDate(m.getDate()+i);let iso=dd.toLocaleDateString('en-CA',{timeZone:EAT});let it=iso===CD;let lb=dd.toLocaleDateString('en',{weekday:'short',timeZone:EAT}).toUpperCase();d.push({iso,label:lb,num:dd.getDate(),it});}return d;}function rd(){let d=gwd();let h='';d.forEach(x=>{h+=`<div class=dt ${x.it?'active':''} onclick=ld('${x.iso}',this)><div style=font-size:11px;color:#888>${x.label}</div><div style=font-size:14px;font-weight:bold>${x.num}</div></div>`;});document.getElementById('ds').innerHTML=h;}function tt(i){try{return new Date(i).toLocaleTimeString('en-GB',{hour:'2-digit',minute:'2-digit',timeZone:EAT,hour12:false});}catch(e){return '';}}function doSearch(){CS=document.getElementById('si').value;ld(CD);}async function ld(date,el){if(el){document.querySelectorAll('.dt').forEach(x=>x.classList.remove('active'));el.classList.add('active');CD=date;}document.getElementById('co').innerHTML='<div class=em>Loading '+date+'...</div>';try{let url='/api/day?date='+date;if(CS) url+='&search='+encodeURIComponent(CS);let r=await fetch(url);let j=await r.json();document.getElementById('total').innerText=j.count+' • '+j.source;if(j.count==0){document.getElementById('co').innerHTML=`<div class=em><b>No games ${date}</b><br>${j.source}</div>`;return;}let html='';j.countries.forEach(c=>{c.leagues.forEach(l=>{html+=`<div class=ct><div class=ch>${c.country} • ${l.league}</div><div class=lh><span>${l.league}</span><span>${l.games.length} games</span></div>`;l.games.forEach(g=>{let time=tt(g.fixture.date);let st=g.fixture.status.short;let live=st=='1H'||st=='2H';let isHT=st=='HT';let ho=g.teams.home.name;let aw=g.teams.away.name;let sh=g.goals.home;let sa=g.goals.away;let txt=(sh!=null&&sa!=null)?`${sh}-${sa}`:time;let cl=live?'live':isHT?'ht':'';let liveIcon=live?`<span class=ld></span>`:'';let minute=g.fixture.status.el?` ${g.fixture.status.el}'`:'';let fid=g.fixture.id;html+=`<div class=ma onclick=window.open('/match/${fid}','_blank')><div class=ti>${liveIcon}${live||isHT?minute||st:time||st}</div><div class=te><div>${ho}</div><div>${aw}</div></div><div class=sc ${cl}>${txt}</div></div>`;});html+=`</div>`;});});document.getElementById('co').innerHTML=html;}catch(e){document.getElementById('co').innerHTML='<div class=em>Failed</div>';}}async function showNews(){document.getElementById('co').innerHTML='<div class=em>Loading News...</div>';try{let r=await fetch('/api/news');let j=await r.json();let h='<div style=padding:10px><h3 style=color:#FFD700>News Live</h3>';j.news.forEach(n=>{h+=`<div style=background:#111;border-left:3px solid #FFD700;padding:10px;margin:10px 0;border-radius:8px><div style=font-size:10px;color:#FFD700>${n.type} • ${n.time}</div><div style=font-weight:bold;margin:5px 0>${n.title}</div><div style=font-size:12px;color:#aaa>${n.desc}</div></div>`;});h+='</div>';document.getElementById('co').innerHTML=h;}catch(e){document.getElementById('co').innerHTML='<div class=em>News failed</div>';}}rd();ld(CD);setInterval(()=>ld(CD),10000);fetch('/api/news').then(r=>r.json()).then(j=>{if(j.news&&j.news[0]) document.getElementById('nb').innerText=j.news[0].title;});</script></body></html>"""
@app.route('/')
def home():return R(HTML)
def bot():
 print("V16.4 FB CLEAN - NO VERCEL")
 while True:
  try:
   now=datetime.now(EAT);global NW;NW=fetch_news();today=now.strftime("%Y-%m-%d");F=get(today)
   for f in F:
    fid=str(f['fixture']['id']);hg=f['goals']['home'];ag=f['goals']['away'];st=f['fixture']['status'].get('short','NS');lg=f['league']['name'];ho=f['teams']['home']['name'];aw=f['teams']['away']['name'];mn=f['fixture']['status'].get('el','');pr=MS.get(fid,{})
    if st in ['1H','2H'] and pr.get('status') not in ['1H','2H'] and f"{fid}-k" not in PD:PD.add(f"{fid}-k");save_pd();post(f"KICK OFF!\n\n{ho} vs {aw}\n\n{lg}",lg)
    if hg is not None and ag is not None:
     gid=f"{fid}-{hg}-{ag}"
     if gid not in PD and (hg+ag)>0:
      ph=pr.get('hg')
      if ph is None or hg>ph or ag>pr.get('ag',0):PD.add(gid);save_pd();post(f"GOAL! {mn}\n\n{ho} {hg}-{ag} {aw}\n\n{lg} FAST\nLive: unfiltered-scores.vercel.app",lg)
    if st=='HT' and f"{fid}-ht" not in PD:PD.add(f"{fid}-ht");save_pd();post(f"HALF TIME\n\n{ho} {hg}-{ag} {aw}\n\n{lg}",lg)
    if st=='FT' and f"{fid}-ft" not in PD and hg is not None:PD.add(f"{fid}-ft");save_pd();post(f"FULL TIME\n\n{ho} {hg}-{ag} {aw}\n\n{lg}\nLive: unfiltered-scores.vercel.app",lg)
    MS[fid]={"status":st,"hg":hg,"ag":ag}
   time.sleep(60)
  except Exception as e:print(e);time.sleep(60)
threading.Thread(target=bot,daemon=True).start()
if __name__=="__main__":app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
