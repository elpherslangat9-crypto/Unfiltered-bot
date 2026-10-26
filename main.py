import os,time,threading,requests,json
from flask import Flask,render_template_string as R,jsonify,request,Response
from datetime import datetime,timezone,timedelta
from collections import defaultdict
app=Flask(__name__);P=os.environ
KEY=P.get("FOOTBALL_API_KEY");TB=P.get("TELEGRAM_BOT_TOKEN");TC=P.get("TELEGRAM_CHANNEL_ID","@unfiltered_scores")
H={"x-apisports-key":KEY} if KEY else {};EAT=timezone(timedelta(hours=3))
C={};LC={};LT=[];LE={"t":"","e":""};NW=[];MS={};PF="/tmp/posted.json"
try:PD=set(json.load(open(PF)) if os.path.exists(PF) else [])
except:PD=set()
def save_pd():
 try:json.dump(list(PD),open(PF,"w"))
 except:pass
def post_tg(m):
 try:
  if TB and TC:
   requests.post(f"https://api.telegram.org/bot{TB}/sendMessage",data={"chat_id":TC,"text":m},timeout=10)
   LT.insert(0,{"t":datetime.now(EAT).strftime("%H:%M"),"m":m})
   if len(LT)>50:LT.pop()
   print(f"TG POSTED: {m[:60]}")
 except Exception as e:LE["e"]=str(e)[:100];print(e)
def live(d):
 try:
  y=d.replace("-","")
  if y in LC and time.time()-LC[y][0]<30:return LC[y][1]
  r=requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard?dates={y}",timeout=10)
  if r.status_code==200:
   F=[]
   for ev in r.json().get("events",[]):
    try:
     cp=ev.get("competitions",[{}])[0];cs=cp.get("competitors",[]);ho=next((c for c in cs if c.get("homeAway")=="home"),{});aw=next((c for c in cs if c.get("homeAway")=="away"),{});lg=ev.get("league",{});st=cp.get("status",{}).get("type",{});sn=st.get("name","");sv=st.get("state","");lv=sn in ["STATUS_IN_PROGRESS","STATUS_HALFTIME"] or sv=="in";ft=sn=="STATUS_FINAL";clock=cp.get("status",{}).get("displayClock","") or str(cp.get("status",{}).get("clock",0))
     F.append({"fixture":{"id":f"e-{ev.get('id')}","date":cp.get("date"),"status":{"short":"HT" if "HALFTIME" in sn else "1H" if lv else "FT" if ft else "NS","long":sn,"el":clock}},"league":{"name":lg.get("name","Football"),"country":lg.get("name","World").split()[0] if " " in lg.get("name","") else "World","ccode":lg.get("abbreviation","WORLD")},"teams":{"home":{"name":ho.get("team",{}).get("displayName","Home")},"away":{"name":aw.get("team",{}).get("displayName","Away")}},"goals":{"home":int(ho.get("score",0)) if str(ho.get("score","")).isdigit() else None,"away":int(aw.get("score",0)) if str(aw.get("score","")).isdigit() else None}})
    except:continue
   if F:LC[y]=(time.time(),F);return F
 except Exception as e:LE["e"]=str(e)[:80]
 return []
def api(d):
 if d in C and time.time()-C[d][0]<180 and len(C[d][1])>0:return C[d][1]
 try:
  if KEY:
   r=requests.get("https://v3.football.api-sports.io/fixtures",headers=H,params={"date":d},timeout=15)
   if r.status_code==200:
    D=r.json().get("response",[])
    if D:C[d]=(time.time(),D);return D
 except Exception as e:LE["e"]=str(e)
 return []
def get(d):
 x=live(d)
 return x if x else api(d)
@app.route('/api/day')
def ad():
 d=request.args.get('date') or datetime.now(EAT).strftime("%Y-%m-%d");s=request.args.get('search','').lower()
 F=get(d)
 if s:F=[f for f in F if s in f['teams']['home']['name'].lower() or s in f['teams']['away']['name'].lower() or s in f['league']['name'].lower() or s in f['league'].get('country','').lower()]
 F.sort(key=lambda f:f['fixture']['date']);G=defaultdict(list)
 for f in F:G[(f['league'].get('country','World'),f['league']['name'])].append(f)
 B=defaultdict(list)
 for (c,l),gm in G.items():B[c].append({"league":l,"games":gm})
 O=[{"country":c,"leagues":l} for c,l in B.items()];O.sort(key=lambda c:(0 if 'kenya' in c['country'].lower() else 1 if 'england' in c['country'].lower() else 2 if 'spain' in c['country'].lower() else 10))
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
 try:n.append({"id":"live","title":"ALL LEAGUES LIVE - FAST GOALS","desc":"Every goal from every country live on Telegram","time":datetime.now(EAT).strftime("%H:%M"),"type":"LIVE"})
 except:pass
 try:
  r=requests.get("https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/news?limit=3",timeout=6)
  if r.status_code==200:
   for a in r.json().get("articles",[])[:3]:n.append({"id":f"espn-{a.get('id')}","title":a.get("headline","")[:90],"desc":a.get("description","")[:110],"time":"Now","type":"EPL"})
 except:pass
 return n
IC="<svg xmlns='http://www.w3.org/2000/svg' width='512' height='512'><rect width='512' height='512' rx='120' fill='black'/><text x='256' y='300' text-anchor='middle' font-weight='900' font-size='42' fill='#39FF14'>UNFILTERED</text><text x='256' y='350' text-anchor='middle' font-weight='900' font-size='52' fill='#39FF14'>SCORES</text></svg>"
@app.route('/icon.svg')
def ic():return Response(IC,mimetype='image/svg+xml')
@app.route('/manifest.json')
def mf():return jsonify({"name":"Unfiltered Scores - All Leagues","short_name":"Unfiltered","start_url":"/","display":"standalone","background_color":"#000","theme_color":"#39FF14","icons":[{"src":"/icon.svg","sizes":"512x512"}]})
@app.route('/sw.js')
def sw():return Response("self.addEventListener('install',e=>self.skipWaiting());",mimetype='application/javascript')
@app.route('/debug')
def dbg():
 d=datetime.now(EAT).strftime("%Y-%m-%d");f=live(d);a=api(d)
 return f"<html><body style=background:#000;color:#fff;padding:20px;font-family:monospace><h2 style=color:#39FF14>V17 TELEGRAM+WEBSITE ONLY</h2><p>FAST:{len(f)} | API:{len(a)} | POSTED:{len(PD)}</p><p>FB: DISABLED - DISCONNECTED</p><p>TG: FAST ALL LEAGUES</p><p>Countries: Shows country > league > time</p><p>Last:{LT[:2]}</p><p>Err:{LE}</p></body></html>"
HTML="""<!DOCTYPE html><html><head><meta charset=UTF-8><meta name=viewport content=width=device-width,initial-scale=1><meta name=theme-color content=#39FF14><title>V17 ALL LEAGUES</title><link rel=manifest href=/manifest.json><link rel=icon href=/icon.svg><style>*{margin:0;padding:0;box-sizing:border-box}body{background:#000;color:#fff;font-family:Arial}.top{background:#000;position:sticky;top:0;z-index:20;border-bottom:2px solid #39FF14}.lb{display:flex;align-items:center;padding:12px;gap:10px}.lb img{width:42px;height:42px;border-radius:10px}.lb h1{color:#39FF14;font-size:15px}.sb{padding:8px 12px;background:#0a0a0a;display:flex;gap:8px}.sb input{flex:1;padding:10px 14px;border-radius:20px;border:1px solid #222;background:#151515;color:#fff;outline:none}.ds{display:flex;overflow-x:auto;background:#0a0a0a}.dt{min-width:60px;text-align:center;padding:10px 6px;border-bottom:3px solid transparent;cursor:pointer}.dt.active{border-bottom-color:#39FF14;background:#111}.co{max-width:700px;margin:0 auto}.ct{margin-top:12px;background:#0f0f0f;border:1px solid #1a1a1a;border-radius:8px;overflow:hidden}.ch{padding:10px 12px;background:#151515;font-size:13px;color:#39FF14;font-weight:bold;border-left:3px solid #39FF14;display:flex;justify-content:space-between;align-items:center}.lh{padding:8px 12px;font-size:11px;color:#aaa;background:#0a0a0a;display:flex;justify-content:space-between;border-bottom:1px solid #151515}.ma{padding:10px 12px;display:flex;align-items:center;gap:10px;border-top:1px solid #151515;background:#000;cursor:pointer}.ti{width:55px;font-size:11px;color:#39FF14;font-weight:bold;text-align:center}.te{flex:1;font-size:13px;line-height:1.3}.sc{font-weight:bold;font-size:13px;background:#111;padding:6px 10px;border-radius:6px;min-width:48px;text-align:center}.sc.live{background:#39FF14;color:#000;animation:pu 1.2s infinite}.sc.ht{background:#FFD700;color:#000}.ld{width:6px;height:6px;background:#39FF14;border-radius:50%;display:inline-block;animation:pu 1s infinite;margin-right:4px}@keyframes pu{0%{box-shadow:0 0 0 0 rgba(57,255,20,.7)}70%{box-shadow:0 0 0 6px rgba(57,255,20,0)}100%{box-shadow:0 0 0 0 rgba(57,255,20,0)}}.em{padding:40px 20px;text-align:center;color:#666}.nb{background:linear-gradient(90deg,#39FF14,#00cc00);color:#000;padding:8px 12px;font-size:11px;font-weight:bold;text-align:center;cursor:pointer}.bn{position:fixed;bottom:0;left:0;right:0;background:#0a0a0a;border-top:1px solid #1a1a1a;display:flex;justify-content:space-around;padding:8px 0}.bn div{font-size:10px;color:#666;text-align:center}.bn div.active{color:#39FF14}</style></head><body><div class=top><div class=lb><img src=/icon.svg><h1>UNFILTERED <span style=background:#39FF14;color:#000;font-size:8px;padding:2px 5px;border-radius:8px>V17 ALL LEAGUES</span></h1><span id=total style=color:#666;font-size:9px;margin-left:auto>...</span></div><div class=nb id=nb>ALL LEAGUES LIVE FAST — Telegram + Website</div><div class=sb><input id=si placeholder="Search country, team, league..." onkeyup="if(event.key==='Enter') doSearch()"><button onclick=doSearch() style=background:#39FF14;color:#000;border:none;padding:10px 16px;border-radius:20px;font-weight:bold>Search</button></div><div class=ds id=ds></div></div><div class=co id=co><div class=em>Loading ALL leagues...</div></div><div style=height:70px></div><div class=bn><div class=active>Scores</div><div style=color:#39FF14 onclick=window.open('/debug','_blank')>Debug</div><div style=color:#39FF14 onclick=window.open('https://t.me/unfiltered_scores','_blank')>Telegram</div></div><script>const EAT='Africa/Nairobi';let CD=new Date().toLocaleDateString('en-CA',{timeZone:EAT});let CS='';function gwd(){let d=[];let t=new Date();let day=t.getDay();let diff=t.getDate()-day+(day==0?-6:1);let m=new Date(t.setDate(diff));for(let i=0;i<7;i++){let dd=new Date(m);dd.setDate(m.getDate()+i);let iso=dd.toLocaleDateString('en-CA',{timeZone:EAT});let it=iso===CD;let lb=dd.toLocaleDateString('en',{weekday:'short',timeZone:EAT}).toUpperCase();d.push({iso,label:lb,num:dd.getDate(),it});}return d;}function rd(){let d=gwd();let h='';d.forEach(x=>{h+=`<div class=dt ${x.it?'active':''} onclick=ld('${x.iso}',this)><div style=font-size:11px;color:#888>${x.label}</div><div style=font-size:14px;font-weight:bold>${x.num}</div></div>`;});document.getElementById('ds').innerHTML=h;}function tt(i){try{return new Date(i).toLocaleTimeString('en-GB',{hour:'2-digit',minute:'2-digit',timeZone:EAT,hour12:false});}catch(e){return '';}}function doSearch(){CS=document.getElementById('si').value;ld(CD);}async function ld(date,el){if(el){document.querySelectorAll('.dt').forEach(x=>x.classList.remove('active'));el.classList.add('active');CD=date;}document.getElementById('co').innerHTML='<div class=em>Loading '+date+'...</div>';try{let url='/api/day?date='+date;if(CS) url+='&search='+encodeURIComponent(CS);let r=await fetch(url);let j=await r.json();document.getElementById('total').innerText=j.count+' games • '+j.source;if(j.count==0){document.getElementById('co').innerHTML=`<div class=em><b>No games ${date}</b><br>Source: ${j.source}</div>`;return;}let html='';j.countries.forEach(c=>{c.leagues.forEach(l=>{let flag=c.country.substring(0,2).toUpperCase();html+=`<div class=ct><div class=ch><span>🌍 ${c.country.toUpperCase()} • ${l.league}</span><span style=background:#39FF14;color:#000;font-size:9px;padding:2px 6px;border-radius:10px>${l.games.length} GAMES</span></div><div class=lh><span>${l.league}</span><span>EAT Time</span></div>`;l.games.forEach(g=>{let time=tt(g.fixture.date);let st=g.fixture.status.short;let live=st=='1H'||st=='2H';let isHT=st=='HT';let ho=g.teams.home.name;let aw=g.teams.away.name;let sh=g.goals.home;let sa=g.goals.away;let txt=(sh!=null&&sa!=null)?`${sh}-${sa}`:time;let cl=live?'live':isHT?'ht':'';let liveIcon=live?`<span class=ld></span>`:'';let minute=g.fixture.status.el?` ${g.fixture.status.el}'`:'';let fid=g.fixture.id;html+=`<div class=ma onclick=window.open('/match/${fid}','_blank')><div class=ti>${liveIcon}${live||isHT?minute||st:time||st}</div><div class=te><div style=font-weight:bold>${ho}</div><div style=color:#aaa>${aw}</div></div><div class=sc ${cl}>${txt}</div></div>`;});html+=`</div>`;});});document.getElementById('co').innerHTML=html;}catch(e){document.getElementById('co').innerHTML='<div class=em>Failed to load</div>';}}rd();ld(CD);setInterval(()=>ld(CD),10000);</script></body></html>"""
@app.route('/')
def home():return R(HTML)
def bot():
 print("V17 TELEGRAM+WEBSITE ONLY - ALL LEAGUES FAST")
 while True:
  try:
   now=datetime.now(EAT);global NW;NW=fetch_news();today=now.strftime("%Y-%m-%d");F=get(today)
   print(f"Checking {len(F)} games {today}")
   for f in F:
    fid=str(f['fixture']['id']);hg=f['goals']['home'];ag=f['goals']['away'];st=f['fixture']['status'].get('short','NS');lg=f['league']['name'];country=f['league'].get('country','World');ho=f['teams']['home']['name'];aw=f['teams']['away']['name'];mn=f['fixture']['status'].get('el','');pr=MS.get(fid,{})
    if st in ['1H','2H'] and pr.get('status') not in ['1H','2H'] and f"{fid}-k" not in PD:PD.add(f"{fid}-k");save_pd();post_tg(f"⚽ KICK OFF!\n\n{country} - {lg}\n{ho} vs {aw}\n\nLive: unfiltered-scores.vercel.app")
    if hg is not None and ag is not None:
     gid=f"{fid}-{hg}-{ag}"
     if gid not in PD and (hg+ag)>0:
      ph=pr.get('hg')
      if ph is None or hg>ph or ag>pr.get('ag',0):
       PD.add(gid);save_pd()
       post_tg(f"🔥 GOAL! {mn}\n\n{country} - {lg}\n{ho} {hg}-{ag} {aw}\n\n⚡ Live: unfiltered-scores.vercel.app\n🌍 All leagues live")
    if st=='HT' and f"{fid}-ht" not in PD:PD.add(f"{fid}-ht");save_pd();post_tg(f"⏸️ HALF TIME\n\n{country} - {lg}\n{ho} {hg}-{ag} {aw}")
    if st=='FT' and f"{fid}-ft" not in PD and hg is not None:PD.add(f"{fid}-ft");save_pd();post_tg(f"✅ FULL TIME\n\n{country} - {lg}\n{ho} {hg}-{ag} {aw}\n\nLive: unfiltered-scores.vercel.app")
    MS[fid]={"status":st,"hg":hg,"ag":ag}
   time.sleep(30)
  except Exception as e:print(f"BOT ERR {e}");time.sleep(30)
threading.Thread(target=bot,daemon=True).start()
if __name__=="__main__":app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
