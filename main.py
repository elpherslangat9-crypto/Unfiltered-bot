import requests, time, os, json, random
from datetime import datetime

PAGE_ID = os.environ.get("PAGE_ID")
PAGE_TOKEN = os.environ.get("PAGE_TOKEN")
LAST_FILE = "last_scores.json"

# BEAT MatchCorner - Priority leagues only (no boring leagues spam)
TOP_LEAGUES = [7, 8, 17, 35, 1, 14, 679, 17015] # EPL, LaLiga, UCL, Bundesliga, etc
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0"}

def load_last():
    try:
        with open(LAST_FILE, "r") as f: return json.load(f)
    except: return {}

def save_last(d):
    with open(LAST_FILE, "w") as f: json.dump(f, d)

def fb_post(msg):
    url = f"https://graph.facebook.com/v19.0/{PAGE_ID}/feed"
    data = {"message": msg, "access_token": PAGE_TOKEN}
    r = requests.post(url, data=data)
    print(f"FB: {r.text[:200]}")
    # Anti-block: random sleep 45-90 sec after post
    time.sleep(random.randint(45,90))
    return r

def get_live():
    try:
        url = "https://api.sofascore.com/api/v1/sport/football/events/live"
        r = requests.get(url, headers=HEADERS, timeout=15)
        return r.json().get("events", [])
    except Exception as e:
        print(f"API Error: {e}")
        return []

def get_incidents(event_id):
    try:
        url = f"https://api.sofascore.com/api/v1/event/{event_id}/incidents"
        r = requests.get(url, headers=HEADERS, timeout=10)
        return r.json().get("incidents", [])
    except: return []

print("🔥 UNFILTERED SCORES - MATCHCORNER KILLER STARTED!")
last = load_last()

while True:
    events = get_live()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Checking {len(events)} live games")

    for ev in events:
        try:
            tournament_id = ev.get("tournament", {}).get("id", 0)
            # Filter: only Top leagues + any game with 2+ goals
            home = ev["homeTeam"]["name"]
            away = ev["awayTeam"]["name"]
            hs = ev["homeScore"].get("current", 0)
            aws = ev["awayScore"].get("current", 0)
            minute = ev.get("time", {}).get("currentPeriodStartTimestamp", 0)
            status = ev["status"]["type"]
            event_id = ev["id"]
            key = str(event_id)

            current_state = f"{hs}-{aws}-{status}"

            if last.get(key) == current_state:
                continue # No change, skip

            # --- GOAL DETECTION (BETTER THAN MATCHCORNER) ---
            if last.get(key) and last[key].split("-")[0] != str(hs) or last[key].split("-")[1] != str(aws) or key not in last:
                if status == "inprogress" and (hs + aws > 0):
                    # Try get scorer
                    scorer = ""
                    incidents = get_incidents(event_id)
                    for inc in reversed(incidents[-3:]):
                        if inc.get("incidentType") == "goal":
                            scorer = inc.get("player", {}).get("name", "")
                            goal_min = inc.get("time", 0)
                            is_home = inc.get("isHome", True)
                            scorer_text = f"\n⚽ Scorer: {scorer} ({goal_min}' )" if scorer else f"\n⏱️ {goal_min}'"
                            team_scored = home if is_home else away
                            break
                    else:
                        scorer_text = ""
                        team_scored = home if hs > int(last.get(key, "0-0-inprogress").split("-")[0]) else away

                    msg = f"🚨 GOAL ALERT! 🚨\n\n{home} {hs} - {aws} {away}{scorer_text}\n\n🔥 {team_scored} takes the lead!\n⏱️ LIVE - {ev.get('status', {}).get('description', 'LIVE')}\n\n#UnfilteredScores #Live #Football #GOAL"

                    fb_post(msg)
                    print(f"GOAL POSTED: {home} {hs}-{aws} {away}")

            # --- HALF TIME ---
            if status == "halftime" and "halftime" not in last.get(key, ""):
                msg = f"⏸️ HALF TIME\n\n{home} {hs} - {aws} {away}\n\nWhat a first half! Thoughts? 👇\n\n#HT #UnfilteredScores"
                fb_post(msg)

            # --- FULL TIME ---
            if status == "finished" and "finished" not in last.get(key, ""):
                winner = home if hs > aws else away if aws > hs else "DRAW!"
                msg = f"🏁 FULL TIME RESULT\n\n{home} {hs} - {aws} {away}\n\nWinner: {winner} 🔥\n\nDid your team win? Comment! 👇\n\n#FT #UnfilteredScores #Results"
                fb_post(msg)

            # --- RED CARD ---
            incidents = get_incidents(event_id) if key not in last else []
            for inc in incidents[-1:]:
                if inc.get("incidentType") == "card" and inc.get("incidentClass") == "red":
                    player = inc.get("player", {}).get("name", "Player")
                    msg = f"🟥 RED CARD!\n\n{home} vs {away}\n{player} SENT OFF! {inc.get('time', 0)}'\n\nScore: {hs} - {aws}\n\nGame changed! 😱\n\n#RedCard #UnfilteredScores"
                    fb_post(msg)

            last[key] = current_state
            save_last(last)

        except Exception as e:
            print(f"Loop error: {e}")
            continue

    # Clean old finished games (keep file small)
    if len(last) > 200:
        last = {k:v for k,v in list(last.items())[-100:]}
        save_last(last)

    wait = random.randint(70, 110) # Human-like 70-110 sec - BEATS spam filter
    print(f"Sleeping {wait}s...")
    time.sleep(wait)
