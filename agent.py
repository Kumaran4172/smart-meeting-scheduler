"""
Smart Meeting Scheduler - Kaggle Capstone Project (Concierge Track)

Demonstrates 3 required AI Agent concepts:
1. Tool Use       → mock calendar read/write
2. Multi-step Planning → parse → find → rank → schedule
3. Memory         → store last scheduled time + preferences
"""

import json
import os
from datetime import datetime, timedelta
from dateutil import parser, tz

MEMORY_FILE = "user_memory.json"
CALENDAR_FILE = "mock_calendar.json"

# -------------------- Memory Functions --------------------
def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    return {}

def save_memory(mem):
    with open(MEMORY_FILE, "w") as f:
        json.dump(mem, f, indent=2)

# -------------------- Calendar Tool (Mock) --------------------
def load_calendar():
    if os.path.exists(CALENDAR_FILE):
        with open(CALENDAR_FILE, "r") as f:
            return json.load(f)
    return []

def save_calendar(cal):
    with open(CALENDAR_FILE, "w") as f:
        json.dump(cal, f, indent=2, default=str)

def add_event(start_iso, end_iso, title="Meeting"):
    cal = load_calendar()
    cal.append({
        "start": start_iso,
        "end": end_iso,
        "title": title
    })
    save_calendar(cal)
    return {"status": "ok", "event": {"start": start_iso, "end": end_iso, "title": title}}

def find_free_slots(start_window_iso, end_window_iso, duration_minutes=30):
    start_win = parser.isoparse(start_window_iso)
    end_win = parser.isoparse(end_window_iso)
    cal = load_calendar()

    # Convert events to datetime
    events = [(parser.isoparse(e["start"]), parser.isoparse(e["end"])) for e in cal]
    events.sort()

    delta = timedelta(minutes=duration_minutes)
    candidates = []
    cursor = start_win

    while cursor + delta <= end_win:
        slot_ok = True
        for s, e in events:
            if not (cursor + delta <= s or cursor >= e):
                slot_ok = False
                break
        if slot_ok:
            candidates.append((cursor.isoformat(), (cursor + delta).isoformat()))
        cursor += timedelta(minutes=30)

    return candidates

# -------------------- Planning & Ranking --------------------
def parse_request(text):
    text = text.lower()
    duration = 30

    if "1 hour" in text or "60" in text:
        duration = 60

    now = datetime.now(tz=tz.tzlocal())

    if "tomorrow" in text:
        target = now + timedelta(days=1)
        start = target.replace(hour=10, minute=0, second=0)
    elif "next week" in text:
        target = now + timedelta(days=7)
        start = target.replace(hour=10, minute=0, second=0)
    else:
        try:
            start = parser.parse(text, default=now)
            if start < now:
                start = now + timedelta(days=1)
                start = start.replace(hour=10, minute=0)
        except:
            start = now + timedelta(days=1)
            start = start.replace(hour=10, minute=0)

    end = start + timedelta(minutes=duration)
    return {"start": start.isoformat(), "end": end.isoformat(), "duration": duration}

def rank_slots(slots, prefs):
    if not slots:
        return []
    if not prefs:
        return [slots[0]]

    preferred = []
    for s, e in slots:
        hour = parser.isoparse(s).hour
        if prefs["preferred_start_hour"] <= hour < prefs["preferred_end_hour"]:
            preferred.append((s, e))
    return preferred if preferred else [slots[0]]

# -------------------- High-level Agent --------------------
def run_agent(user_id, text):
    mem = load_memory()

    prefs = mem.get(user_id, {
        "preferred_start_hour": 10,
        "preferred_end_hour": 17,
        "timezone": str(tz.tzlocal())
    })

    parsed = parse_request(text)

    start_window = datetime.now(tz=tz.tzlocal()).isoformat()
    end_window = (datetime.now(tz=tz.tzlocal()) + timedelta(days=3)).isoformat()

    slots = find_free_slots(start_window, end_window, parsed["duration"])
    ranked = rank_slots(slots, prefs)

    if not ranked:
        return {"status": "no-slots", "message": "No free slots found."}

    chosen = ranked[0]
    add_event(chosen[0], chosen[1], "Auto-scheduled meeting")

    prefs["last_scheduled"] = chosen[0]
    mem[user_id] = prefs
    save_memory(mem)

    return {"status": "scheduled", "slot": chosen}
