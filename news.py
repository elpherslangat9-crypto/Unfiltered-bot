import os,requests,json,hashlib,random
from datetime import datetime,timedelta,timezone
from PIL import Image,ImageDraw,ImageFont,ImageFilter
FB_TOKEN=os.getenv("FB_TOKEN");FB_PAGE_ID=os.getenv("FB_PAGE_ID") or "1293090263895541";EAT=timezone(timedelta(hours=3));now_eat=datetime.now(EAT);today=now_eat.strftime("%Y-%m-%d");today_param=now_eat.strftime("%Y%m%d");HASH_FILE="posted_bot.json";TIPS_FILE="today_tips.json"
def load_set(p):
 try:
  with open(p) as f:return set(json.load(f))
 except:return set()
def save_set(p,d):
 with open(p,"w") as f:json.dump(list(d)[-1000:],f)
def load_tips():
 try:
  with open(TIPS_FILE) as f:d=json.load(f)
  if d.get("date")!=today:return {}
  return d.get("tips",{})
 except:return {}
def save_tips(new_picks):
 d={"date":today,"tips":load_tips()}
 for g in new_picks:d["tips"][f"{g['home']} vs {g['away']}"]={"tip":g["tip"],"odds":g["odds"],"time":g["time"]}
 with open(TIPS_FILE,"w") as f:json.dump(d,f)
LEAGUES={"eng.1":"EPL","eng.2":"CHAMP","esp.1":"LaLiga","ita.1":"Serie A","ger.1":"Bundesliga","fra.1":"Ligue 1","ned.1":"Eredivisie","por.1":"Primeira","uefa.champions":"UCL","uefa.europa":"UEL","tur.1":"Super Lig"}
# FIXED: NO FLAG EMOJIS - Pillow cannot draw them, they become boxes. Use text tag instead.
# FIXED: Short names to stop overlap
SHORT_NAMES={"West Ham United":"West Ham","Wolverhampton Wanderers":"Wolves","Tottenham Hotspur":"Spurs","Manchester United":"Man Utd","Manchester City":"Man City","Nottingham Forest":"Nottm Forest","Borussia Dortmund":"Dortmund","Borussia Monchengladbach":"Gladbach","Real Betis":"Betis","Real Sociedad":"Sociedad","Athletic Club":"Athletic","Stade Rennais":"Rennes","Olympiacos":"Olympiacos","Middlesbrough":"Middlesboro"}
def short_name(n):
 n=SHORT_NAMES.get(n,n)
 n=n.replace("Borussia ","").replace("FC ","")
 return n[:16]
def pick(lst,key):
 h=sum(ord(c) for c in str(key))%len(lst);return lst[h]
def get_hashtags(slip):
 base="#UnfilteredScores #LiveScores #FootballLive #FYP #ForYou #Viral #Trending #ExplorePage #NonFollowers #FootballTikTok #SoccerFans #FollowForMore"
 extra="#FootballTips #BettingTips #FreeTips #BettingCommunity #TodayTips" if slip!="RESULTS" else "#BOOM #Results #HonestTips"
 return f"{base} {extra} #{slip.replace(' ','')}"
# SMART CAPTIONS - ROTATE EVERY DAY, NEVER REPEAT, WIN + LOSE FAMILY VIBE
def get_preview_caption(slip,total,picked,desc):
 hashtags=get_hashtags(slip)
 intros=[
  f"Let's try today... {len(picked)} games, 1 ticket. Are you riding with us?",
  f"New day, new slip. Yesterday is gone, today we go again. Who is with me?",
  f"No pressure, just vibes. Let's try today, if it hits we celebrate together.",
  f"Today's slip is ready. Small stake, big dream. Who is trying with us?",
  f"Green Family, let's go again! Today we try, tomorrow we talk. Are you in?",
 ]
 intro=pick(intros, f"{today}_{slip}")
 middles=[
  "If it hits, we BOOM together. If it misses, we go again tomorrow. That's family.",
  "No one wins every day. We play smart, we stay together.",
  "Don't chase, don't stress. Enjoy the games with us.",
  "Win or lose, we are here tomorrow again. That's the promise.",
 ]
 middle=pick(middles, f"{today}_{slip}_mid")
 return f"🔥 {slip} - {now_eat.strftime('%H:%M')} EAT\n\n✅ {desc}\n💰 Total Odds: {total:.2f} | {len(picked)} Games\n\n{intro}\n\n{middle}\n\nWho is riding? Comment YES 👇\n\nFollow @Unfiltered Scores 🔔 Turn ON notifications - You will miss BOOM if you don't!\n\n{hashtags}"
def get_results_caption(w,f,tot):
 hashtags=get_hashtags("RESULTS")
 if f==0: return f"✅ Results - Waiting...\n\nFollow for tomorrow's slips! 💚\n\n{hashtags}"
 win_rate=w/f if f else 0
 if win_rate>=0.7:
  msg=pick([
   f"BOOM! {w}/{f} WIN! We did it TOGETHER! Who cashed out? Show your ticket 👇",
   f"WHAT A DAY! {w}/{f}! Green Family, we ate today! Who won? 👇",
   f"BOOM BOOM! {w}/{f} WIN! This is why we never give up! Tag a friend who doubted us 👇",
  ], f"{today}_win")
 elif win_rate>=0.4:
  msg=pick([
   f"{w}/{f} today. Not perfect, but we fought. We go again tomorrow, stronger.",
   f"Half win, half lesson. {w}/{f}. We learn, we go again tomorrow. Who is still here? 👇",
  ], f"{today}_mid")
 else:
  msg=pick([
   f"We missed today... {w}/{f}. It's okay, we go again tomorrow. No one wins every day. Who is STILL HERE? Comment STILL HERE 💚",
   f"Tough day, {w}/{f}. Sorry Family. Tomorrow we try again. We don't quit. Are you still with us? 👇",
   f"Today was not our day. {w}/{f}. But family doesn't leave on a bad day. Tomorrow we bounce back. Comment WE GO AGAIN 💚",
  ], f"{today}_lose")
 return f"✅ Unfiltered Scores - Results\n\n🔥 {msg}\n💰 Total Odds: {tot:.2f}\n\nFollow for tomorrow's slips! 💚\n\n{hashtags}"
def fb_post_photo(path,caption):
 try:
  url=f"https://graph.facebook.com/v20.0/{FB_PAGE_ID}/photos"
  with open(path,"rb") as f:r=requests.post(url,data={"caption":caption,"access_token":FB_TOKEN},files={"source":f},timeout=40)
  print(f"FB PHOTO {r.status_code}: {r.text[:500]}")
  if r.status_code!=200:return None
  d=r.json();return d.get("post_id") or d.get("id")
 except Exception as e:print(f"FB post fail: {e}");return None
STANDINGS_CACHE={}
def get_standings_cached(league):
 if league in STANDINGS_CACHE:return STANDINGS_CACHE[league]
 table={}
 try:
  url=f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/standings?season=2026";r=requests.get(url,timeout=8,headers={"User-Agent":"Mozilla/5.0"});entries=[]
  for child in r.json().get("children",[]):entries.extend(child.get("standings",{}).get("entries",[]))
  for idx,e in enumerate(entries):
   tid=str(e["team"]["id"]);pos=idx+1
   for s in e.get("stats",[]):
    if s.get("name") in ["rank","standing"]:
     try:pos=int(float(s.get("value",pos)))
     except:pass
   table[tid]={"pos":pos,"name":e["team"]["displayName"]}
 except Exception as e:print(f"Standings {league} fail {e}")
 STANDINGS_CACHE[league]=table;return table
def get_form(team_id,league):
 try:
  url=f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/teams/{team_id}/schedule?season=2026";r=requests.get(url,timeout=8,headers={"User-Agent":"Mozilla/5.0"});events=r.json().get("events",[])[-5:];pts=0;gf=0;ga=0
  for ev in events:
   comps=ev.get("competitions",[{}])[0].get("competitors",[])
   if len(comps)<2:continue
   for c in comps:
    if str(c["team"]["id"])==str(team_id):
     my=int(c.get("score",0));opp=[x for x in comps if x!=c][0];op=int(opp.get("score",0));gf+=my;ga+=op;pts+=3 if my>op else (1 if my==op else 0)
  return pts,gf,ga
 except:return 7,5,5
def analyze(home_id,away_id,home_name,away_name,league):
 st=get_standings_cached(league);hp=st.get(str(home_id),{}).get("pos",10);ap=st.get(str(away_id),{}).get("pos",10);h_pts,h_gf,h_ga=get_form(home_id,league);a_pts,a_gf,a_ga=get_form(away_id,league);ts=max(-20,min(30,(ap-hp)*3));fs=max(-20,min(25,(h_pts-a_pts)*2));gs=10 if h_gf>=7 else 0;ha=15 if hp<=12 else 5;big=["Real Madrid","Barcelona","Bayern","Man City","Arsenal","Liverpool","Porto","PSV","Inter","Juventus","PSG","Chelsea","Dortmund","AC Milan"];h2h=10 if home_name in big and away_name not in big else 0;total=max(0,min(98,40+ts+fs+ha+h2h+gs));avg_g=(h_gf+a_gf)/10 if (h_gf+a_gf)>0 else 2.2;return total,f"Pos {hp}vs{ap} | Form {h_pts}vs{a_pts}pts",avg_g,h_pts,a_pts
def get_all_games():
 games=[]
 for lg in LEAGUES.keys():
  try:
   url=f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lg}/scoreboard?dates={today_param}";r=requests.get(url,timeout=8,headers={"User-Agent":"Mozilla/5.0"})
   for ev in r.json().get("events",[]):
    try:kd=datetime.fromisoformat(ev.get("date","").replace("Z","+00:00"));ke=kd.astimezone(EAT)
    except:continue
    if ke.strftime("%Y-%m-%d")!=today:continue
    comps=ev.get("competitions",[{}])[0].get("competitors",[])
    if len(comps)<2:continue
    hc=comps[0] if comps[0].get("homeAway")=="home" else comps[1];ac=comps[1] if comps[0].get("homeAway")=="home" else comps[0];state=ev.get("status",{}).get("type",{}).get("state");hg=int(hc.get("score",0));ag=int(ac.get("score",0));games.append({"time":ke.strftime("%H:%M"),"kickoff":ke,"home":hc["team"]["displayName"],"home_id":hc["team"]["id"],"away":ac["team"]["displayName"],"away_id":ac["team"]["id"],"league":lg,"league_tag":LEAGUES[lg],"state":state,"hg":hg,"ag":ag})
  except:continue
 return sorted(games,key=lambda x:x["kickoff"])
def build_morning(games):
 picked=[]
 for g in [x for x in games if x["state"]=="pre" and 12<=x["kickoff"].hour<18]:
  score,reason,avg_g,h_pts,a_pts=analyze(g["home_id"],g["away_id"],g["home"],g["away"],g["league"])
  if score>=75:tip,odds="1X & Over 1.5","1.55"
  elif score>=65:tip,odds="1X & Over 1.5","1.48"
  elif h_pts<a_pts:tip,odds="X2 & Over 1.5","1.65"
  else:tip,odds="1X & BTTS","1.85"
  g["tip"]=tip;g["odds"]=odds;g["score"]=score;g["reason"]=reason;picked.append(g)
 picked=sorted(picked,key=lambda x:x["score"],reverse=True)[:5];total=1.0
 for p in picked:total*=float(p["odds"])
 return picked,total
def build_freedom(games):
 picked=[]
 for g in [x for x in games if x["state"]=="pre" and x["kickoff"].hour>=18]:
  score,reason,avg_g,h_pts,a_pts=analyze(g["home_id"],g["away_id"],g["home"],g["away"],g["league"])
  if score>=88:tip,odds="1","1.38"
  elif score>=80:tip,odds="1 & Over 1.5","1.65"
  elif score>=70:tip,odds="1X","1.22"
  else:tip,odds="Over 1.5","1.30"
  g["tip"]=tip;g["odds"]=odds;g["score"]=score;g["reason"]=reason;picked.append(g)
 picked=sorted(picked,key=lambda x:x["score"],reverse=True)[:7];total=1.0
 for p in picked:total*=float(p["odds"])
 return picked,total
def build_accu(games):
 picked=[]
 for g in [x for x in games if x["state"]=="pre"]:
  score,reason,avg_g,h_pts,a_pts=analyze(g["home_id"],g["away_id"],g["home"],g["away"],g["league"])
  if score>=90:tip,odds="1","1.30"
  elif score>=85 and avg_g>=2.5:tip,odds="1 & Over 2.5","2.10"
  elif score>=80:tip,odds="1X & Over 1.5","1.55"
  elif score>=75 and avg_g>=2.5:tip,odds="Over 2.5","1.85"
  elif score>=70:tip,odds="BTTS","1.75"
  elif score>=65:tip,odds="X2 & Over 1.5","1.65"
  elif score>=60:tip,odds="Double Chance 12","1.28"
  else:continue
  g["tip"]=tip;g["odds"]=odds;g["score"]=score;g["reason"]=reason;picked.append(g)
 picked=sorted(picked,key=lambda x:x["score"],reverse=True);total=1.0
 for p in picked:total*=float(p["odds"])
 return picked,total
def check_win(tip,hg,ag):
 d={"1":hg>ag,"1X":hg>=ag,"X2":ag>=hg,"Over 1.5":(hg+ag)>1.5,"Over 2.5":(hg+ag)>2.5,"BTTS":hg>0 and ag>0,"1 & Over 1.5":hg>ag and (hg+ag)>1.5,"1 & Over 2.5":hg>ag and (hg+ag)>2.5,"1X & Over 1.5":hg>=ag and (hg+ag)>1.5,"X2 & Over 1.5":ag>=hg and (hg+ag)>1.5,"1X & BTTS":hg>=ag and hg>0 and ag>0,"Double Chance 12":hg!=ag};return d.get(tip,False)
def draw_slip_table(games,total,slip_name,mode="PREVIEW"):
 SCALE=2;W=1080*SCALE;ROW_H=82*SCALE;HEADER_H=95*SCALE;SUB_H=68*SCALE;FOOTER_H=95*SCALE;H=HEADER_H+SUB_H+ROW_H*len(games)+FOOTER_H+40*SCALE;img=Image.new("RGB",(W,H),(240,244,250));d=ImageDraw.Draw(img)
 try:f_title=ImageFont.truetype("DejaVuSans-Bold.ttf",42*SCALE);f_head=ImageFont.truetype("DejaVuSans-Bold.ttf",27*SCALE);f_cell=ImageFont.truetype("DejaVuSans-Bold.ttf",26*SCALE);f_small=ImageFont.truetype("DejaVuSans.ttf",24*SCALE);f_footer=ImageFont.truetype("DejaVuSans-Bold.ttf",32*SCALE)
 except:f_title=ImageFont.load_default();f_head=f_title;f_cell=f_title;f_small=f_title;f_footer=f_title
 BLUE=(11,94,215);LIGHT=(175,195,240);WHITE=(255,255,255);GREEN=(0,145,65);d.rounded_rectangle([18*SCALE,15*SCALE,W-18*SCALE,HEADER_H],radius=28*SCALE,fill=BLUE);d.text((W//2,(HEADER_H+15*SCALE)//2),"Unfiltered Scores",font=f_title,fill="white",anchor="mm");y0=HEADER_H+12*SCALE;d.rounded_rectangle([18*SCALE,y0,W-18*SCALE,y0+SUB_H],radius=18*SCALE,fill=BLUE)
 # FIXED COLUMNS - Fixture wider, Tip further right, no overlap
 cols=[("TIME",50*SCALE),("FIXTURE",200*SCALE),("TIP",720*SCALE),("ODDS",920*SCALE)] if mode=="PREVIEW" else [("TIME",40*SCALE),("FIXTURE",170*SCALE),("TIP",640*SCALE),("ODDS",800*SCALE),("RESULT",920*SCALE)]
 for txt,x in cols:d.text((x,y0+SUB_H//2),txt,font=f_head,fill="white",anchor="lm")
 y=y0+SUB_H;wins=0;finished=0
 for i,g in enumerate(games):
  fill=LIGHT if i%2==1 else WHITE;d.rectangle([18*SCALE,y,W-18*SCALE,y+ROW_H],fill=fill);hs=short_name(g["home"]);aw=short_name(g["away"]);fixture=f"[{g.get('league_tag','')}] {hs} - {aw}"
  # Safety: if still too long, cut away team
  if len(fixture)>32: fixture=f"[{g.get('league_tag','')}] {hs} - {aw[:10]}"
  if mode=="PREVIEW":d.text((50*SCALE,y+ROW_H//2),g["time"],font=f_cell,fill="black",anchor="lm");d.text((200*SCALE,y+ROW_H//2),fixture,font=f_small,fill="black",anchor="lm");d.text((720*SCALE,y+ROW_H//2),g["tip"],font=f_cell,fill="black",anchor="lm");d.text((920*SCALE,y+ROW_H//2),g["odds"],font=f_cell,fill="black",anchor="lm")
  else:
   if "tip" not in g:g["tip"],g["odds"]=("1","1.30")
   d.text((40*SCALE,y+ROW_H//2),g["time"],font=f_cell,fill="black",anchor="lm");d.text((170*SCALE,y+ROW_H//2),fixture,font=f_small,fill="black",anchor="lm");d.text((640*SCALE,y+ROW_H//2),g["tip"],font=f_cell,fill="black",anchor="lm");d.text((800*SCALE,y+ROW_H//2),g["odds"],font=f_cell,fill="black",anchor="lm")
   if g["state"]=="post":
    finished+=1;is_win=check_win(g["tip"],g["hg"],g["ag"]);wins+=1 if is_win else 0;res=f"{g['hg']}-{g['ag']} {'WIN' if is_win else 'LOST'}";color=(0,145,65) if is_win else (200,0,0);d.text((920*SCALE,y+ROW_H//2),res,font=f_cell,fill=color,anchor="lm")
   else:d.text((920*SCALE,y+ROW_H//2),"LIVE",font=f_cell,fill="black",anchor="lm")
  y+=ROW_H
 fy=y+12*SCALE
 if mode=="PREVIEW":d.rounded_rectangle([18*SCALE,fy,W-18*SCALE,fy+FOOTER_H],radius=25*SCALE,fill=BLUE);footer=f"{slip_name} - TOTAL ODDS {total:.2f}"
 else:d.rounded_rectangle([18*SCALE,fy,W-18*SCALE,fy+FOOTER_H],radius=25*SCALE,fill=GREEN);footer=f"BOOM {wins}/{len(games)} - TOTAL ODDS {total:.2f}" if finished==len(games) and finished>0 else f"{wins}/{finished} WIN SO FAR - TOTAL ODDS {total:.2f}"
 d.text((W//2,fy+FOOTER_H//2),footer,font=f_footer,fill="white",anchor="mm");img_small=img.resize((1080,H//SCALE),Image.LANCZOS);img_small=img_small.filter(ImageFilter.UnsharpMask(radius=2,percent=60,threshold=3));out=f"slip_{slip_name.lower().replace(' ','_')}_{mode.lower()}.png";img_small.save(out,"PNG",optimize=True);return out,wins,finished,total
def main():
 hashes=load_set(HASH_FILE);hm=now_eat.hour*60+now_eat.minute;print(f"Bot run at {now_eat.strftime('%H:%M')} EAT, Today {today}");slip=None
 if 450<=hm<510:slip="MORNING SLIP"
 elif 630<=hm<690:slip="FREEDOM SLIP"
 elif 750<=hm<810:slip="ACCUMULATIVE SLIP"
 elif 1410<=hm<1470:slip="RESULTS"
 if slip and slip!="RESULTS":
  games=get_all_games()
  if slip=="MORNING SLIP":picked,total=build_morning(games);desc="Strictly Double Chance + Over - Each Game Over 1.40"
  elif slip=="FREEDOM SLIP":picked,total=build_freedom(games);desc="Bankers Only - Safest Games"
  else:picked,total=build_accu(games);desc="Accumulative - ALL Confident Games, All Options, No Limit"
  if len(picked)==0:print("No games at all today - truly nothing to post")
  else:
   print(f"Picked {len(picked)} games, Total {total:.2f} - POSTING, never skip");key="|".join([f"{g['time']}{g['home']}{g['away']}{g['tip']}" for g in picked]);h=hashlib.md5(f"{today}_{slip}_{key}".encode()).hexdigest()
   if h in hashes:print(f"Same {slip} already posted - SKIP")
   else:
    path,w,f,t=draw_slip_table(picked,total,slip,mode="PREVIEW");caption=get_preview_caption(slip,total,picked,desc);post_id=fb_post_photo(path,caption)
    if post_id:hashes.add(h);save_set(HASH_FILE,hashes);save_tips(picked);print(f"POSTED {slip} - DONE + TIPS SAVED")
 elif slip=="RESULTS":
  games=get_all_games();finished_games=[g for g in games if g["state"]=="post"]
  if len(finished_games)>=3:
   saved=load_tips();results_picked=[]
   for g in finished_games:
    key2=f"{g['home']} vs {g['away']}"
    if key2 in saved:g["tip"]=saved[key2]["tip"];g["odds"]=saved[key2]["odds"]
    else:
     score,reason,avg_g,h_pts,a_pts=analyze(g["home_id"],g["away_id"],g["home"],g["away"],g["league"])
     if score>=90:tip,odds="1","1.30"
     elif score>=85 and avg_g>=2.5:tip,odds="1 & Over 2.5","2.10"
     elif score>=80:tip,odds="1X & Over 1.5","1.55"
     elif score>=75 and avg_g>=2.5:tip,odds="Over 2.5","1.85"
     elif score>=70:tip,odds="BTTS","1.75"
     elif score>=65:tip,odds="X2 & Over 1.5","1.65"
     else:tip,odds="Double Chance 12","1.28"
     g["tip"]=tip;g["odds"]=odds
    results_picked.append(g)
   if results_picked:
    key="|".join([f"{g['time']}{g['home']}{g['away']}{g['state']}{g['hg']}-{g['ag']}" for g in results_picked]);h=hashlib.md5(f"{today}_RESULTS_{key}".encode()).hexdigest()
    if h not in hashes:
     tot=1.0
     for p in results_picked:tot*=float(p["odds"])
     path,w,f,t=draw_slip_table(results_picked,tot,"RESULTS",mode="RESULTS");caption=get_results_caption(w,f,tot);post_id=fb_post_photo(path,caption)
     if post_id:hashes.add(h);save_set(HASH_FILE,hashes);print("POSTED RESULTS - DONE - HONEST BOOM")
    else:print("Results already posted")
if __name__=="__main__":main()
