import os,requests,json,random,xml.etree.ElementTree as ET,re
from datetime import datetime
from io import BytesIO
from PIL import Image,ImageDraw,ImageFont,ImageEnhance
from concurrent.futures import ThreadPoolExecutor
FB_TOKEN=os.getenv("FB_TOKEN") or os.getenv("FB_PAGE_ACCESS_TOKEN") or os.getenv("FB_PAGE_TOKEN")
FB_PAGE_ID=os.getenv("FB_PAGE_ID") or os.getenv("PAGE_ID") or "1293090263895541"
if not FB_PAGE_ID or FB_PAGE_ID.strip()=="0" or len(FB_PAGE_ID.strip())<5:FB_PAGE_ID="1293090263895541"
FOOTBALL_KEY=os.getenv("FOOTBALL_API_KEY") or os.getenv("API_FOOTBALL_KEY")
MAX_API=int(os.getenv("MAX_API_REQUESTS","95"))
POSTED_FILE="posted.json";COUNT_FILE="/tmp/api_count.json"
ALL_LEAGUES={39:"Premier League",140:"La Liga",2:"Champions League",3:"Europa League",78:"Bundesliga",135:"Serie A",61:"Ligue 1",88:"Eredivisie",94:"Primeira Liga",144:"Belgian Pro League",40:"Championship",79:"Bundesliga 2",531:"UEFA Conference",204:"Kenya FKF Premier",202:"Tanzania Premier",203:"Uganda Premier",201:"Rwanda Premier",233:"Egypt Premier",235:"Morocco Botola",236:"Algeria Ligue 1",237:"Tunisia Ligue 1",238:"South Africa PSL",239:"Nigeria NPFL",6:"CAF Champions League",7:"CAF Confederation Cup",400:"AFCON",11:"Africa WC Qualifiers"}
AFRICAN_IDS=[204,202,203,201,233,235,236,237,238,239,6,7,400,11]
EUROPEAN_IDS=[39,140,2,3,78,135,61,88,94,144,40,531]
def load_posted():
 try:
  with open(POSTED_FILE,"r") as f:return set([str(x) for x in json.load(f)])
 except:return set()
def save_posted(p):
 try:
  with open(POSTED_FILE,"w") as f:json.dump(list(p)[-1500:],f)
 except:pass
def get_api_count():
 try:
  with open(COUNT_FILE,"r") as f:
   d=json.load(f);return d["count"] if d["date"]==datetime.now().strftime("%Y-%m-%d") else 0
 except:return 0
def save_api_count(c):
 try:
  os.makedirs(os.path.dirname(COUNT_FILE),exist_ok=True)
  with open(COUNT_FILE,"w") as f:json.dump({"date":datetime.now().strftime("%Y-%m-%d"),"count":c},f)
 except:pass
def safe_name(s):return s.replace("/","").replace("\\","").replace(":","").replace(" ","_")[:25]
def create_image(home,away,league,score_text,home_logo,away_logo,state="LIVE"):
 W,H=1080,1080;bg=Image.new("RGB",(W,H),(10,15,25));draw=ImageDraw.Draw(bg)
 for y in range(H):draw.line([(0,y),(W,y)],fill=(int(10+y*0.08),int(15+y*0.05),int(25+y*0.1)))
 def get_logo(url):
  try:r=requests.get(url,timeout=10);logo=Image.open(BytesIO(r.content)).convert("RGBA");return logo.resize((340,340),Image.LANCZOS)
  except:return Image.new("RGBA",(340,340),(0,0,0,0))
 hl=get_logo(home_logo);al=get_logo(away_logo);bg.paste(hl,(110,280),hl);bg.paste(al,(630,280),al)
 try:fb=ImageFont.truetype("arial.ttf",80)
 except:fb=ImageFont.load_default()
 try:fs=ImageFont.truetype("arial.ttf",38)
 except:fs=ImageFont.load_default()
 try:fsmall=ImageFont.truetype("arial.ttf",32)
 except:fsmall=ImageFont.load_default()
 draw.text((W//2,420),"VS",fill="white",font=fb,anchor="mm");draw.text((280,680),home[:15],fill="white",font=fb,anchor="mm");draw.text((800,680),away[:15],fill="white",font=fb,anchor="mm");draw.text((W//2,780),score_text,fill=(0,255,136),font=fb,anchor="mm");draw.text((W//2,850),league,fill=(200,200,200),font=fs,anchor="mm");draw.text((W//2,900),state,fill=(255,215,0),font=fsmall,anchor="mm")
 overlay=Image.new("RGBA",(W,130),(0,255,136,235));bg.paste(overlay,(0,H-130),overlay);draw.text((W//2,H-65),"UNFILTERED SCORES",fill="black",font=fb,anchor="mm")
 path=f"/tmp/{safe_name(home)}_{safe_name(away)}_{safe_name(state)}_{int(datetime.now().timestamp())}.jpg";bg.save(path,"JPEG",quality=95,optimize=True);return path
def fb_text(msg):
 if not FB_TOKEN or not FB_PAGE_ID:return None
 url=f"https://graph.facebook.com/v20.0/{FB_PAGE_ID}/feed"
 try:r=requests.post(url,data={"message":msg,"access_token":FB_TOKEN},timeout=30);print(f"FB TEXT {r.status_code} {msg[:80]}\n{r.text[:500]}");return r
 except Exception as e:print(f"FB TEXT error {e}");return None
def fb_photo(msg,img_path):
 global FB_PAGE_ID
 if not FB_PAGE_ID or FB_PAGE_ID.strip()=="0" or len(FB_PAGE_ID.strip())<5:
  try:r=requests.get(f"https://graph.facebook.com/v20.0/me/accounts?access_token={FB_TOKEN}",timeout=15).json();FB_PAGE_ID=str(r["data"][0]["id"])
  except:return None
 url=f"https://graph.facebook.com/v20.0/{FB_PAGE_ID}/photos"
 try:
  with open(img_path,"rb") as fp:r=requests.post(url,files={"source":fp},data={"caption":msg,"access_token":FB_TOKEN},timeout=30);print(f"FB PHOTO {r.status_code} {msg[:60]}\n{r.text[:500]}");return r
 except Exception as e:print(f"FB PHOTO error {e}");return None
RSS_FEEDS=["http://feeds.bbci.co.uk/sport/football/rss.xml","https://www.espn.com/espn/rss/soccer/news","https://feeds.skynews.com/feeds/rss/sports.xml"]
OTHER_SPORTS_BLOCK=["tennis","cricket","rugby","nba","nfl","baseball","golf","formula 1"," f1 ","boxing","wwe","athletics","olympic","hockey","darts","snooker","volleyball","handball","badminton","ufc","mma","motogp","nascar","cycling","swimming","basketball","ncaa"]
FOOTBALL_MUST_HAVE=["football","soccer","premier league","la liga","serie a","bundesliga","ligue 1","eredivisie","champions league","europa","conference league","afcon","caf","fifa","uefa","fa cup","carabao cup","fkf","psl","botola","npfl","pl","epl","chelsea","arsenal","liverpool","man utd","man city","manchester","barcelona","real madrid","atletico","bayern","dortmund","psg","juventus","ac milan","inter milan","transfer","goal","league","cup","fixture","lineup","injury","manager","coach","club","striker","midfielder","defender"]
def is_football_news(title):
 t=title.lower()
 for bad in OTHER_SPORTS_BLOCK:
  if bad in t and not any(f in t for f in ["football","soccer","premier","fifa","uefa","caf"]):print(f"FILTERED OUT: {title}");return False
 if not any(f in t for f in FOOTBALL_MUST_HAVE):
  if " vs " not in t and "goal" not in t and "football" not in t:print(f"FILTERED OUT (no football): {title}");return False
 return True
def fetch_news_rss():
 items=[]
 for feed_url in RSS_FEEDS:
  try:
   r=requests.get(feed_url,timeout=12,headers={"User-Agent":"Mozilla/5.0"});root=ET.fromstring(r.content)
   for item in root.findall(".//item")[:15]:
    title=item.findtext("title","").strip()
    if not title or len(title)<15:continue
    if not is_football_news(title):continue
    link=item.findtext("link","");enc=item.find("enclosure");img=enc.get("url") if enc is not None else ""
    if not img:
     for ns in ["{http://search.yahoo.com/mrss/}content","media:content"]:
      m=item.find(ns)
      if m is not None:img=m.get("url","")
    if not img:img=f"https://images.unsplash.com/photo-1574629810360-214f3770f775?w=1080&h=1350&fit=crop&q=90&random={random.randint(1,1000)}"
    items.append({"title":title[:150],"image":img,"link":link})
  except Exception as e:print(f"RSS {feed_url} error {e}");continue
 print(f"RSS fetched {len(items)} FOOTBALL ONLY");return items
def fetch_real_image(article_url):
 try:
  r=requests.get(article_url,timeout=10,headers={"User-Agent":"Mozilla/5.0"});m=re.search(r'<meta property="og:image" content="([^"]+)"',r.text)
  if m:return m.group(1)
  m2=re.search(r'<meta name="twitter:image" content="([^"]+)"',r.text)
  if m2:return m2.group(1)
 except:pass
 return None
def create_news_image_clear(title,img_url,article_url=""):
 W,H=1080,1350;real_img=fetch_real_image(article_url) if article_url else None;target_url=real_img or img_url
 try:
  if target_url and "http" in target_url and ".svg" not in target_url:
   r=requests.get(target_url,timeout=15,headers={"User-Agent":"Mozilla/5.0"})
   if len(r.content)>15000:
    bg=Image.open(BytesIO(r.content)).convert("RGB");w,h=bg.size;bg=bg.resize((W,int(W*h/w)),Image.LANCZOS)
    if bg.height<H:bg=bg.resize((int(H*w/h),H),Image.LANCZOS)
    left=(bg.width-W)//2;top=max(0,(bg.height-H)//3);bg=bg.crop((left,top,left+W,top+H))
    bg=ImageEnhance.Brightness(bg).enhance(1.25);bg=ImageEnhance.Color(bg).enhance(1.30);bg=ImageEnhance.Contrast(bg).enhance(1.15)
   else:raise Exception("small")
  else:raise Exception("no url")
 except Exception as e:
  print(f"Real image fail {e}");bg=Image.new("RGB",(W,H),(22,33,62))
  try:r=requests.get("https://images.unsplash.com/photo-1522778119026-d647f0596c20?w=1080&h=1350&fit=crop&q=95",timeout=10);bg=Image.open(BytesIO(r.content)).convert("RGB").resize((W,H),Image.LANCZOS);bg=ImageEnhance.Brightness(bg).enhance(1.2)
  except:pass
 draw=ImageDraw.Draw(bg,"RGBA")
 try:font_small=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",36)
 except:font_small=ImageFont.load_default()
 draw.rectangle([(0,H-110),(W,H)],fill=(0,255,136,255));draw.text((W//2,H-55),"UNFILTERED SCORES",fill="black",font=font_small,anchor="mm")
 path=f"/tmp/news_{int(datetime.now().timestamp())}.jpg";bg.save(path,"JPEG",quality=98,optimize=True);return path
def fetch_european_livescore():
 games=[];espn_map={"eng.1":39,"esp.1":140,"uefa.champions":2,"uefa.europa":3,"ger.1":78,"ita.1":135,"fra.1":61,"ned.1":88,"por.1":94,"bel.1":144,"eng.2":40}
 for code,lid in espn_map.items():
  try:
   r=requests.get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{code}/scoreboard",timeout=12).json()
   for ev in r.get("events",[]):
    comp=ev["competitions"][0];games.append({"league_id":lid,"home":comp["competitors"][0]["team"]["displayName"],"away":comp["competitors"][1]["team"]["displayName"],"status_state":comp["status"]["type"]["state"],"status_detail":comp["status"]["type"]["detail"],"home_logo":comp["competitors"][0]["team"].get("logo",""),"away_logo":comp["competitors"][1]["team"].get("logo",""),"score":f"{comp['competitors'][0].get('score','0')}-{comp['competitors'][1].get('score','0')}","date":ev.get("date","")[:10],"id":ev.get("id","")})
  except:continue
 print(f"Euro {len(games)} games");return games
def fetch_african_api_parallel():
 used=get_api_count()
 if used>=MAX_API:print(f"API {used}/{MAX_API} OVER");return []
 try:
  today=datetime.now().strftime("%Y-%m-%d");r=requests.get("https://v3.football.api-sports.io/fixtures",headers={"x-apisports-key":FOOTBALL_KEY},params={"date":today},timeout=20);save_api_count(used+1);data=[]
  for fx in r.json().get("response",[]):
   lid=fx["league"]["id"]
   if lid in AFRICAN_IDS or lid in ALL_LEAGUES:
    if lid in AFRICAN_IDS or lid in EUROPEAN_IDS:data.append(fx)
  print(f"African {len(data)} fixtures");return data
 except Exception as e:print(f"African API error {e}");return []
def main():
 posted=load_posted();print(f"=== V61 FIXED - POSTED {len(posted)} ===")
 with ThreadPoolExecutor(max_workers=2) as ex:
  euro_f=ex.submit(fetch_european_livescore);af_f=ex.submit(fetch_african_api_parallel);euro_games=euro_f.result();african_games=af_f.result()
 today_utc=datetime.utcnow().strftime("%Y-%m-%d");today_local=datetime.now().strftime("%Y-%m-%d")
 euro_games=[g for g in euro_games if g.get("date","")==today_utc or g.get("date","")==today_local or g["status_state"]=="in" or not g.get("date")]
 print(f"Filtered {len(euro_games)} TODAY/LIVE")
 for g in euro_games:
  if g["league_id"] not in ALL_LEAGUES:continue
  base_key=f"{g['home']}_{g['away']}_{g.get('date','')}";state=g["status_state"];detail=g["status_detail"];league=ALL_LEAGUES[g["league_id"]]
  if state=="pre":
   key=f"lineup_{base_key}_{today_local}"
   if key not in posted and g["league_id"] in [39,140,2,78,135,61]:fb_text(f"📋 LINEUPS: {g['home']} vs {g['away']}\n🏆 {league}\n⏰ Kickoff soon! Predict score 👇\n\n#Lineup #UnfilteredScores");posted.add(key);save_posted(posted)
  elif state=="in" and ("0'" in detail or detail.startswith("0'")):
   key=f"kickoff_{base_key}_{today_local}"
   if key not in posted:fb_text(f"🟢 KICKOFF: {g['home']} vs {g['away']}\n🏆 {league} LIVE!\n\n#Live #UnfilteredScores");posted.add(key);save_posted(posted)
  elif state=="in":
   new_key=f"live_{base_key}_{detail}_{g['score']}_{today_local}";old_key=f"live_{base_key}_{detail}_{today_local}";old_simple=f"live_{g['home']}_{g['away']}_{detail}"
   if new_key in posted or old_key in posted or old_simple in posted:
    if (old_key in posted or old_simple in posted) and new_key not in posted:posted.add(new_key);save_posted(posted)
    continue
   fb_text(f"⚽ {detail}: {g['home']} {g['score']} {g['away']}\n🏆 {league}\n\n#FootballLive #UnfilteredScores");posted.add(new_key);posted.add(old_key);posted.add(old_simple);save_posted(posted)
  elif state=="post":
   if g.get("date","") and g.get("date","")!=today_utc and g.get("date","")!=today_local:continue
   key=f"ft_{base_key}_{today_local}"
   if key not in posted:fb_text(f"✅ FT: {g['home']} {g['score']} {g['away']}\n🏆 {league}\n\n#FullTime #UnfilteredScores");posted.add(key);save_posted(posted)
 for fx in african_games:
  fid=fx["fixture"]["id"];status=fx["fixture"]["status"]["short"];home=fx["teams"]["home"]["name"];away=fx["teams"]["away"]["name"];league=ALL_LEAGUES.get(fx["league"]["id"],"African Football");fixture_date=fx["fixture"]["date"][:10]
  if fixture_date!=today_local and fixture_date!=today_utc:continue
  if status=="NS":
   key=f"af_lineup_{fid}_{today_local}"
   if key not in posted and get_api_count()<MAX_API:
    try:
     r=requests.get("https://v3.football.api-sports.io/fixtures/lineups",headers={"x-apisports-key":FOOTBALL_KEY},params={"fixture":fid},timeout=10);save_api_count(get_api_count()+1)
     if r.json().get("response"):
      fb_text(f"📋 AFRICAN LINEUP: {home} vs {away}\n🏆 {league}\n\n#AfricanFootball #UnfilteredScores");posted.add(key);save_posted(posted)
    except:pass
  elif status in ["1H","2H","ET","LIVE","HT"]:
   key=f"af_live_{fid}_{status}_{fx['goals']['home']}_{fx['goals']['away']}_{today_local}";old_af_key=f"af_live_{fid}_{status}_{today_local}";old_simple=f"af_live_{fid}_{status}"
   if key in posted or old_af_key in posted or old_simple in posted:
    if (old_af_key in posted or old_simple in posted) and key not in posted:posted.add(key);save_posted(posted)
    continue
   fb_text(f"🌍 LIVE AFRICA: {home} {fx['goals']['home']}-{fx['goals']['away']} {away}\n🏆 {league} {status}\n\n#AfricanFootball #UnfilteredScores");posted.add(key);posted.add(old_af_key);posted.add(old_simple);save_posted(posted)
  elif status in ["FT","AET","PEN"]:
   key=f"af_ft_{fid}_{today_local}"
   if key not in posted:fb_text(f"✅ FT AFRICA: {home} {fx['goals']['home']}-{fx['goals']['away']} {away}\n🏆 {league}\n\n#FT #UnfilteredScores");posted.add(key);save_posted(posted)
 news_key=f"news_{datetime.now().strftime('%Y-%m-%d_%H')}"
 if news_key not in posted:
  news=fetch_news_rss()
  if news:
   football_news=[n for n in news if is_football_news(n["title"])]
   if football_news:n=random.choice(football_news);img=create_news_image_clear(n["title"],n["image"],n.get("link",""));fb_photo(f"🚨 {n['title']}\n\n#FootballNews #UnfilteredScores",img);posted.add(news_key);save_posted(posted)
 print("V61 FIXED DONE")
if __name__=="__main__":main()
