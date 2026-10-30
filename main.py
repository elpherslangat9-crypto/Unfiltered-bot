# V48 PRO FINAL - SHORT - ALL TOP LEAGUES
import os, json, requests, io, hashlib, random
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

PAGE=os.getenv("FB_PAGE_ID") or os.getenv("PAGE_ID")
TOKEN=os.getenv("FB_PAGE_TOKEN") or os.getenv("FB_TOKEN")

def load_mem():
    def ld(n):
        try:
            if os.path.exists(n): return json.load(open(n))
        except: pass
        return {}
    p=ld("posted_v38.json") or ld("posted.json") or {}
    s=ld("scores_v38.json") or {}
    sf=ld("schedule.json") or {}
    nt=ld("news_titles.json") or {}
    games=sf.get("games",{}) if isinstance(sf,dict) else {}
    if not games and isinstance(sf,dict) and len(sf)>3 and "games" not in sf: games=sf
    return {"posted":p,"scores":s,"sched":games,"sched_date":sf.get("date","") if isinstance(sf,dict) else "","news_titles":nt}

def save_mem(m):
    json.dump(m["posted"],open("posted_v38.json","w")); json.dump(m["posted"],open("posted.json","w"))
    json.dump(m["scores"],open("scores_v38.json","w"))
    json.dump({"date":m["sched_date"],"games":m["sched"]},open("schedule.json","w"))
    json.dump(m["news_titles"],open("news_titles.json","w"))

def fb_text(t):
    if not t.startswith("🟢"): t="🟢 "+t
    try: r=requests.post(f"https://graph.facebook.com/{PAGE}/feed",data={"message":t,"access_token":TOKEN},timeout=12); return r.status_code==200
    except: return False

def fb_file(path,cap):
    if not cap.startswith("🟢"): cap="🟢 "+cap
    try:
        with open(path,'rb') as f: r=requests.post(f"https://graph.facebook.com/{PAGE}/photos",files={'source':f},data={"caption":cap,"access_token":TOKEN},timeout=25); return r.status_code==200
    except: return False

def clean_lg(lg):
    l=lg.lower()
    d={"premier":"Premier League","laliga":"LaLiga","serie a":"Serie A","bundesliga":"Bundesliga","ligue 1":"Ligue 1","champions":"Champions League","europa":"Europa League","eredivisie":"Eredivisie","primeira":"Primeira Liga","super lig":"Turkish Super Lig","belgium":"Belgian Pro League","scottish":"Scottish Premiership","championship":"Championship","kenya":"Kenya PL","zambia":"Zambia SL","tanzania":"Tanzania PL","uganda":"Uganda PL","nigeria":"Nigeria NPFL","south africa":"South Africa PSL","egypt":"Egypt PL","morocco":"Morocco Botola","saudi":"Saudi Pro League","mls":"MLS"}
    for k,v in d.items():
        if k in l: return v
    return lg

def tags(lg):
    l=lg.lower()
    if "kenya" in l: return "#KPL #FootballLive"
    if "zambia" in l: return "#ZambiaSL #FootballLive"
    if "tanzania" in l: return "#LigiKuuBara #FootballLive"
    if "south africa" in l or "psl" in l: return "#PSL #FootballLive"
    if "egypt" in l: return "#EgyptPL #FootballLive"
    if "morocco" in l: return "#Botola #FootballLive"
    if "saudi" in l: return "#SaudiProLeague #Ronaldo #FootballLive"
    if "premier" in l: return "#PremierLeague #FootballLive"
    if "eredivisie" in l or "primeira" in l or "super lig" in l: return "#FootballLive #EuropeanFootball"
    return "#FootballLive #UnfilteredScores"

def ls_live():
    out=[]
    try:
        today=datetime.now().strftime("%Y%m%d")
        j=requests.get(f"https://prod-public-api.livescore.com/v1/api/app/date/soccer/{today}/3.00?MD=1",headers={"User-Agent":"Mozilla/5.0"},timeout=8).json()
        for s in j.get("Stages",[]):
            lg=s.get("Cnm","")+" "+s.get("Snm","")
            for e in s.get("Events",[]):
                eps=str(e.get("Eps",""))
                if eps in ["NS","","FT","AET","Postp.","Canc."]: continue
                h=e.get("T1",[{}])[0].get("Nm",""); a=e.get("T2",[{}])[0].get("Nm","")
                if h and a: out.append({"h":h,"a":a,"lg":lg,"gh":int(e.get("Tr1",0) or 0),"ga":int(e.get("Tr2",0) or 0),"st":eps,"m":eps,"norm":f"{h.lower()} vs {a.lower()}","fid":e.get("Eid","")})
    except: pass
    return out

def espn_live():
    out=[]; today=datetime.now().strftime("%Y%m%d")
    codes=["eng.1","esp.1","ger.1","ita.1","fra.1","ned.1","por.1","tur.1","sco.1","eng.2","uefa.champions","uefa.europa","ken.1","zam.1","tan.1","uga.1","rsa.1","egy.1","sau.1","usa.1"]
    for code in codes:
        try:
            j=requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{code}/scoreboard?dates={today}",timeout=5).json()
            for ev in j.get("events",[]):
                comp=ev["competitions"][0]
                if comp["status"]["type"]["completed"] or comp["status"]["type"]["state"]!="in": continue
                c1=comp["competitors"][0]; c2=comp["competitors"][1]
                h=c1["team"]["displayName"]; a=c2["team"]["displayName"]
                out.append({"h":h,"a":a,"lg":ev.get("league",{}).get("name",code),"gh":int(float(c1["score"])),"ga":int(float(c2["score"])),"st":"LIVE","m":comp["status"]["displayClock"],"norm":f"{h.lower()} vs {a.lower()}"})
        except: pass
    return out

def build_sched(m):
    today=datetime.now().strftime("%Y-%m-%d")
    if m["sched_date"]==today and len(m["sched"])>10: return
    try:
        td=datetime.now().strftime("%Y%m%d")
        j=requests.get(f"https://prod-public-api.livescore.com/v1/api/app/date/soccer/{td}/3.00?MD=1",headers={"User-Agent":"Mozilla/5.0"},timeout=8).json()
        games={}
        for s in j.get("Stages",[]):
            lg=s.get("Cnm","")+" "+s.get("Snm","")
            for e in s.get("Events",[]):
                h=e.get("T1",[{}])[0].get("Nm",""); a=e.get("T2",[{}])[0].get("Nm","")
                if h and a: games[f"{h.lower()} vs {a.lower()}"]={"h":h,"a":a,"lg":lg}
        if len(games)>=5: m["sched"]=games; m["sched_date"]=today
    except: pass

def make_hd(url):
    try:
        if "w=" in url: url=url.split("?")[0]+"?w=1280&quality=100"
        im=Image.open(io.BytesIO(requests.get(url,timeout=10,headers={"User-Agent":"Mozilla/5.0"}).content)).convert("RGB")
        w,h=im.size
        if w<1080: sc=1080/w; im=im.resize((int(w*sc),int(h*sc)),Image.LANCZOS); w,h=im.size
        im=ImageEnhance.Sharpness(im).enhance(1.4)
        bh=int(h*0.20); nh=h+max(bh,100)
        nim=Image.new("RGB",(w,nh),(0,0,0)); nim.paste(im,(0,0))
        d=ImageDraw.Draw(nim)
        try: fb=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",int(w*0.038)); fs=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",int(w*0.022))
        except: fb=ImageFont.load_default(); fs=ImageFont.load_default()
        d.ellipse((22,h+20,48,h+46),fill=(0,230,100)); d.text((58,h+18),"Unfiltered Scores",font=fb,fill=(255,255,255)); d.text((22,h+56),"Live Football Worldwide • HD",font=fs,fill=(220,220,220))
        out="/tmp/hd.jpg"; nim.save(out,"JPEG",quality=98,subsampling=0); return out
    except: return None

def main():
    print("🟢 V48 FINAL SHORT")
    m=load_mem(); build_sched(m)
    live=ls_live()+espn_live()
    merged={}
    for g in live:
        if g["norm"] not in merged: merged[g["norm"]]=g
    live=list(merged.values()); print(f"LIVE {len(live)}")
    
    # POST GAMES
    for g in live:
        norm=g["norm"]; lg=clean_lg(g["lg"]); t=tags(lg); gh=g["gh"]; ga=g["ga"]
        last=m["scores"].get(norm,{"gh":0,"ga":0})
        if gh<last["gh"] or ga<last["ga"]: continue
        kick=f"kick-{norm}"; goal=f"goal-{norm}-{gh}-{ga}"; ft=f"ft-{norm}"; ht=f"ht-{norm}"
        is_ft="FT" in g["st"]; is_ht="HT" in g["st"]
        if kick not in m["posted"]:
            if fb_text(f"⚽ KICKOFF: {g['h']} vs {g['a']}\n{lg} is LIVE!\n\n{t}"): m["posted"][kick]=1; m["scores"][norm]={"gh":gh,"ga":ga}; continue
        if not is_ft and not is_ht and gh+ga>0 and goal not in m["posted"] and (gh>last["gh"] or ga>last["ga"]):
            if fb_text(f"⚽ GOOAL! {g['m']}' {g['h']} {gh}-{ga} {g['a']}!\n{lg}\n\n{t}"): m["posted"][goal]=1; m["scores"][norm]={"gh":gh,"ga":ga}
        if is_ht and ht not in m["posted"]:
            if fb_text(f"⏸️ HALF: {g['h']} {gh}-{ga} {g['a']}\n{lg}\n\n{t}"): m["posted"][ht]=1
        if is_ft and ft not in m["posted"] and norm in m["scores"]:
            if fb_text(f"✅ FULL TIME: {g['h']} {gh}-{ga} {g['a']}\n{lg}\n\n{t}"): m["posted"][ft]=1

    # POST NEWS - 2 max
    if datetime.now().minute % 15 < 4:
        all_news=[]
        for u in ["https://site.api.espn.com/apis/site/v2/sports/soccer/news","https://site.api.espn.com/apis/site/v2/sports/soccer/ken.1/news","https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/news"]:
            try:
                for a in requests.get(u,timeout=5).json().get("articles",[])[:5]:
                    if a.get("images"): all_news.append({"id":str(a["id"]),"title":a["headline"],"desc":a.get("description","")[:150],"img":a["images"][0]["url"],"hash":hashlib.md5(a["headline"].lower().encode()).hexdigest()[:12]})
            except: pass
        cnt=0
        for n in all_news:
            if cnt>=2: break
            if f"news-{n['id']}" in m["posted"] or n["hash"] in m["news_titles"]: continue
            ph=make_hd(n["img"])
            if ph and fb_file(ph, f"📰 {n['title']}\n\n{n['desc']}...\n\n🟢 Unfiltered Scores"):
                m["posted"][f"news-{n['id']}"]=1; m["news_titles"][n["hash"]]=datetime.now().isoformat(); cnt+=1

    # VIRAL 5K - 1 per hour
    key=f"viral-{datetime.now().strftime('%Y-%m-%d-%H')}"
    if key not in m["posted"]:
        big=list(m["sched"].values()); txt=None
        if datetime.now().hour==6 and big: txt="🟢 TODAY'S FOOTBALL\n\n" + "\n".join([f"⚽ {g['h']} vs {g['a']} | {clean_lg(g['lg'])}" for g in big[:12]]) + "\n\n👇 Which game? SHARE!\n✅ FOLLOW for LIVE goals!\n\n#FixturesToday #FootballLive"
        elif datetime.now().hour==18 and big: g=random.choice(big[:6]); txt=f"🎯 PREDICT & WIN - ROAD TO 5K 🎯\n\n⚽ {g['h']} vs {g['a']}\n🏆 {clean_lg(g['lg'])}\n\n💰 WIN 100 KES airtime!\n1️⃣ FOLLOW 2️⃣ SHARE 3️⃣ COMMENT score\n\n#PredictAndWin #RoadTo5K"
        elif datetime.now().hour==20: txt="🇨🇩 Famille Congolaise - Merci! Si 5K, LINAFOOT LIVE lundi! Partagez! #Linafoot" if datetime.now().weekday()%2==0 else "🇰🇪 🇿🇲 Kenya+Zambia - At 5K FULL table daily! Tag friend! #KPL"
        if txt and fb_text(txt): m["posted"][key]=1

    save_mem(m); print("✅ DONE EXIT")

if __name__=="__main__": main()
