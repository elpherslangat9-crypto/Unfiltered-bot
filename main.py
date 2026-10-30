# V48 FINAL - NO WHILE TRUE - FIXES YOUR ERROR
import os, json, requests, io, hashlib, random, time
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

PAGE=os.getenv("FB_PAGE_ID") or os.getenv("PAGE_ID")
TOKEN=os.getenv("FB_PAGE_TOKEN") or os.getenv("FB_TOKEN")
API_KEY=os.getenv("API_FOOTBALL_KEY")

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
    try: r=requests.post(f"https://graph.facebook.com/{PAGE}/feed",data={"message":t,"access_token":TOKEN},timeout=12); print(f"FB {r.status_code} {t[:60]}"); return r.status_code==200
    except Exception as e: print(f"FB ERR {e}"); return False

def clean_lg(lg):
    l=lg.lower()
    d={"premier":"Premier League","laliga":"LaLiga","champions":"Champions League","serie a":"Serie A","bundesliga":"Bundesliga","ligue 1":"Ligue 1","eredivisie":"Eredivisie","primeira":"Primeira Liga","super lig":"Turkish Super Lig","kenya":"Kenya PL","zambia":"Zambia SL","south africa":"South Africa PSL","saudi":"Saudi Pro League"}
    for k,v in d.items():
        if k in l: return v
    return lg

def tags(lg):
    l=lg.lower()
    if "premier" in l: return "#PremierLeague #EPL #FootballLive"
    if "laliga" in l: return "#LaLiga #FootballLive"
    if "champions" in l: return "#ChampionsLeague #UCL #FootballLive"
    if "kenya" in l: return "#KPL #FootballLive"
    if "saudi" in l: return "#SaudiProLeague #Ronaldo"
    return "#FootballLive #UnfilteredScores"

def is_lineup_league(lg):
    l=lg.lower()
    return ("premier" in l) or ("laliga" in l) or ("champions" in l and "africa" not in l)

def ls_live():
    out=[]
    try:
        today=datetime.now().strftime("%Y%m%d")
        j=requests.get(f"https://prod-public-api.livescore.com/v1/api/app/date/soccer/{today}/3.00?MD=1",headers={"User-Agent":"Mozilla/5.0"},timeout=8).json()
        for s in j.get("Stages",[]):
            lg=s.get("Cnm","")+" "+s.get("Snm","")
            for e in s.get("Events",[]):
                eps=str(e.get("Eps",""))
                if eps in ["FT","AET","Postp.","Canc."]: continue
                h=e.get("T1",[{}])[0].get("Nm",""); a=e.get("T2",[{}])[0].get("Nm","")
                if h and a: out.append({"h":h,"a":a,"lg":lg,"gh":int(e.get("Tr1",0) or 0),"ga":int(e.get("Tr2",0) or 0),"st":eps,"m":eps,"norm":f"{h.lower()} vs {a.lower()}","fid":e.get("Eid","")})
    except: pass
    return out

def espn_live():
    out=[]; today=datetime.now().strftime("%Y%m%d")
    for code in ["eng.1","esp.1","ger.1","ita.1","fra.1","ned.1","por.1","tur.1","uefa.champions","ken.1","zam.1","rsa.1","sau.1","usa.1"]:
        try:
            j=requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{code}/scoreboard?dates={today}",timeout=5).json()
            for ev in j.get("events",[]):
                comp=ev["competitions"][0]
                if comp["status"]["type"]["completed"]: continue
                c1=comp["competitors"][0]; c2=comp["competitors"][1]
                h=c1["team"]["displayName"]; a=c2["team"]["displayName"]
                out.append({"h":h,"a":a,"lg":ev.get("league",{}).get("name",code),"gh":int(float(c1["score"] or 0)),"ga":int(float(c2["score"] or 0)),"st":comp["status"]["type"]["shortDetail"],"m":comp["status"]["displayClock"],"norm":f"{h.lower()} vs {a.lower()}","fid":ev.get("id","")})
        except: pass
    return out

def main():
    print("🟢 V48 FINAL - NO LOOP - START")
    m=load_mem()
    live=ls_live()+espn_live()
    merged={}
    for g in live:
        if g["norm"] not in merged: merged[g["norm"]]=g
    live=list(merged.values()); print(f"LIVE {len(live)}")
    for g in live:
        norm=g["norm"]; lg=clean_lg(g["lg"]); t=tags(lg); gh=g["gh"]; ga=g["ga"]
        last=m["scores"].get(norm,{"gh":0,"ga":0})
        if gh<last["gh"] or ga<last["ga"]: continue
        st=g["st"]; is_ft="FT" in st; is_ht="HT" in st; is_ns=st in ["NS","","Pre"] or "vs" in st.lower()
        lineup_k=f"lineup-{norm}"; kick=f"kick-{norm}"; goal=f"goal-{norm}-{gh}-{ga}"; ft=f"ft-{norm}"; ht=f"ht-{norm}"
        if lineup_k not in m["posted"] and is_ns and is_lineup_league(g["lg"]):
            if fb_text(f"🔜 COMING UP: {g['h']} vs {g['a']}\n🏆 {lg}\n⏰ Lineup soon! Predict 👇\n\n{t}"): m["posted"][lineup_k]=1; continue
        if kick not in m["posted"] and not is_ns:
            if fb_text(f"⚽ KICKOFF: {g['h']} vs {g['a']}\n{lg} LIVE!\n\n{t}"): m["posted"][kick]=1; m["scores"][norm]={"gh":gh,"ga":ga}; continue
        if not is_ft and not is_ht and gh+ga>0 and goal not in m["posted"] and (gh>last["gh"] or ga>last["ga"]):
            if fb_text(f"⚽ GOOAL! {g['m']}' {g['h']} {gh}-{ga} {g['a']}!\n{lg}\n\n{t}"): m["posted"][goal]=1; m["scores"][norm]={"gh":gh,"ga":ga}
        if is_ht and ht not in m["posted"]:
            if fb_text(f"⏸️ HALF: {g['h']} {gh}-{ga} {g['a']}\n{lg}\n\n{t}"): m["posted"][ht]=1
        if is_ft and ft not in m["posted"] and norm in m["scores"]:
            if fb_text(f"✅ FULL TIME: {g['h']} {gh}-{ga} {g['a']}\n{lg}\n\n{t}"): m["posted"][ft]=1
    save_mem(m); print("✅ DONE - EXIT IN 20 SECONDS - NO LOOP")

if __name__=="__main__": main()
