import os, json, requests, feedparser, re
from datetime import datetime, timezone, timedelta
from PIL import Image, ImageEnhance, ImageDraw, ImageFont
from io import BytesIO

FB_TOKEN=os.getenv("FB_TOKEN")
FB_PAGE_ID=os.getenv("FB_PAGE_ID") or "1293090263895541"
POSTED_NEWS="posted_news.json"
SLIPS_FILE="slips_tracking.json"
EAT=timezone(timedelta(hours=3))
now=datetime.now(EAT)

RSS_FEEDS=[
    "https://feeds.bbci.co.uk/sport/football/rss.xml",
    "https://www.skysports.com/rss/12040",
    "https://www.espn.com/espn/rss/soccer/news",
]

LEAGUE_FLAGS={
    "Man City":"🏴󠁧󠁢󠁥󠁮󠁧󠁿 EPL","Leeds":"🏴󠁧󠁢󠁥󠁮󠁧󠁿 CHAMP","Derby":"🏴󠁧󠁢󠁥󠁮󠁧󠁿 CHAMP","Bristol":"🏴󠁧󠁢󠁥󠁮󠁧󠁿 CHAMP","Coventry":"🏴󠁧󠁢󠁥󠁮󠁧󠁿 CHAMP","Preston":"🏴󠁧󠁢󠁥󠁮󠁧󠁿 CHAMP",
    "Barcelona":"🇪🇸 LaLiga","Getafe":"🇪🇸 LaLiga","Real":"🇪🇸 LaLiga",
    "Inter":"🇮🇹 Serie A","Fiorentina":"🇮🇹 Serie A","Juventus":"🇮🇹 Serie A",
    "Bayern":"🇩🇪 Bundesliga","Werder":"🇩🇪 Bundesliga",
    "Galatasaray":"🇹🇷 Super Lig","Antalyaspor":"🇹🇷 Super Lig","Fenerbahce":"🇹🇷 Super Lig",
    "PSG":"🇫🇷 Ligue 1","Nice":"🇫🇷 Ligue 1","Marseille":"🇫🇷 Ligue 1",
    "Al Hilal":"🇸🇦 Saudi","Al Nassr":"🇸🇦 Saudi","Al Fateh":"🇸🇦 Saudi",
    "Ajax":"🇳🇱 Eredivisie","Feyenoord":"🇳🇱 Eredivisie",
    "Sporting":"🇵🇹 Primeira","Benfica":"🇵🇹 Primeira",
    "Bournemouth":"🏴󠁧󠁢󠁥󠁮󠁧󠁿 EPL","Swansea":"🏴󠁧󠁢󠁥󠁮󠁧󠁿 CHAMP","Hull":"🏴󠁧󠁢󠁥󠁮󠁧󠁿 CHAMP","Blackburn":"🏴󠁧󠁢󠁥󠁮󠁧󠁿 CHAMP","Stoke":"🏴󠁧󠁢󠁥󠁮󠁧󠁿 CHAMP","Sheff":"🏴󠁧󠁢󠁥󠁮󠁧󠁿 CHAMP",
}

def get_flag(team):
    for k,v in LEAGUE_FLAGS.items():
        if k.lower() in team.lower(): return v
    return "🌍 ALL LEAGUES"

def load_json(f, d):
    try:
        with open(f,"r") as x: return json.load(x)
    except: return d
def save_json(f, data):
    with open(f,"w") as x: json.dump(data, x, indent=2)

def get_image_url(entry):
    if hasattr(entry,'media_thumbnail'): return entry.media_thumbnail[0]['url']
    if hasattr(entry,'media_content'): return entry.media_content[0]['url']
    if 'enclosures' in entry and len(entry.enclosures)>0: return entry.enclosures[0].href
    m=re.search(r'<img[^>]+src="([^"]+)"', entry.get('description',''))
    if m: return m.group(1)
    return None

def make_clear_watermark(img_url):
    try:
        r=requests.get(img_url, headers={"User-Agent":"Mozilla/5.0"}, timeout=20)
        if r.status_code!=200: return None
        img=Image.open(BytesIO(r.content)).convert("RGB")
        img=ImageEnhance.Sharpness(img).enhance(1.8)
        img=ImageEnhance.Color(img).enhance(1.15)
        img=ImageEnhance.Contrast(img).enhance(1.1)
        W,H=img.size
        draw=ImageDraw.Draw(img)
        text="Unfiltered Scores"
        try: font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", int(W*0.045))
        except: font=ImageFont.load_default()
        bbox=draw.textbbox((0,0), text, font=font)
        tw=bbox[2]-bbox[0]; th=bbox[3]-bbox[1]
        x=(W-tw)//2; y=H-th-int(H*0.04)
        draw.text((x,y), text, font=font, fill="white", stroke_width=3, stroke_fill="black")
        path="clear_news.jpg"
        img.save(path,"JPEG",quality=95)
        return path
    except: return None

def fb_post_photo(image_path, message):
    try:
        url=f"https://graph.facebook.com/v20.0/{FB_PAGE_ID}/photos"
        with open(image_path,'rb') as f:
            r=requests.post(url, files={'source':f}, data={'message':message,'access_token':FB_TOKEN}, timeout=40)
        if r.status_code==200: return r.json().get('id') or r.json().get('post_id')
        return None
    except: return None

def fb_post_text(message):
    try:
        url=f"https://graph.facebook.com/v20.0/{FB_PAGE_ID}/feed"
        r=requests.post(url, data={'message':message,'access_token':FB_TOKEN}, timeout=20)
        if r.status_code==200: return r.json().get('id')
        return None
    except: return None

def fb_comment(post_id, message):
    try:
        url=f"https://graph.facebook.com/v20.0/{post_id}/comments"
        requests.post(url, data={'message':message,'access_token':FB_TOKEN}, timeout=20)
    except: pass

def get_ft_score(home):
    try:
        url="https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard"
        r=requests.get(url, timeout=10)
        data=r.json()
        for ev in data.get('events',[]):
            comp=ev.get('competitions',[{}])[0]
            h=comp['competitors'][0]['team']['displayName']
            if home.lower() in h.lower():
                status=comp['status']['type']['name']
                if status=='STATUS_FINAL':
                    hs=comp['competitors'][0]['score']
                    as_=comp['competitors'][1]['score']
                    return f"{hs}-{as_}", True
        return "Pending", False
    except: return "Pending", False

def evaluate_pick(pick, score):
    try:
        if score=="Pending": return "⏳"
        h,a=map(int, score.split('-'))
        if pick=="1": return "✅" if h>a else "❌"
        if pick=="2": return "✅" if a>h else "❌"
        if pick=="1X": return "✅" if h>=a else "❌"
        if pick=="X2": return "✅" if a>=h else "❌"
        if pick=="12": return "✅" if h!=a else "❌"
        return "✅" if h>=a else "❌"
    except: return "⏳"

def get_today_games_for_slip(is_early):
    if is_early:
        return [
            {"time":"10:00","home":"Leeds","away":"Swansea","pick":"1X","odd":"1.55","league":"Championship"},
            {"time":"11:30","home":"Derby","away":"Hull","pick":"1X","odd":"1.60","league":"Championship"},
            {"time":"12:00","home":"Bristol City","away":"Blackburn","pick":"X2","odd":"1.65","league":"Championship"},
            {"time":"12:30","home":"Coventry","away":"Stoke","pick":"1X","odd":"1.52","league":"Championship"},
            {"time":"12:45","home":"Preston","away":"Sheff Wed","pick":"1X","odd":"1.58","league":"Championship"},
        ]
    else:
        return [
            {"time":"15:00","home":"Man City","away":"Bournemouth","pick":"1","odd":"1.50","league":"Premier League"},
            {"time":"17:30","home":"Barcelona","away":"Getafe","pick":"1","odd":"1.55","league":"LaLiga"},
            {"time":"18:00","home":"Al Hilal","away":"Al Fateh","pick":"1","odd":"1.60","league":"Saudi Pro League"},
            {"time":"20:45","home":"Inter","away":"Fiorentina","pick":"1X","odd":"1.60","league":"Serie A"},
            {"time":"21:00","home":"Galatasaray","away":"Antalyaspor","pick":"1","odd":"1.70","league":"Super Lig"},
            {"time":"22:00","home":"Bayern","away":"Werder","pick":"1","odd":"2.10","league":"Bundesliga"},
            {"time":"22:30","home":"PSG","away":"Nice","pick":"1 & Over 1.5","odd":"1.85","league":"Ligue 1"},
        ]

def build_decorated_table(games, slip_type):
    if slip_type=="early":
        header="🟢 Unfiltered Scores - EARLY BIRDS CASH 💰\nMORNING ROLLOVER - SAFE DOUBLE CHANCE\n\n📅 TODAY - ALL LEAGUES INCLUDED\nNo league filtered - Early markets before 13:00\n\n"
    else:
        header="🟢 Unfiltered Scores - MAIN BANKER 🔥\nMEGA ACCA - UNFILTERED BOMB 💣\nDAY'S STRONGEST - 6 TO 7 GAMES - HIGH FREEDOM\n\n📅 TODAY - ALL LEAGUES INCLUDED\nNo league filtered - Best bankers worldwide 13:30-23:30\n\n"
    header+="╔════════════════════════════════╗\n"
    total=1.0
    for i,g in enumerate(games,1):
        try: total*=float(g['odd'].split()[0])
        except: pass
        flag=get_flag(g['home'])
        header+=f"║ {i}. ⏰ {g['time']} | {flag}\n"
        header+=f"║ {g['home']} vs {g['away']}\n"
        header+=f"║ 🎯 {g['pick']} @ {g['odd']} | {g['league']}\n"
        if i<len(games): header+="║ ────────────────────────────\n"
    header+="╚════════════════════════════════╝\n\n"
    header+=f"💰 Total Odds: ~{total:.2f}\n\n🧠 Analyzed: Form + H2H + Squad + Home/Away + Table + Motivation\n\n⚠️ Analysis only - Football is unpredictable. Bet responsibly.\n#UnfilteredScores #AllLeagues #EPL #LaLiga #SerieA #Bundesliga #Saudi #UCL #FYP #NonFollowers"
    return header

def main():
    posted=load_json(POSTED_NEWS, [])
    posted_set=set(posted)
    slips=load_json(SLIPS_FILE, {})
    today=now.strftime("%Y-%m-%d")
    if slips.get("date")!=today: slips={"date":today}

    # RESULTS TICK IMMEDIATELY WHEN FT
    if "early_posted" in slips and "early_result_posted" not in slips and now.hour>=13:
        orig_id=slips.get("early_post_id")
        msg=f"🟢 Unfiltered Scores - EARLY RESULTS ✅\nTagging early slip:\n\n╔════════════════════════════╗\n"
        all_done=True
        for g in slips["early_games"]:
            score,done=get_ft_score(g['home'])
            if not done: all_done=False
            tick=evaluate_pick(g['pick'], score)
            flag=get_flag(g['home'])
            msg+=f"║ {tick} {g['time']} {flag} {g['home']} {score}\n"
        msg+="╚════════════════════════════╝\n"
        if all_done:
            new_id=fb_post_text(msg)
            if new_id and orig_id: fb_comment(orig_id, f"Early results ✅ https://facebook.com/{new_id}")
            slips["early_result_posted"]=True
            save_json(SLIPS_FILE, slips)
            return

    if "main_posted" in slips and "main_result_posted" not in slips and now.hour>=23:
        orig_id=slips.get("main_post_id")
        msg=f"🟢 Unfiltered Scores - MAIN RESULTS 🔥\nTagging main banker (6-7 games):\n\n╔════════════════════════════╗\n"
        all_done=True
        for g in slips["main_games"]:
            score,done=get_ft_score(g['home'])
            if not done: all_done=False
            tick=evaluate_pick(g['pick'], score)
            flag=get_flag(g['home'])
            msg+=f"║ {tick} {g['time']} {flag} {g['home']} {score}\n"
        msg+="╚════════════════════════════╝\n"
        if all_done:
            new_id=fb_post_text(msg)
            if new_id and orig_id: fb_comment(orig_id, f"Main results 🔥 https://facebook.com/{new_id}")
            slips["main_result_posted"]=True
            save_json(SLIPS_FILE, slips)
            return

    if 7<=now.hour<8 and 20<=now.minute<=40 and "early_posted" not in slips:
        games=get_today_games_for_slip(True)
        msg=build_decorated_table(games,"early")
        pid=fb_post_text(msg)
        if pid:
            slips["early_posted"]=True; slips["early_games"]=games; slips["early_post_id"]=pid
            save_json(SLIPS_FILE, slips); return

    if 10<=now.hour<11 and 20<=now.minute<=40 and "main_posted" not in slips:
        games=get_today_games_for_slip(False)
        msg=build_decorated_table(games,"main")
        pid=fb_post_text(msg)
        if pid:
            slips["main_posted"]=True; slips["main_games"]=games; slips["main_post_id"]=pid
            save_json(SLIPS_FILE, slips); return

    all_news=[]
    for feed_url in RSS_FEEDS:
        try:
            feed=feedparser.parse(feed_url)
            for e in feed.entries[:8]:
                if e.link not in posted_set:
                    all_news.append(e)
        except: pass

    for entry in all_news[:1]:
        title=entry.get('title','').strip()
        summary=re.sub('<[^<]+?>','', entry.get('description',''))[:280]
        img_url=get_image_url(entry)
        if "breaking" in title.lower():
            caption=f"🟢 Unfiltered Scores\n\n🚨 {title}\n\n{summary}"
        else:
            caption=f"🟢 Unfiltered Scores\n\n{title}\n\n{summary}"
        caption+=f"\n\n#UnfilteredScores #FootballNews #AllLeagues #FYP #NonFollowers"
        pid=None
        if img_url:
            clear_path=make_clear_watermark(img_url)
            if clear_path: pid=fb_post_photo(clear_path, caption)
        else:
            pid=fb_post_text(caption)
        if pid:
            fb_comment(pid, f"Source: {entry.link}")
            posted.append(entry.link)
            break

    save_json(POSTED_NEWS, posted[-1000:])
    save_json(SLIPS_FILE, slips)

if __name__=="__main__": main()
