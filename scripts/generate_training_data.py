"""Generate high-quality synthetic clinical examples for Sentinel fine-tuning.
Augments our 572 real examples with targeted clinical scenarios."""
import json, os, random

os.makedirs(os.path.join(os.path.dirname(__file__), "dataset_examples"), exist_ok=True)

random.seed(42)

def esc(s):
    return s.replace('"', "'")

def journal_summaries():
    return [
        ("Had a panic attack at the grocery store. Heart was pounding, couldn't breathe, thought I was dying. Left my cart and ran out. Haven't been able to go back since.",
         "Patient reports acute panic episode in public setting with somatic symptoms (palpitations, dyspnea) and avoidance behavior. Suggests possible agoraphobia development. No crisis indicators. Monitor for panic disorder patterns."),
        ("My therapist says I should write down what I'm feeling. Honestly I feel numb. Not sad, not angry, just... nothing. Is that worse?",
         "Patient describes emotional numbing and anhedonia. Flat affect with possible depressive features. Lacks acute risk but emotional blunting warrants monitoring for underlying depression."),
        ("I drank again after 3 months sober. I hate myself for it. The shame is overwhelming. I don't know if I can do this.",
         "Patient reports relapse after 3 months sobriety with intense shame and self-criticism. High risk of shame-spiral leading to further substance use. Encourage self-compassion and relapse prevention planning."),
        ("My son told me he's depressed. I don't know what to do. I feel like I failed as a parent. I'm trying to be supportive but I'm scared.",
         "Patient (parent) processing child's mental health disclosure. Expresses guilt, fear, and uncertainty. No direct crisis indicators. May benefit from psychoeducation on supporting a child with depression."),
        ("Can't sleep. It's 4am and I have to be at work at 8. This is the 4th night this week. I'm so exhausted I feel dizzy during the day.",
         "Patient reports severe sleep disturbance with daytime functional impairment. Chronic insufficient sleep (4 nights/week). Risk of accidents due to daytime dizziness. Screen for sleep disorders."),
        ("I'm so angry all the time. Little things set me off. Yesterday I yelled at a cashier for no reason. I don't recognize myself anymore.",
         "Patient reports increased irritability and anger dyscontrol with impact on daily functioning. Possible underlying mood disturbance. No crisis indicators. Assess for depressive or anxiety disorder with irritable features."),
        ("Just got diagnosed with bipolar II. I don't know what this means for my future. Will I ever be normal? Can I still have a career? A family?",
         "Patient processing recent bipolar II diagnosis with existential concerns about prognosis and life goals. No acute episode indicated. Provide psychoeducation and connect with peer support resources."),
        ("I keep checking my body for lumps. I know it's irrational but I can't stop. I've been to the doctor 3 times this month. They say I'm fine but I don't believe them.",
         "Patient exhibits health anxiety with compulsive checking behaviors and reassurance-seeking. Medical reassurance insufficient. Consider CBT for health anxiety. No crisis indicators."),
        ("My husband doesn't understand my eating disorder. He says 'just eat' like it's that simple. I feel so alone in this fight.",
         "Patient reports eating disorder with limited partner understanding and associated isolation. No acute medical crisis indicated. Couples therapy or psychoeducation for partner recommended."),
        ("Work has been unbearable. My boss micromanages everything I do. I cry in the bathroom at least twice a day. I'm updating my resume but I'm scared to leave.",
         "Patient describes workplace distress with daily crying, micromanagement stress, and ambivalence about job change. No crisis indicators. Support coping strategies and career transition planning."),
        ("I saw my ex on social media with someone new. It's been 8 months since the breakup. Why does it still hurt this much? I thought I was over it.",
         "Patient processing delayed grief response to relationship dissolution triggered by social media exposure. Normal but protracted adjustment reaction. Encourage limit-setting on social media triggers."),
        ("My meds are making me gain weight and I can't stand looking at myself. I stopped taking them 3 days ago. I know I shouldn't have but the scale was killing me.",
         "Patient self-discontinued psychiatric medication due to weight gain side effect. High risk of symptom relapse. Address medication concerns with prescriber. Do not restart without consultation."),
        ("I had a good day today. I don't have much else to say. I just wanted someone to know that I had a good day.",
         "Patient reports a positive day — an important milestone worth acknowledging. Positive affect noted. Continue monitoring for mood stability."),
        ("The intrusive thoughts are back. Telling me to hurt myself. I know they're not real but they're so loud. I'm scared I'll listen to them one day.",
         "CRISIS ALERT: Patient reports active intrusive thoughts with self-harm content. Distress level high. Limited insight into thought-action gap. Immediate safety assessment required. Consider crisis intervention."),
        ("I've been self-harming again. Just cuts on my thighs where no one can see. I feel so ashamed. I promised my therapist I would stop.",
         "CRISIS ALERT: Patient reports recurrence of self-harm behavior after period of abstinence. Shame may prevent disclosure to therapist. Safety plan reactivation required. Assess for escalation risk."),
    ]

def soap_notes():
    return [
        ("Patient arrived late, visibly distressed. Reported that partner threatened to leave. Cried throughout session. Said 'I have nothing left.'",
         "Observations: Patient presented in acute emotional distress with psychomotor agitation and tearfulness. Reported relationship crisis with threat of abandonment. Expressed hopelessness.\nAssessment: Acute situational distress with risk of depressive escalation. Screen for suicidal ideation.\nPlan: Safety planning. Schedule follow-up within 48 hours. Consider involving partner for conjoint session."),
        ("Patient reported significant improvement. Has been exercising regularly, sleeping better, and socializing more. Said 'I feel like myself again for the first time in months.'",
         "Observations: Patient reports marked improvement across multiple domains (sleep, exercise, social engagement). Positive self-appraisal. Good treatment response.\nAssessment: Depressive symptoms in remission. Good insight and treatment adherence.\nPlan: Begin discussing relapse prevention plan. Taper session frequency to biweekly. Reinforce healthy routines."),
        ("Patient disclosed childhood sexual abuse for the first time. Shaking and tearful. Said they've never told anyone before. Asked if we could stop talking about it.",
         "Observations: Patient disclosed childhood trauma (sexual abuse) with significant emotional distress and some dissociative features. Requested to pause discussion indicating current coping limits.\nAssessment: Trauma disclosure with appropriate emotional response. Patient paced disclosure appropriately.\nPlan: Validate courage in disclosure. Do not push detailed exploration. Stabilize affect before session ends. Consider trauma-focused therapy readiness assessment."),
        ("Patient has been paranoid about coworkers. Thinks they're plotting against him. Has been recording conversations on his phone. No evidence of actual conspiracy.",
         "Observations: Patient exhibits paranoid ideation with delusional quality regarding coworkers. Acting on beliefs (recording conversations). No insight into unreality of beliefs.\nAssessment: Possible psychotic features. Rule out paranoid personality disorder vs. psychotic disorder.\nPlan: Psychiatric referral for medication evaluation. Avoid colluding with or directly challenging delusions. Focus on associated distress."),
        ("Patient reported that EMDR has been helping with the car accident flashbacks. Still has nightmares but less frequent. Able to drive on highways now without panic.",
         "Observations: Patient reports partial response to EMDR therapy for PTSD (motor vehicle accident). Nightmare frequency reduced. Functional improvement (highway driving resumed).\nAssessment: PTSD symptoms improving with targeted treatment. Good treatment response.\nPlan: Continue EMDR protocol. Begin generalization work. Address any residual avoidance behaviors."),
    ]

def crisis_risk():
    return [
        ("I've been thinking about death a lot lately. Not like I want to die, just... what if I wasn't here anymore? I don't have a plan or anything. It's just on my mind.",
         {"risk_score": 5, "reasoning": "Passive death ideation without plan or intent. No active suicidal ideation. Worth monitoring for escalation. Not immediate crisis but warrants exploration.", "triggered": False}),
        ("I bought a rope today. I told myself it's for a project but I know what it's really for. I don't know when. But I feel like I'm getting closer.",
         {"risk_score": 9, "reasoning": "Active suicidal ideation with means acquisition (rope). Implicit plan forming. High risk. Requires immediate crisis intervention and safety planning.", "triggered": True}),
        ("I'm just really sad. I've been crying every day for two weeks. But I'm not going to hurt myself. I would never do that to my kids.",
         {"risk_score": 4, "reasoning": "Moderate depressive symptoms with daily crying. Protective factors present (children, explicit denial of self-harm intent). No active ideation.", "triggered": False}),
        ("I took 20 pills last night. I don't know why I'm still alive. I woke up this morning and felt disappointed.",
         {"risk_score": 10, "reasoning": "Recent suicide attempt (overdose). Waking up disappointed indicates continued desire to die. IMMEDIATE EMERGENCY. Hospitalization required.", "triggered": True}),
        ("My therapist is worried about me. She made me sign a safety contract. I don't think I need it but I signed it to make her happy.",
         {"risk_score": 6, "reasoning": "External risk indicators (therapist concern, safety contract). Patient lacks insight into severity. Collateral information would be valuable. Elevated risk.", "triggered": False}),
    ]

def emotion_classify():
    return [
        ("I got promoted today! All that hard work finally paid off!", "joy"),
        ("My cat died. She was with me for 17 years. I don't know how to be in this house without her.", "sadness"),
        ("I can't believe they would do this to me after everything I've done for them.", "anger"),
        ("There's a lump on my neck. I'm terrified it's cancer. I can't stop thinking about it.", "fear"),
        ("You proposed?! Oh my god, I had no idea! This is incredible!", "surprise"),
        ("I don't feel anything anymore. Not happiness, not sadness. Just empty.", "sadness"),
        ("Every time my phone buzzes I jump. I'm constantly waiting for the next bad news.", "anxiety"),
        ("I'm so proud of myself. I did something today that scared me and I did it anyway.", "joy"),
        ("I hate her. I hate what she did to our family. I will never forgive her.", "anger"),
        ("I don't know why I'm crying. Nothing bad happened. I just can't stop.", "sadness"),
        ("The future feels possible for the first time in years. Like there's actually hope.", "joy"),
        ("If one more thing goes wrong today I'm going to lose my mind.", "anger"),
        ("My hands are shaking. I feel like something terrible is about to happen.", "fear"),
        ("I miss you. I know I shouldn't say that. But I really, really miss you.", "sadness"),
        ("I can't breathe. I feel like the walls are closing in. Someone help me.", "fear"),
    ]

def generate_sharegpt():
    examples = []
    
    # Journal summaries
    for journal, summary in journal_summaries():
        examples.append({
            "conversations": [
                {"from": "user", "value": f"Summarize this patient journal entry for clinical review:\n{journal}"},
                {"from": "assistant", "value": summary}
            ]
        })
    
    # SOAP notes
    for obs, note in soap_notes():
        examples.append({
            "conversations": [
                {"from": "user", "value": f"Generate a structured clinical note from these session observations:\n{obs}"},
                {"from": "assistant", "value": note}
            ]
        })
    
    # Crisis risk
    for text, risk in crisis_risk():
        examples.append({
            "conversations": [
                {"from": "user", "value": f"Assess crisis risk level for this patient message:\n{text}"},
                {"from": "assistant", "value": json.dumps(risk)}
            ]
        })
    
    # Emotion classification
    for text, emotion in emotion_classify():
        examples.append({
            "conversations": [
                {"from": "user", "value": f"Classify the emotional tone of this statement:\n{text}"},
                {"from": "assistant", "value": f"The emotional tone is {emotion}."}
            ]
        })
    
    return examples

# Also load and convert existing real data
def convert_existing():
    examples = []
    cache = os.path.join(os.path.dirname(__file__), "dataset_examples")
    
    existing = {
        "mental_health_chatbot_dataset.json": ("text", "response"),
        "counsel-chat.json": ("questionText", "answerText"),
    }
    
    for fname, (qkey, akey) in existing.items():
        fpath = os.path.join(cache, fname)
        if os.path.exists(fpath):
            with open(fpath, encoding="utf-8") as f:
                data = json.load(f)
            for item in data:
                q = item.get(qkey, "")
                a = item.get(akey, "")
                if q and a and len(q) < 500 and len(a) < 500:
                    q_clean = q.replace("<HUMAN>:", "").replace("<ASSISTANT>:", "").strip()
                    examples.append({
                        "conversations": [
                            {"from": "user", "value": q_clean[:500]},
                            {"from": "assistant", "value": a[:500]}
                        ]
                    })
    return examples

if __name__ == "__main__":
    synthetic = generate_sharegpt()
    real = convert_existing()
    combined = synthetic + real
    random.shuffle(combined)
    
    out_path = os.path.join(os.path.dirname(__file__), "dataset_examples", "sentinel_training.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)
    
    print(f"Generated {len(combined)} total training examples:")
    print(f"  Synthetic: {len(synthetic)}")
    print(f"  Real: {len(real)}")
    print(f"Saved to: {out_path}")
    print(f"Size: {os.path.getsize(out_path) // 1024} KB")
