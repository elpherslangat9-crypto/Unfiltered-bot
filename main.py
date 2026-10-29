import os, json, time, requests, io
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageDraw, ImageFont

API_KEY=os.getenv("API_FOOTBALL_KEY")
PAGE=os.getenv("FB_PAGE_ID")
TOKEN=os.getenv("FB_PAGE_TOKEN")

def load_any(names):
    for n in names:
        try:
            if os.path.exists(n):
                d=json.load(open(n))
                if isinstance(d, dict): return d
        except: pass
    return {}
posted=load_any(["/tmp/p38.json","posted_v37.json","posted_v38.json","posted.json"])
scores=load_any(["/tmp/s38.json","scores_v37.json","scores_v38.json","scores.json"])
sched=load_any(["/tmp/sched38.json","schedule.json"])
USED={"api":0, "reset":datetime.now().strftime("%Y-%m-%d")}

def save():
    try:
        json.dump(posted,open("/tmp/p38.json","w")); json.dump(posted,open("posted_v38.json","w")); json.dump(posted,open("posted.json","w"))
        json.dump(scores,open("/tmp/s38.json","w")); json.dump(scores,open("scores_v38.json","w")); json.dump(scores,open("scores.json","w"))
        json.dump(sched,open("/tmp/sched38.json","w")); json.dump(sched,open("schedule.json","w"))
    except: pass

def fb_text(t):
    if not t.startswith("🟢"): t="🟢 "+t
    try:
        r=requests.post(f"https://graph.facebook.com/{PAGE}/feed",data={"message":t,"access_token":TOKEN},timeout=15)
        print(f"FB TEXT {r.status_code} {t[:80]}")
        return r.status_code==200
    except Exception as e: print(f"FB err {e}"); return False

def fb_photo_url(url,cap):
    if not cap.startswith("🟢"): cap="🟢 "+cap
    try:
        if "w=" in url: url=url.split("w=")[0]+"w=800"
        r=requests.post(f"https://graph.facebook.com/{PAGE}/photos",data={"url":url,"caption":cap,"access_token":TOKEN},timeout=20)
        return r.status_code==200
    except: return False

def fb_photo_file(path,cap):
    if not cap.startswith("🟢"): cap="🟢 "+cap
    try:
        with open(path,'rb') as f:
            r=requests.post(f"https://graph.facebook.com/{PAGE}/photos",files={'source':f},data={"caption":cap,"access_token":TOKEN},timeout=30)
            print(f"FB FILE {r.status_code}")
            return r.status_code==200
    except Exception as e: print(f"FILE err {e}"); return False

def make_news_image(img_url):
    # FIXED: Extend below, don't cover photo - green dot
    try:
        resp=requests.get(img_url,timeout=10)
        im=Image.open(io.BytesIO(resp.content)).convert("RGB")
        w,h=im.size
        if w>1080:
            nh=int(h*1080/w); im=im.resize((1080,nh), Image.LANCZOS); w,h=1080,nh
        bar_h=int(h*0.19)
        if bar_h<90: bar_h=90
        new_h=h+bar_h
        new_im=Image.new("RGB",(w,new_h),(0,0,0))
        new_im.paste(im,(0,0))
        draw=ImageDraw.Draw(new_im)
        try:
            fb=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", max(20,int(w*0.032)))
            fs=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", max(14,int(w*0.020)))
            fs_small=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", max(12,int(w*0.016)))
        except:
            fb=ImageFont.load_default(); fs=ImageFont.load_default(); fs_small=ImageFont.load_default()
        draw.ellipse((18, h+18, 38, h+38), fill=(0,230,100))
        draw.text((48, h+16), "Unfiltered Scores", font=fb, fill=(255,255,255))
        draw.text((18, h+48), "Live Football Worldwide", font=fs, fill=(200,200,200))
        corner="Unfiltered Scores"
        try: tw=draw.textbbox((0,0),corner,font=fs_small)[2]-draw.textbbox((0,0),corner,font=fs_small)[0]
        except: tw=len(corner)*7
        draw.text((w-tw-18, new_h-28), corner, font=fs_small, fill=(180,180,180))
        out="/tmp/news_branded.jpg"
        new_im.save(out,"JPEG",quality=90)
        return out
    except Exception as e:
        print(f"Brand err {e}"); return None

def clean_lg(lg):
    l=lg.lower()
    if "eng.1" in l or "premier" in l: return "Premier League"
    if "esp.1" in l or "laliga" in l or "la liga" in l: return "LaLiga"
    if "uefa.champions" in l: return "Champions League"
    if "ita.1" in l or "serie a" in l: return "Serie A"
    if "ger.1" in l or "bundesliga" in l: return "Bundesliga"
    if "fra.1" in l or "ligue 1" in l: return "Ligue 1"
    if "ken.1" in l or "kenya" in l: return "Kenya Premier League"
    if "zam.1" in l or "zambia" in l: return "Zambia Super League"
    if "tan.1" in l or "tanzania" in l: return "Tanzania Premier League"
    return lg

def tags(lg):
    l=lg.lower()
    if "kenya" in l: return "#KPL #KenyaFootball #FootballLive"
    if "zambia" in l: return "#ZambiaSuperLeague #FootballLive"
    if "tanzania" in l: return "#LigiKuuBara #FootballLive"
    if "premier league" in l: return "#PremierLeague #FootballLive"
    if "laliga" in l: return "#LaLiga #FootballLive"
    if "champions" in l: return "#ChampionsLeague #FootballLive"
    return "#FootballLive #UnfilteredScores"

def is_top_lineup(lg):
    l=lg.lower()
    return any(x in l for x in ["premier","eng.1","laliga","esp.1","champions","uefa.champions"])

def is_big(lg): return any(x in lg.lower() for x in ["premier","laliga","serie a","bundesliga","champions","kenya","zambia","tanzania","ligue 1"])

def ls_live():
    out=[]
    try:
        j=requests.get("https://prod-public-api.livescore.com/v1/api/app/stage/soccer/live",timeout=6).json()
        for s in j.get("Stages",[]):
            lg=s.get("Cnm","")+" "+s.get("Snm","")
            for e in s.get("Events",[]):
                eps=e.get("Eps","")
                if eps in ["FT","AET","Postp."] or eps in ["","NS"]: continue
                h=e.get("T1",[{}])[0].get("Nm",""); a=e.get("T2",[{}])[0].get("Nm","")
                if h and a:
                    out.append({"src":"LS","lg":lg,"h":h,"a":a,"st":eps,"m":eps,"gh":int(e.get("Tr1",0) or 0),"ga":int(e.get("Tr2",0) or 0),"norm":f"{h.lower()} vs {a.lower()}"})
    except Exception as e: print(f"LS err {e}")
    return out

def espn_live():
    out=[]; today=datetime.now().strftime("%Y%m%d")
    for code in ["ken.1","tan.1","zam.1","eng.1","esp.1","ger.1","ita.1","fra.1","uefa.champions"]:
        try:
            j=requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{code}/scoreboard?dates={today}",timeout=5).json()
            for ev in j.get("events",[]):
                if ev["competitions"][0]["status"]["type"]["state"]!="in": continue
                comp=ev["competitions"][0]
                h=comp["competitors"][0]["team"]["displayName"]; a=comp["competitors"][1]["team"]["displayName"]
                out.append({"src":"ESPN","lg":ev.get("league",{}).get("name",code),"h":h,"a":a,"st":"LIVE","m":comp["status"]["displayClock"] or "","gh":int(comp["competitors"][0]["score"]),"ga":int(comp["competitors"][1]["score"]),"norm":f"{h.lower()} vs {a.lower()}"})
        except: pass
    return out

def api_live():
    if USED["api"]>=75 or not API_KEY: return []
    try:
        r=requests.get("https://v3.football.api-sports.io/fixtures?live=all",headers={"x-apisports-key":API_KEY},timeout=7)
        USED["api"]+=1; out=[]
        for f in r.json().get("response",[]):
            out.append({"src":"API","fid":f['fixture']['id'],"lg":f["league"]["name"],"h":f["teams"]["home"]["name"],"a":f["teams"]["away"]["name"],"st":f["fixture"]["status"]["short"],"m":str(f["fixture"]["status"]["elapsed"] or ""),"gh":f["goals"]["home"] or 0,"ga":f["goals"]["away"] or 0,"norm":f"{f['teams']['home']['name'].lower()} vs {f['teams']['away']['name'].lower()}"})
        return out
    except: return []

def ls_schedule():
    out={}
    try:
        today=datetime.now().strftime("%Y%m%d")
        j=requests.get(f"https://prod-public-api.livescore.com/v1/api/app/date/soccer/{today}/3",timeout=6).json()
        for s in j.get("Stages",[]):
            lg=s.get("Cnm","")+" "+s.get("Snm","")
            for e in s.get("Events",[]):
                h=e.get("T1",[{}])[0].get("Nm",""); a=e.get("T2",[{}])[0].get("Nm","")
                if h and a:
                    norm=f"{h.lower()} vs {a.lower()}"
                    out[norm]={"h":h,"a":a,"lg":lg,"fid":e.get("Eid",""),"src":"LS"}
    except Exception as e: print(f"LS sched err {e}")
    return out

def build_schedule():
    global sched
    today=datetime.now().strftime("%Y-%m-%d")
    if USED["reset"]!=today: USED["api"]=0; USED["reset"]=today
    last=sched.get("built_h",-10); cur=datetime.now().hour
    if sched.get("date")==today and cur-last<2 and len(sched.get("games",{}))>15: return
    games={}; print("Building schedule ALL SOURCES...")
    if API_KEY and USED["api"]<35:
        try:
            r=requests.get(f"https://v3.football.api-sports.io/fixtures?date={today}",headers={"x-apisports-key":API_KEY},timeout=10)
            USED["api"]+=1
            for f in r.json().get("response",[]):
                norm=f"{f['teams']['home']['name'].lower()} vs {f['teams']['away']['name'].lower()}"
                games[norm]={"h":f['teams']['home']['name'],"a":f['teams']['away']['name'],"lg":f["league"]["name"],"fid":f['fixture']['id'],"src":"API","time":f['fixture']['date']}
            print(f"API {len(r.json().get('response',[]))}")
        except Exception as e: print(f"API err {e}")
    espn_codes=["eng.1","esp.1","ita.1","ger.1","fra.1","uefa.champions","uefa.europa","ken.1","tan.1","zam.1","ned.1","por.1"]
    cnt=0
    for code in espn_codes:
        try:
            j=requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{code}/scoreboard?dates={today.replace('-','')}",timeout=5).json()
            for ev in j.get("events",[]):
                comp=ev["competitions"][0]; h=comp["competitors"][0]["team"]["displayName"]; a=comp["competitors"][1]["team"]["displayName"]
                norm=f"{h.lower()} vs {a.lower()}"
                if norm not in games:
                    games[norm]={"h":h,"a":a,"lg":ev.get("league",{}).get("name",code),"fid":ev['id'],"src":"ESPN","time":ev.get('date','')}; cnt+=1
        except: pass
    print(f"ESPN +{cnt}")
    ls_sched=ls_schedule(); add=0
    for norm,data in ls_sched.items():
        if norm not in games: games[norm]=data; add+=1
    print(f"LS +{add}")
    if len(games)>=10:
        sched={"date":today,"built_h":cur,"games":games}; save()
        print(f"✅ SCHEDULE {len(games)} games")

def check_lineups():
    try:
        for norm,g in sched.get("games",{}).items():
            lg=g.get("lg","")
            if not is_top_lineup(lg): continue
            line_k=f"lineup-{norm}"
            if line_k in posted: continue
            fid=g.get("fid")
            if not fid or not str(fid).isdigit(): continue
            if API_KEY and USED["api"]<85:
                try:
                    r=requests.get(f"https://v3.football.api-sports.io/fixtures/lineups?fixture={fid}",headers={"x-apisports-key":API_KEY},timeout=5)
                    USED["api"]+=1
                    data=r.json().get("response",[])
                    if len(data)>=2:
                        h=g["h"]; a=g["a"]; clean=clean_lg(lg); t=tags(clean)
                        if fb_text(f"📋 LINEUPS: {h} vs {a}\nLineups confirmed ✅\n{clean} is starting soon!\n\n{t}"):
                            posted[line_k]=True; save(); print(f"Lineup posted {h} vs {a}"); time.sleep(2)
                except: pass
    except Exception as e: print(f"Lineup err {e}")

def scorer(fid):
    if USED["api"]>=90 or not API_KEY: return ""
    try:
        r=requests.get(f"https://v3.football.api-sports.io/fixtures/events?fixture={fid}",headers={"x-apisports-key":API_KEY},timeout=5)
        USED["api"]+=1
        for ev in reversed(r.json().get("response",[])):
            if ev.get("type")=="Goal": return f" Scorer: {ev.get('player',{}).get('name','')} ⚽"
        return ""
    except: return ""

def get_news():
    all_news=[]; urls=["https://site.api.espn.com/apis/site/v2/sports/soccer/news","https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/news","https://site.api.espn.com/apis/site/v2/sports/soccer/esp.1/news","https://site.api.espn.com/apis/site/v2/sports/soccer/uefa.champions/news","https://site.api.espn.com/apis/site/v2/sports/soccer/ger.1/news","https://site.api.espn.com/apis/site/v2/sports/soccer/ita.1/news","https://site.api.espn.com/apis/site/v2/sports/soccer/ken.1/news","https://site.api.espn.com/apis/site/v2/sports/soccer/zam.1/news"]
    for u in urls:
        try:
            data=requests.get(u,timeout=5).json()
            for a in data.get("articles",[])[:8]:
                if a.get("images"):
                    img=a["images"][0].get("url","")
                    if img: all_news.append({"id":str(a["id"]),"title":a["headline"],"desc":a.get("description","")[:160],"img":img})
        except: pass
    seen=set(); uniq=[]
    for n in all_news:
        if n["id"] not in seen: seen.add(n["id"]); uniq.append(n)
    return uniq[:40]

def bot():
    print("🟢 V43 FINAL - LINEUPS FIX + NO CUT PHOTO + GREEN BRAND")
    while True:
        try:
            build_schedule()
            if datetime.now().minute % 8 < 2: check_lineups()
            ls=ls_live()
            if len(ls)<5:
                with ThreadPoolExecutor(max_workers=2) as ex:
                    espn=ex.submit(espn_live).result(); api=ex.submit(api_live).result()
                all_games=ls+espn+api
                print(f"ALL LS:{len(ls)} ESPN:{len(espn)} API:{len(api)} -> {len(all_games)}")
            else:
                all_games=ls; print(f"LS ONLY {len(ls)} API {USED['api']}/75")
            merged={}
            for g in all_games:
                norm=g["norm"]
                if norm not in merged: merged[norm]=g
                elif g["src"]=="LS": merged[norm]=g
            valid=[]
            for norm,g in merged.items():
                last=scores.get(norm,{"gh":0,"ga":0})
                if g["gh"]<last["gh"] or g["ga"]<last["ga"]: continue
                key=f"{norm}-{g['gh']}-{g['ga']}"
                if key in posted: continue
                valid.append(g)
            print(f"VALID {len(valid)}")
            for g in valid:
                norm=g["norm"]; lg=clean_lg(g["lg"]); t=tags(lg)
                st=g["st"]; m=str(g["m"]); gh=g["gh"]; ga=g["ga"]
                is_ft="FT" in st or "AET" in st; is_ht="HT" in st
                kick_k=f"kick-{norm}"; goal_k=f"goal-{norm}-{gh}-{ga}"; ht_k=f"ht-{norm}"; ft_k=f"ft-{norm}"
                if kick_k not in posted:
                    if fb_text(f"⚽ KICKOFF: {g['h']} vs {g['a']}\n{lg} is LIVE now!\n\n{t}"):
                        posted[kick_k]=True; scores[norm]={"gh":gh,"ga":ga}; save()
                last=scores.get(norm,{"gh":0,"ga":0})
                if not is_ft and not is_ht and gh+ga>0 and goal_k not in posted and (gh>last["gh"] or ga>last["ga"]):
                    sc=scorer(g["fid"]) if "fid" in g and is_big(lg) else ""
                    if fb_text(f"⚽ GOOAL! {m}' {g['h']} {gh}-{ga} {g['a']}!{sc}\n{lg}\n\n{t}"):
                        posted[goal_k]=True; scores[norm]={"gh":gh,"ga":ga}; save()
                if is_ht and ht_k not in posted:
                    if fb_text(f"⏸️ HALF TIME: {g['h']} {gh}-{ga} {g['a']}\n{lg}\n\n{t}"):
                        posted[ht_k]=True; save()
                if is_ft and ft_k not in posted and norm in scores:
                    if fb_text(f"✅ FULL TIME: {g['h']} {gh}-{ga} {g['a']}\n{lg}\n\n{t}"):
                        posted[ft_k]=True; save()
            if datetime.now().minute % 10 < 4:
                news_list=get_news(); print(f"NEWS {len(news_list)}")
                cnt=0
                for n in news_list:
                    if cnt>=4: break
                    nid=f"news-{n['id']}"
                    if nid not in posted:
                        branded=make_news_image(n["img"])
                        caption=f"📰 {n['title']}\n\n{n['desc']}...\n\n━━━━━━━━━━━━━━━\n🟢 Unfiltered Scores | Live Football Worldwide\n#FootballLive #BreakingNews"
                        ok=False
                        if branded and os.path.exists(branded): ok=fb_photo_file(branded,caption)
                        if not ok: ok=fb_photo_url(n["img"],caption)
                        if ok: posted[nid]=True; save(); cnt+=1; time.sleep(3)
            time.sleep(7)
        except Exception as e:
            print(f"ERR {e}"); import traceback; traceback.print_exc(); time.sleep(7)

if __name__=="__main__": bot()
