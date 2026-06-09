import os, json
from datetime import datetime, timedelta
try:
    from ai_kernel_ import _query_ai
except Exception:
    def _query_ai(p): return ""

def _get_journal_texts(patient):
    try:
        from data_manager_ import get_patient_history
        entries = get_patient_history(patient)
        texts = []
        for e in entries[-7:]:
            raw = e.get("raw_content", "")
            texts.append(raw[:300])
        return texts
    except Exception:
        return []

def _get_grades(patient):
    try:
        from data_manager_ import load_followups
        tasks = [t for t in load_followups() if t["patient"] == patient]
        recent = [t for t in tasks if t.get("grade") and t["grade"] != "none"]
        return [t["grade"] for t in recent[-5:]]
    except Exception:
        return []

def _get_latest_note(patient):
    try:
        from data_manager_ import get_clinical_notes
        from patient_profiles_ import get_all_patients
        psychs = get_all_patients() or ["test_psych_1", "test_psych_2"]
        for psych in psychs:
            notes = get_clinical_notes(psych)
            for n in reversed(notes):
                if n["patient"] == patient:
                    return n.get("raw_notes", "") or n.get("ai_synthesis", "")
    except Exception:
        return ""
    return ""

def _get_psych_name(username):
    try:
        from patient_profiles_ import get_psychologist_name
        return get_psychologist_name(username)
    except Exception:
        return username

def _get_patient_name(username):
    try:
        from patient_profiles_ import get_patient_name
        return get_patient_name(username)
    except Exception:
        return username

def _get_bookings(patient=None):
    try:
        from data_manager_ import load_bookings
        bs = load_bookings()
        if patient:
            return [b for b in bs if b["patient"] == patient]
        return bs
    except Exception:
        return []

def _count_missed(patient):
    try:
        from data_manager_ import load_followups
        tasks = [t for t in load_followups() if t["patient"] == patient]
        return sum(1 for t in tasks if t["status"] == "not_yet")
    except Exception:
        return 0

def _count_recent_journals(patient):
    texts = _get_journal_texts(patient)
    return len(texts)


def triage_summary(patient: str) -> dict:
    journals = _get_journal_texts(patient)
    grades = _get_grades(patient)
    missed = _count_missed(patient)
    recent_j_count = len(journals)
    name = _get_patient_name(patient)

    prompt = (
        f"Patient: {name}. Recent journals: {' | '.join(journals[-3:]) if journals else 'none'}. "
        f"Recent follow-up grades: {grades if grades else 'none'}. "
        f"Missed tasks: {missed}. Journals last 7 days: {recent_j_count}. "
        "Assess priority (low/medium/high) and give a 1-line clinical assessment."
    )
    ai = _query_ai("You are a triage AI. " + prompt)
    if ai:
        return {"suggestion": ai, "priority": "high" if "high" in ai.lower() else ("medium" if "medium" in ai.lower() else "low"), "source": "ai"}

    reds = grades.count("red")
    yellows = grades.count("yellow")
    if reds >= 2 or missed >= 3:
        return {"suggestion": f"{name} — High priority. {reds} red grades, {missed} missed tasks.", "priority": "high", "source": "rule"}
    if yellows >= 2 or missed >= 1:
        return {"suggestion": f"{name} — Medium priority. Some flags detected.", "priority": "medium", "source": "rule"}
    return {"suggestion": f"{name} — Low priority. No significant flags.", "priority": "low", "source": "rule"}


def suggest_slots(patient: str, psych_username: str = "test_psych_1") -> dict:
    name = _get_patient_name(patient)
    psych_name = _get_psych_name(psych_username)

    grades = _get_grades(patient)
    missed = _count_missed(patient)
    journals = _get_journal_texts(patient)
    past_bookings = _get_bookings(patient)
    triage = triage_summary(patient)
    priority = triage.get("priority", "low")

    try:
        from data_manager_ import load_bookings
        all_bookings = load_bookings()
        pending_count = sum(1 for b in all_bookings if b.get("status") == "Pending")
    except Exception:
        pending_count = 0

    past_times = [b["time"] for b in past_bookings if b.get("time")]
    red_count = grades.count("red")
    urgency_score = red_count * 3 + len(grades) + missed * 2

    today = datetime.now()
    suggested = []
    preferred_time = "10:00"
    if past_times:
        from collections import Counter
        preferred_time = Counter(past_times).most_common(1)[0][0]

    if urgency_score >= 5:
        offset = 1
        reasoning = f"High urgency ({red_count} red grades, {missed} missed tasks). Earliest available."
    elif urgency_score >= 2:
        offset = 2
        reasoning = f"Medium urgency. Slots within the week at preferred time ({preferred_time})."
    else:
        offset = 3
        reasoning = f"Routine scheduling. Expanding options based on past patterns."

    for i in range(3):
        d = today + timedelta(days=offset + i)
        t = preferred_time
        if i == 2 and urgency_score < 2:
            t = f"{int(preferred_time.split(':')[0]) + 1:02d}:00"
        suggested.append({
            "date": d.strftime("%Y-%m-%d"),
            "day": d.strftime("%A"),
            "time": t,
            "label": f"{d.strftime('%A')} {d.strftime('%Y-%m-%d')} @ {t}",
        })

    return {
        "suggestion": "\n".join(s["label"] for s in suggested),
        "source": "rule",
        "priority": priority,
        "urgency_score": urgency_score,
        "workload": {"pending_bookings": pending_count},
        "suggested_slots": suggested,
        "reasoning": reasoning,
        "patient": patient,
        "psych_username": psych_username,
    }


def draft_followup(patient: str, psych_username: str = "test_psych_1") -> dict:
    name = _get_patient_name(patient)
    journals = _get_journal_texts(patient)
    grades = _get_grades(patient)
    missed = _count_missed(patient)
    note = _get_latest_note(patient)
    compliance = compliance_radar(patient)
    silence = silent_period_watch(patient)

    _all_journal_text = " | ".join(journals[-5:]) if journals else ""
    red_count = grades.count("red")
    yellow_count = grades.count("yellow")
    has_anxiety = any(w in _all_journal_text.lower() for w in ["anxious","stress","worried","panic","fear","overwhelm"])
    has_mood = any(w in _all_journal_text.lower() for w in ["sad","depressed","hopeless","empty","lonely","cry"])
    has_sleep = any(w in _all_journal_text.lower() for w in ["sleep","insomnia","tired","exhausted","nightmare"])
    has_crisis_theme = any(w in _all_journal_text.lower() for w in ["suicide","self-harm","hurt","emergency","die","hopeless","desperate"])

    tasks = []
    if red_count >= 2 or missed >= 3 or has_crisis_theme:
        tasks.append({
            "title": "Urgent Mood & Safety Check-In",
            "description": "Rate your current distress level (1-10) each morning and evening. Note any intrusive thoughts or urges. Contact support immediately if distress exceeds 7."
        })
    elif has_anxiety:
        tasks.append({
            "title": "Anxiety Management Log",
            "description": "Practice 5-5-5 breathing (inhale 5s, hold 5s, exhale 5s) whenever anxiety spikes. Log triggers, intensity (1-10), and which coping skill helped."
        })
    elif has_mood:
        tasks.append({
            "title": "Daily Mood Tracker",
            "description": "Rate your mood 3x daily (morning/afternoon/evening) on a 1-10 scale. Note one positive moment and one challenge each day."
        })
    elif has_sleep:
        tasks.append({
            "title": "Sleep Hygiene Log",
            "description": "Record bedtime, wake time, and sleep quality (1-10). Note caffeine/alcohol intake and screen time before bed."
        })
    else:
        tasks.append({
            "title": "Guided Reflection",
            "description": "Write 3-5 sentences about what went well this week, what was hard, and what you'd like to focus on next session."
        })

    if silence.get("flag"):
        tasks.append({
            "title": "Re-Connection Check-In",
            "description": f"No activity detected in {silence.get('days', 'several')} days. Write a brief update on what has been happening and how you're feeling today."
        })
    elif compliance.get("compliance", 100) < 70:
        tasks.append({
            "title": "Task Completion Reset",
            "description": f"Review your {missed} pending tasks. Pick 1 small goal to complete this week and describe what support you need to finish it."
        })
    elif red_count >= 1 or yellow_count >= 2:
        tasks.append({
            "title": "Skill Practice Log",
            "description": "Practice the coping skill we discussed in session. Log: date, skill used, before intensity (1-10), after intensity (1-10), and effectiveness."
        })
    else:
        tasks.append({
            "title": "Weekly Reflection Journal",
            "description": "Write 5 sentences about: highlights, challenges, something you learned, something you're grateful for, and a goal for next week."
        })

    prompt = (
        f"Patient: {name}. Journals: {_all_journal_text[:400]}. "
        f"Grades: {grades}. Missed: {missed}. Latest note: {note[:300] if note else 'none'}. "
        f"Analyze and suggest 2 follow-up tasks (title + short description) in JSON format: [{{\"title\":\"...\",\"description\":\"...\"}}]"
    )
    ai = _query_ai("You are a follow-up planning AI. " + prompt)
    if ai:
        try:
            import json as _json
            _parsed = _json.loads(ai.strip())
            if isinstance(_parsed, list) and len(_parsed) >= 1:
                for t in _parsed[:2]:
                    if t.get("title") and t.get("description"):
                        tasks[0] = t
        except Exception:
            pass

    return {
        "suggestion": "\n".join(f"{i+1}. {t['title']} — {t['description'][:80]}..." for i, t in enumerate(tasks[:2])),
        "source": "rule",
        "tasks": tasks[:2],
        "reasoning": f"Analyzed {len(journals)} journal entries, {len(grades)} grades ({red_count} red, {yellow_count} yellow), {missed} missed tasks.",
        "patient": patient,
        "psych_username": psych_username,
    }


THERAPY_REGISTRY = {
    "CBT (Cognitive Behavioral Therapy)": {
        "for": ["anxiety", "mood", "stress", "panic", "phobia", "ocd"],
        "techniques": ["Thought records", "Cognitive restructuring", "Behavioral activation", "Exposure therapy", "Socratic questioning"],
    },
    "CBT-I (Insomnia-Specific CBT)": {
        "for": ["sleep", "insomnia", "nightmare"],
        "techniques": ["Sleep restriction", "Stimulus control", "Cognitive restructuring about sleep", "Paradoxical intention"],
    },
    "DBT (Dialectical Behavior Therapy)": {
        "for": ["crisis", "self-harm", "suicidal", "emotional dysregulation", "bpd"],
        "techniques": ["Distress tolerance (TIPP)", "Emotion regulation", "Interpersonal effectiveness", "Mindfulness skills", "Radical acceptance"],
    },
    "Art Therapy": {
        "for": ["anxiety", "mood", "trauma", "stress", "grief"],
        "techniques": ["Emotion wheel painting", "Collage therapy", "Zentangle drawing", "Mandala coloring", "Expressive sculpture"],
    },
    "Music Therapy": {
        "for": ["anxiety", "mood", "sleep", "stress", "pain"],
        "techniques": ["Guided imagery with music", "Lyric analysis", "Rhythm-based drumming", "Binaural beats", "Mood-matching playlist"],
    },
    "Mindfulness-Based Therapy": {
        "for": ["anxiety", "mood", "stress", "panic", "general"],
        "techniques": ["Body scan meditation", "RAIN technique", "5-4-3-2-1 grounding", "Breathing exercises", "Loving-kindness meditation"],
    },
    "Interpersonal Therapy (IPT)": {
        "for": ["mood", "grief", "relationship", "loneliness", "isolation"],
        "techniques": ["Role disputes exploration", "Communication analysis", "Social rhythm regularization", "Grief processing"],
    },
    "Behavioral Activation": {
        "for": ["mood", "depression", "withdrawal", "isolation"],
        "techniques": ["Activity scheduling", "Pleasant events list", "Graded task assignment", "Mastery and pleasure tracking"],
    },
    "Somatic Therapy": {
        "for": ["anxiety", "stress", "trauma", "panic"],
        "techniques": ["Progressive muscle relaxation", "Body awareness", "Grounding exercises", "Breathwork", "Sensorimotor processing"],
    },
    "Sleep Hygiene Education": {
        "for": ["sleep", "insomnia", "fatigue"],
        "techniques": ["Consistent sleep schedule", "Screen time reduction", "Caffeine management", "Wind-down routine", "Bedroom environment optimization"],
    },
}


def _detect_themes(text: str) -> list:
    text_lower = text.lower()
    themes = set()
    if any(w in text_lower for w in ["anxious", "anxiety", "panic", "fear", "worried", "nervous", "dread", "terrified"]):
        themes.add("anxiety")
    if any(w in text_lower for w in ["sad", "depressed", "hopeless", "lonely", "empty", "cry", "miserable", "worthless", "anhedonia"]):
        themes.add("mood")
    if any(w in text_lower for w in ["sleep", "insomnia", "tired", "exhausted", "nightmare", "restless", "can't sleep", "fatigue"]):
        themes.add("sleep")
    if any(w in text_lower for w in ["stress", "overwhelm", "pressure", "burnout", "deadline", "workload", "overworked"]):
        themes.add("stress")
    if any(w in text_lower for w in ["suicide", "self-harm", "die", "end my life", "not exist", "hurt myself", "emergency", "want to disappear"]):
        themes.add("crisis")
    if any(w in text_lower for w in ["alone", "isolat", "withdrew", "no one", "nobody", "lonely"]):
        themes.add("isolation")
    if any(w in text_lower for w in ["angry", "rage", "frustrat", "irritabl", "snapped", "temper"]):
        themes.add("anger")
    if not themes:
        themes.add("general")
    return list(themes)


def _match_therapies(themes: list, text: str) -> list:
    text_lower = text.lower()
    scores = {}
    for tname, tinfo in THERAPY_REGISTRY.items():
        score = 0
        target_conditions = tinfo["for"]
        for theme in themes:
            if theme in target_conditions:
                score += 3
        for condition in target_conditions:
            if condition in text_lower:
                score += 2
        specific_keywords = {
            "CBT (Cognitive Behavioral Therapy)": ["thought", "think", "catastroph", "overthink", "ruminat", "negative"],
            "DBT (Dialectical Behavior Therapy)": ["urge", "impulse", "overwhelming emotion", "can't cope", "intense"],
            "Art Therapy": ["creative", "draw", "write", "express", "painting", "color"],
            "Music Therapy": ["music", "song", "listen", "calm", "playlist", "sound"],
            "Mindfulness-Based Therapy": ["breath", "calm", "present", "meditate", "relax", "mindful"],
            "Somatic Therapy": ["tight", "pain", "chest", "heart", "breathless", "body", "tension"],
            "Behavioral Activation": ["nothing", "no energy", "can't", "won't", "avoid", "stay in bed"],
            "Sleep Hygiene Education": ["bed", "night", "morning", "alarm", "screen", "phone", "caffeine"],
            "Interpersonal Therapy (IPT)": ["friend", "family", "partner", "relationship", "argue", "trust"],
        }
        for keyword in specific_keywords.get(tname, []):
            if keyword in text_lower:
                score += 1
        if score > 0:
            scores[tname] = score
    ranked = sorted(scores.items(), key=lambda x: -x[1])
    return [name for name, _ in ranked[:4]]


def journal_to_note(patient: str, journal_text: str, summary: str = "") -> dict:
    name = _get_patient_name(patient)
    themes = _detect_themes(journal_text)
    matched = _match_therapies(themes, journal_text)
    _obs = (summary or journal_text)[:400]

    prompt = (
        f"Patient: {name}. Journal summary: {_obs}. "
        f"Write a structured clinical note. Observations should summarize in 3rd person "
        f"(e.g. 'Patient reports...', 'Patient describes...'). "
        f"Assessment should evaluate emotional state and risk. "
        f"Plan should recommend 2-3 specific therapies from: {', '.join(matched)}. "
        f"Tailor each recommendation to the patient's specific presentation."
    )
    ai = _query_ai("You are a clinical documentation AI. " + prompt)
    if ai:
        return {"suggestion": ai, "source": "ai", "themes": themes, "matched_therapies": matched, "patient": patient}

    _assessment_map = {
        "crisis": "CRISIS: Patient expresses suicidal ideation or self-harm thoughts. Immediate risk assessment required. Ensure safety plan in place and consider emergency protocol.",
        "anxiety": "Patient exhibits symptoms of anxiety including somatic manifestations (chest tightness, elevated heart rate, shortness of breath) and cognitive patterns of catastrophizing. Work and social functioning may be impacted.",
        "panic": "Patient describes acute panic episodes with physical symptoms. Possible panic disorder. Avoidance behaviors may be developing.",
        "mood": "Patient presents with depressive symptoms including low mood, anhedonia, social withdrawal, and feelings of hopelessness. Energy and motivation significantly reduced.",
        "sleep": "Patient reports clinically significant sleep disturbance with daytime fatigue and functional impairment. Sleep quality and duration both affected.",
        "stress": "Patient experiencing chronic stress with features of burnout. Difficulty with emotional regulation and work-life boundaries under pressure.",
        "isolation": "Patient expresses feelings of loneliness and social disconnection. Limited support network and withdrawal from social activities noted.",
        "anger": "Patient reports irritability and anger outbursts, possibly secondary to underlying stress or mood disturbance. Impact on relationships noted.",
    }
    _default_assessment = "Patient processing routine emotional content. No acute concerns identified. General wellbeing maintenance recommended."

    _assessment = _default_assessment
    for theme_key in ["crisis", "panic", "anxiety", "mood", "sleep", "stress", "isolation", "anger"]:
        if theme_key in themes:
            _assessment = _assessment_map.get(theme_key, _default_assessment)
            break

    therapy_plans = {
        "CBT (Cognitive Behavioral Therapy)": "CBT — Challenge maladaptive thought patterns using thought records and cognitive restructuring. Focus on identifying cognitive distortions and developing balanced alternatives.",
        "DBT (Dialectical Behavior Therapy)": "DBT — Teach distress tolerance skills (TIPP technique) and emotion regulation strategies. Focus on building capacity to manage intense emotional states without escalation.",
        "Art Therapy": "Art therapy — Use expressive techniques (emotion wheel, collage, zentangle) to help patient externalize and process difficult emotions non-verbally.",
        "Music Therapy": "Music therapy — Employ mood-matching playlist progression, lyric analysis for emotional insight, or rhythmic drumming for somatic stress release.",
        "Mindfulness-Based Therapy": "Mindfulness — Practice body scan meditation for somatic awareness, RAIN technique for difficult emotions, or 5-4-3-2-1 grounding for acute distress.",
        "CBT-I (Insomnia-Specific CBT)": "CBT-I — Implement sleep restriction therapy and stimulus control. Address dysfunctional beliefs about sleep through cognitive restructuring.",
        "Behavioral Activation": "Behavioral activation — Schedule small achievable activities using graded task assignment. Track mastery and pleasure to rebuild positive reinforcement.",
        "Interpersonal Therapy (IPT)": "Interpersonal therapy — Explore social role disputes, communication patterns, and relationship difficulties. Address grief or role transitions as applicable.",
        "Somatic Therapy": "Somatic therapy — Use progressive muscle relaxation, breathwork, and body awareness exercises to release physiological tension stored in the body.",
        "Sleep Hygiene Education": "Sleep hygiene — Establish consistent sleep-wake schedule, reduce evening screen time, limit caffeine after 2pm, and create a wind-down routine.",
    }

    _plan_lines = []
    for i, t in enumerate(matched[:3], 1):
        plan_entry = therapy_plans.get(t, f"{t} — Based on clinical assessment, this modality is recommended to address identified themes.")
        _plan_lines.append(f"{i}. {plan_entry}")

    _plan = "\n".join(_plan_lines) if _plan_lines else "Monitor and discuss in next session."

    return {
        "suggestion": f"**Observations**: Patient {name} reports: {_obs}{'...' if len(_obs) >= 400 else ''}\n\n**Assessment**: {_assessment}\n\n**Plan**:\n{_plan}",
        "source": "rule",
        "themes": themes,
        "matched_therapies": matched,
        "patient": patient,
    }


def after_session_summary(patient: str, clinical_note: str) -> dict:
    name = _get_patient_name(patient)
    prompt = f"Patient: {name}. Session note: {clinical_note[:500]}. Write a 3-sentence patient-friendly summary of what was covered and next steps."
    ai = _query_ai("You are a patient communication AI. " + prompt)
    if ai:
        return {"suggestion": ai, "source": "ai"}
    return {"suggestion": f"In today's session, we discussed recent experiences and coping strategies. Try the techniques we practiced this week. See you at your next appointment.", "source": "rule"}


def pre_session_brief(patient: str) -> dict:
    journals = _get_journal_texts(patient)
    grades = _get_grades(patient)
    missed = _count_missed(patient)
    last_note = _get_latest_note(patient)
    name = _get_patient_name(patient)

    prompt = (
        f"Patient: {name}. Recent journals: {' | '.join(journals[-3:]) if journals else 'none'}. "
        f"Grades: {grades}. Missed: {missed}. Last note: {last_note[:200] if last_note else 'none'}. "
        "Generate a 3-line pre-session brief."
    )
    ai = _query_ai("You are a clinical briefing AI. " + prompt)
    if ai:
        return {"suggestion": ai, "source": "ai"}

    lines = []
    if journals:
        lines.append(f"Recent mood: {len(journals)} journal entries in the last 7 days.")
    if grades:
        lines.append(f"Follow-up grades: {', '.join(grades)}.")
    if missed:
        lines.append(f"⚠️ {missed} missed tasks.")
    if not lines:
        lines.append("No recent activity to report.")
    return {"suggestion": " | ".join(lines), "source": "rule"}


def mood_trend(patient: str) -> dict:
    journals = _get_journal_texts(patient)
    name = _get_patient_name(patient)
    if len(journals) < 2:
        return {"flag": False, "message": ""}

    negative_words = ["sad", "anxious", "tired", "hopeless", "lonely", "angry", "stressed", "overwhelmed", "depressed", "scared", "worried", "cry", "hurt", "pain", "empty"]
    positive_words = ["happy", "good", "better", "calm", "hopeful", "grateful", "peaceful", "excited", "energetic", "strong", "proud", "loved", "safe"]
    recent = journals[-3:]
    older = journals[:-3] if len(journals) > 3 else journals

    def sentiment_score(texts):
        score = 0
        for t in texts:
            t_lower = t.lower()
            score += sum(-1 for w in negative_words if w in t_lower)
            score += sum(1 for w in positive_words if w in t_lower)
        return score

    recent_score = sentiment_score(recent)
    older_score = sentiment_score(older) if older else 0
    if recent_score - older_score <= -3:
        return {"flag": True, "message": f"⚠️ {name} — Mood declining. Recent sentiment notably lower ({recent_score} vs {older_score} baseline).", "severity": "warning"}
    return {"flag": False, "message": f"✅ {name} — Mood stable."}


def compliance_radar(patient: str) -> dict:
    try:
        from data_manager_ import load_followups
        tasks = [t for t in load_followups() if t["patient"] == patient]
        pending = [t for t in tasks if t["status"] == "pending"]
        missed = [t for t in tasks if t["status"] == "not_yet"]
        completed = [t for t in tasks if t["status"] == "completed"]
        recent_grade_red = [t for t in tasks if t.get("grade") == "red"]
    except Exception:
        return {"flag": False, "message": "Could not load data.", "compliance": 0}

    total = len(pending) + len(missed) + len(completed)
    compliance = (len(completed) / total * 100) if total > 0 else 100
    name = _get_patient_name(patient)

    flags = []
    if missed:
        flags.append(f"{len(missed)} missed tasks")
    if recent_grade_red:
        flags.append(f"{len(recent_grade_red)} red-graded tasks")
    if compliance < 60:
        flags.append(f"compliance at {compliance:.0f}%")

    if flags:
        return {"flag": True, "message": f"⚠️ {name} — {'; '.join(flags)}.", "compliance": compliance}
    return {"flag": False, "message": f"✅ {name} — Compliance {compliance:.0f}%.", "compliance": compliance}


def silent_period_watch(patient: str, max_days: int = 7) -> dict:
    journals = _get_journal_texts(patient)
    bookings = _get_bookings(patient)
    name = _get_patient_name(patient)

    if not journals and not bookings:
        return {"flag": True, "message": f"⚠️ {name} — No activity recorded at all.", "days": 99}

    last_journal_date = None
    try:
        from data_manager_ import get_patient_history
        entries = get_patient_history(patient)
        if entries:
            last_journal_date = datetime.strptime(entries[-1]["timestamp"][:10], "%Y-%m-%d")
    except Exception:
        pass

    last_booking_date = None
    if bookings:
        try:
            dates = []
            for b in bookings:
                if b.get("date"):
                    dates.append(datetime.strptime(b["date"], "%Y-%m-%d"))
            if dates:
                last_booking_date = max(dates)
        except Exception:
            pass

    now = datetime.now()
    days = 0
    if last_journal_date:
        days = (now - last_journal_date).days
    elif last_booking_date:
        days = (now - last_booking_date).days

    if days >= max_days:
        return {"flag": True, "message": f"⚠️ {name} — No activity in {days} days.", "days": days}
    return {"flag": False, "message": "", "days": days}


def relapse_indicators(patient: str) -> dict:
    journals = _get_journal_texts(patient)
    grades = _get_grades(patient)
    name = _get_patient_name(patient)

    indicators = []
    trigger_words = ["can't sleep", "insomnia", "nightmare", "flashback", "panic", "avoid", "isolate", "withdrawn", "no energy", "can't eat", "self-harm", "suicidal", "hopeless", "worthless"]
    for t in journals:
        t_lower = t.lower()
        for w in trigger_words:
            if w in t_lower:
                indicators.append(w)

    red_count = grades.count("red")
    warning = ""
    if len(indicators) >= 3:
        warning = f"⚠️ {name} — {len(indicators)} early warning signs detected: {', '.join(set(indicators[:5]))}."
    elif red_count >= 2:
        warning = f"⚠️ {name} — {red_count} red-graded tasks."
    elif indicators:
        warning = f"ℹ️ {name} — {len(indicators)} minor indicators: {', '.join(set(indicators[:3]))}."

    return {"flag": bool(warning), "message": warning, "indicators": indicators, "red_count": red_count}


def cross_patient_patterns() -> dict:
    try:
        from patient_profiles_ import get_all_patients
        patients = get_all_patients()
    except Exception:
        return {"suggestion": ""}

    common_themes = {}
    for p in patients:
        journals = _get_journal_texts(p)
        theme_words = ["work", "school", "family", "relationship", "money", "health", "sleep", "lonely", "stress", "exam", "deadline", "loss", "grief", "trauma"]
        for t in journals:
            t_lower = t.lower()
            for w in theme_words:
                if w in t_lower:
                    common_themes[w] = common_themes.get(w, 0) + 1

    if not common_themes:
        return {"suggestion": "Not enough data yet to detect patterns."}

    threshold = max(2, len(patients) // 2)
    shared = {k: v for k, v in common_themes.items() if v >= threshold}
    if shared:
        top = sorted(shared.items(), key=lambda x: -x[1])[:3]
        msg = f"🔍 Cross-patient pattern: {len(patients)} patients, common themes — {', '.join(f'{k} ({v})' for k, v in top)}."
        return {"suggestion": msg}
    return {"suggestion": "No significant shared patterns this week."}


def patient_insights(patient: str) -> dict:
    journals = _get_journal_texts(patient)
    grades = _get_grades(patient)
    compliance = compliance_radar(patient)
    trend = mood_trend(patient)
    name = _get_patient_name(patient)
    missed = _count_missed(patient)

    week_count = _count_recent_journals(patient)
    green = grades.count("green")
    yellow = grades.count("yellow")
    red = grades.count("red")

    return {
        "name": name,
        "journal_count": week_count,
        "grades": {"green": green, "yellow": yellow, "red": red},
        "compliance": compliance.get("compliance", 100),
        "missed": missed,
        "mood_flag": trend.get("flag", False),
        "mood_message": trend.get("message", ""),
        "compliance_message": compliance.get("message", ""),
    }


def crisis_debrief() -> dict:
    try:
        from data_manager_ import get_crisis_state
        state = get_crisis_state()
    except Exception:
        return {"debrief": ""}

    if not state.get("active") or not state.get("acknowledged"):
        return {"debrief": ""}

    patient = state.get("patient", "")
    name = _get_patient_name(patient)
    triggered_at = state.get("triggered_at", "")
    ack_at = state.get("acknowledged_at", "")
    ack_by = state.get("acknowledged_by", "clinician")
    tc_acked = state.get("trustee_acknowledged", False)
    helpline = state.get("helpline_escalated", False)

    duration = ""
    if triggered_at and ack_at:
        try:
            d = int((datetime.fromisoformat(ack_at) - datetime.fromisoformat(triggered_at)).total_seconds())
            duration = f"{d}s"
        except Exception:
            pass

    return {
        "debrief": f"Crisis {triggered_at[:10]} — {name} ({duration}). Acknowledged by {ack_by}. TC {'responded' if tc_acked else 'notified'}. Helpline {'contacted' if helpline else 'not required'}.",
        "patient": patient,
        "duration": duration,
        "tc_responded": tc_acked,
        "helpline_contacted": helpline,
    }


def generate_crisis_rules(rules_config: dict = None) -> dict:
    if rules_config is None:
        rules_config = {}
    return {
        "tc_delay": rules_config.get("tc_delay", 30),
        "helpline_delay": rules_config.get("helpline_delay", 60),
        "high_risk_tc": rules_config.get("high_risk_tc", 15),
        "high_risk_helpline": rules_config.get("high_risk_helpline", 30),
        "night_mode": rules_config.get("night_mode", False),
        "night_start": rules_config.get("night_start", "22:00"),
        "night_end": rules_config.get("night_end", "06:00"),
    }


def ring_vitals_risk(ring: dict, baseline: dict = None) -> dict:
    if baseline is None:
        baseline = {"bpm": 72, "spo2": 97, "stress": 35}
    bpm = ring.get("bpm", baseline["bpm"])
    spo2 = ring.get("spo2", baseline["spo2"])
    stress = ring.get("stress", baseline["stress"])
    flags = []
    risk = "low"
    bpm_ratio = bpm / max(baseline["bpm"], 1)
    if bpm_ratio >= 1.35:
        flags.append("tachycardia")
    elif bpm_ratio >= 1.2:
        flags.append("elevated_hr")
    if spo2 < 92:
        flags.append("hypoxia")
    elif spo2 < 95:
        flags.append("low_oxygen")
    if stress > 75:
        flags.append("high_stress")
    elif stress > 60:
        flags.append("elevated_stress")
    if len(flags) >= 2:
        risk = "high"
    elif len(flags) >= 1:
        risk = "medium"
    return {"risk": risk, "flags": flags, "bpm_ratio": round(bpm_ratio, 2), "spo2": spo2, "stress": stress}


def after_session_note(note_text: str) -> str:
    if len(note_text) < 10:
        return ""
    prompt = f"Convert this into a structured clinical note with Observations, Assessment, Plan sections:\n{note_text[:800]}"
    ai = _query_ai("You are a clinical documentation AI. " + prompt)
    if ai:
        return ai
    return note_text
