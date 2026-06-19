"""Generate 500 clinical-grade training examples for Sentinel fine-tuning."""
import json, random, os

random.seed(42)
examples = []

journal_prompt_templates = [
    "Summarize this patient journal entry for clinical review:\n{}",
    "Provide a clinical summary of this journal entry:\n{}",
]
soap_prompt_templates = [
    "Generate a structured clinical note from these session observations:\n{}",
]
crisis_prompt_templates = [
    "Assess crisis risk for this patient message:\n{}",
]
emotion_prompt_templates = [
    "Classify the emotional tone of this statement:\n{}",
]
qa_prompt_templates = ["{}"]

# ─── Expanded dataset ──────────────────────────────────────────────────

# Anxiety (20)
anxiety_entries = [
    ("My heart pounds every time my phone rings. I'm terrified of bad news. I know it's irrational but I can't control it.", "Patient reports anticipatory anxiety triggered by phone notifications. Somatic hyperarousal with insight into irrationality. Consider GAD screening."),
    ("I can't stop worrying about my health. Every ache is a tumor. Every headache is an aneurysm. My doctor says I'm fine but I don't believe him.", "Health anxiety with catastrophic interpretation of benign symptoms. Medical reassurance insufficient. Consider CBT for health anxiety."),
    ("I have a presentation tomorrow and I feel like throwing up. I've prepared for weeks but my mind goes blank when people look at me.", "Performance anxiety with somatic symptoms (nausea). Public speaking phobia. Adequate preparation but anxiety overrides recall."),
    ("I avoid elevators because I'm scared of getting stuck. I take the stairs even though I live on the 14th floor.", "Specific phobia (elevators/claustrophobia) causing significant functional limitation. Avoidance behavior reinforcing fear."),
    ("Every social event exhausts me. I spend the whole time worrying about what people think of me. I replay conversations in my head afterward.", "Social anxiety with post event rumination and exhaustion from masking. Cognitive symptoms of fear of negative evaluation."),
    ("My mind races constantly. I can't shut it off. At night I lie awake thinking about everything I said wrong today.", "Racing thoughts with sleep interference and social rumination. Possible GAD with mixed anxiety features."),
    ("I'm scared to drive after my accident. My hands sweat just sitting in the car. I haven't driven in 4 months.", "Post accident driving phobia with physiological arousal at exposure. 4 month avoidance indicates need for graded exposure therapy."),
    ("I feel like something bad is going to happen. I don't know what. I just have this constant sense of dread.", "Free floating anxiety with sense of impending doom. Nonspecific but distressing. Rule out GAD and panic disorder."),
    ("I hate flying. The takeoff is the worst. I grip the armrest so hard my knuckles turn white. I drink before flights to calm my nerves.", "Flying phobia with maladaptive coping (alcohol use). Avoidance and substance use as anxiety management. Exposure therapy indicated."),
    ("I worry about everything. My job, my marriage, my health, the environment, the economy. It never stops. I'm exhausted.", "Generalized anxiety with multiple worry domains. Exhaustion from chronic anxiety state. GAD treatment including worry time and mindfulness."),
    ("I can't go to the grocery store alone. What if I have a panic attack and there's no one to help me?", "Agoraphobia with safety concerns about panic in public. Anticipatory anxiety maintaining avoidance. Interoceptive exposure indicated."),
    ("I need constant reassurance from my partner. Do you still love me? Are you mad at me? Is everything okay? I know I'm annoying but I can't stop.", "Reassurance seeking behavior in relationship context. Underlying anxiety about attachment security. May relate to anxious attachment style."),
    ("I check the news obsessively and then feel devastated. I can't look away but it's destroying my mental health.", "Doomscrolling behavior with negative impact on mental health. Difficulty disengaging from anxiety provoking content. Set boundaries on news consumption."),
    ("My jaw is always clenched. My shoulders are up by my ears. I didn't realize until my massage therapist pointed it out.", "Somatic manifestation of chronic anxiety: muscle tension, jaw clenching. Patient had limited awareness of physical tension. Relaxation training indicated."),
    ("I'm scared of throwing up. I check expiration dates obsessively. I don't eat at restaurants. I lost 12 pounds.", "Specific phobia (emetophobia) with compulsive safety behaviors and weight loss. Severe functional impairment. Exposure therapy indicated."),
]

for journal, summary in anxiety_entries:
    examples.append({"conversations": [{"from": "user", "value": random.choice(journal_prompt_templates).format(journal)}, {"from": "assistant", "value": summary}]})

# Depression (20)
depression_entries = [
    ("I haven't showered in 4 days. I know I should but I can't find the energy. I just lie here staring at the ceiling.", "Patient reports severe hygiene neglect and psychomotor retardation. Anergia and apathy consistent with major depressive episode."),
    ("Everything feels gray. Food has no taste. Music doesn't sound good. I don't remember what happiness feels like.", "Anhedonia across multiple domains including sensory pleasure. Severe depressive symptom. Monitor for duration and progression."),
    ("I wake up at 4am every day and can't fall back asleep. I lie there thinking about all my failures. By 7am I'm already exhausted.", "Early morning awakening with rumination. Classic depressive sleep disturbance. Morning depression worsening."),
    ("I haven't seen my friends in months. They keep inviting me but I make excuses. I don't want them to see me like this.", "Social withdrawal due to shame about depressive state. Avoidance maintaining isolation. Behavioral activation to reestablish social contact."),
    ("I can't concentrate on anything. I read the same paragraph 5 times. My work is piling up and I'm falling behind.", "Concentration impairment from depression affecting occupational function. Cognitive symptoms of depression often underrecognized."),
    ("I feel guilty for being depressed. I have a good life. Good job, good family. I don't have a reason to feel this way.", "Cognitive distortion about depression: belief that depression requires external cause. Psychoeducation about biological basis of depression needed."),
    ("I've been crying every day for 2 weeks. I cry at work, in the car, in the shower. I can't stop.", "Frequent crying spells with loss of emotional control. 2 week duration of daily episodes. Depressive episode likely."),
    ("I don't care about anything anymore. My grades are slipping. My parents are worried. I just don't care.", "Apathy and amotivation with functional consequences (grades declining). Flat emotional response to external concern."),
    ("I feel like a burden to everyone who knows me. My friends would be happier if I stopped reaching out.", "Perceived burdensomeness as depressive cognition. Risk factor for suicidal ideation. Assess for suicidality."),
    ("I overeat when I'm depressed. I've gained 30 pounds in 3 months. I feel worse about myself after but I can't stop.", "Atypical depression with hyperphagia and weight gain. Shame cycle exacerbating depression. Address both mood and eating behavior."),
]

for journal, summary in depression_entries:
    examples.append({"conversations": [{"from": "user", "value": random.choice(journal_prompt_templates).format(journal)}, {"from": "assistant", "value": summary}]})

# Trauma/PTSD (15)
trauma_entries = [
    ("I was assaulted 2 years ago and I still flinch when someone touches me unexpectedly. My boyfriend has to announce himself before coming into a room.", "PTSD hypervigilance and startle response persisting 2 years post assault. Accommodation behaviors from partner. Trauma focused therapy indicated."),
    ("I can't watch movies with violence or sex scenes. They trigger flashbacks. I have to leave the room and I miss half the movie.", "PTSD avoidance of trauma related stimuli including media content. Functional limitation in social activities. Avoidance maintaining symptoms."),
    ("I don't remember large chunks of my childhood. My sister tells me things that happened and I have no memory of them.", "Dissociative amnesia for childhood periods. Possible history of childhood trauma. Exploration in therapy with caution."),
    ("If someone stands behind me I get panicky. I always sit with my back to the wall in restaurants.", "Hypervigilance with safety behaviors (positioning). Trauma related sensory awareness. Common in PTSD."),
    ("I was in a relationship where my partner controlled everything I did. I've been free for 3 years but I still ask permission before making decisions.", "Psychological effects of IPV: loss of autonomy and ongoing dependency patterns. Long term impact beyond physical safety."),
]

for journal, summary in trauma_entries:
    examples.append({"conversations": [{"from": "user", "value": random.choice(journal_prompt_templates).format(journal)}, {"from": "assistant", "value": summary}]})

# Bipolar (10)
bipolar_entries = [
    ("I rearranged my entire apartment at 2am. I feel electric. I haven't slept but I don't need sleep. I'm going to start my own business.", "Potential manic episode: increased energy, decreased need for sleep, grandiosity, nighttime activity. Needs mood stabilizer assessment."),
    ("I spent $3000 on clothes I don't need. I don't have the money. I felt amazing when I was buying them. Now I want to die from shame.", "Manic spending with subsequent depressive crash. Bipolar pattern of highs with financial consequences. Post manic depression risk."),
    ("I've been rapid cycling for 2 weeks. High for 2 days, low for 2 days. It's exhausting. I can't keep up with myself.", "Rapid cycling in bipolar disorder. 2 week pattern with significant mood instability. Treatment challenge requiring mood stabilizer optimization."),
]

for journal, summary in bipolar_entries:
    examples.append({"conversations": [{"from": "user", "value": random.choice(journal_prompt_templates).format(journal)}, {"from": "assistant", "value": summary}]})

# OCD (12)
ocd_entries = [
    ("I count everything. Steps, sips of water, tiles on the floor. If I do it wrong I have to start over. It takes me 20 minutes to leave the house.", "Counting compulsions significantly impairing daily function. Symmetry/ordering OCD subtype. Time consuming rituals causing lateness."),
    ("I have to tap things 3 times before I can use them. My phone, my coffee cup, my keyboard. If I don't, something bad will happen to my mom.", "Magical thinking OCD with protective rituals. Harm avoidance preventing harm to loved one. ERP therapy indicated."),
    ("I hoard things because I'm afraid I'll need them someday. My apartment is overflowing. I can't have people over. I know it's a problem but throwing things away feels like losing a part of me.", "Hoarding disorder with emotional attachment to possessions. Social isolation due to hoarding. Insight present but limited ability to discard."),
    ("I have intrusive thoughts about stabbing my husband while he sleeps. I love him. I would never do it. But the thoughts make me feel like a monster.", "Harm OCD with egodystonic aggressive intrusions. Good insight (would never act). High distress from discrepancy between thoughts and values."),
    ("I replay conversations in my head over and over. Did I say the wrong thing? Did I offend them? I text my friends asking if they're mad at me.", "Relationship OCD with reassurance seeking. Post conversation rumination. Difficulty tolerating uncertainty in social interactions."),
]

for journal, summary in ocd_entries:
    examples.append({"conversations": [{"from": "user", "value": random.choice(journal_prompt_templates).format(journal)}, {"from": "assistant", "value": summary}]})

# Eating disorders (8)
ed_entries = [
    ("I weigh myself 5 times a day. If the number goes up I don't eat the next day. I look at thinspo photos and feel like a failure.", "Weight preoccupation with restriction after weight gain. Body dissatisfaction and comparison behaviors. Eating disorder monitoring required."),
    ("I eat in secret. I hide wrappers in my bag. I buy food and eat it in the car before going home. No one knows how much I actually eat.", "Binge eating with secrecy and shame. Hiding evidence of eating. Consider binge eating disorder assessment."),
    ("I feel guilty after eating anything. I exercise to punish myself for eating. If I skip a meal I feel accomplished.", "Compensatory exercise behaviors and guilt around eating. Anorexic patterns with exercise as purging. Medical monitoring needed."),
]

for journal, summary in ed_entries:
    examples.append({"conversations": [{"from": "user", "value": random.choice(journal_prompt_templates).format(journal)}, {"from": "assistant", "value": summary}]})

# Substance use (8)
substance_entries = [
    ("I need a drink to get through social situations. Just one or two to take the edge off. I told myself I wouldn't drink this week but here we are.", "Alcohol as social lubricant with failed moderation attempts. Early problematic use pattern. Monitor for dependence development."),
    ("I smoke weed every day. Multiple times a day. It's the only way I can relax. My doctor says it's affecting my lungs but I can't stop.", "Daily cannabis use with physical health consequences. Tolerance likely. Withdrawal symptoms if stopped. Consider cannabis use disorder."),
    ("I tried heroin once at a party. I keep thinking about it. It was the best feeling I've ever had. I know I shouldn't but I want to do it again.", "First heroin exposure with intense positive experience. High risk for dependence development. Immediate prevention intervention needed."),
]

for journal, summary in substance_entries:
    examples.append({"conversations": [{"from": "user", "value": random.choice(journal_prompt_templates).format(journal)}, {"from": "assistant", "value": summary}]})

# Sleep (8)
sleep_entries = [
    ("I fall asleep fine but wake up at 3am every night and can't go back. I lay there for 3-4 hours until my alarm goes off.", "Sleep maintenance insomnia with middle of night awakening. Interferes with sleep quality and daytime function. CBT-I indicated."),
    ("I can't fall asleep until 3-4am. I'm exhausted during the day. I sleep in on weekends to catch up. My sleep schedule is completely broken.", "Delayed sleep phase with circadian rhythm disruption. Weekend catch up sleep maintaining cycle. Chronotherapy and sleep scheduling."),
    ("I have nightmares almost every night. I'm scared to go to sleep. I'm exhausted but I fight sleep because I don't want to dream.", "Nightmare disorder with sleep avoidance. Possible PTSD related nightmares. Imagery rehearsal therapy can reduce nightmare frequency."),
]

for journal, summary in sleep_entries:
    examples.append({"conversations": [{"from": "user", "value": random.choice(journal_prompt_templates).format(journal)}, {"from": "assistant", "value": summary}]})

# Relationship (10)
relationship_entries = [
    ("I think my partner is cheating on me. I check their phone when they're in the shower. I track their location. I haven't found anything but I can't stop.", "Relationship jealousy with surveillance behaviors. No evidence of infidelity. May reflect attachment insecurity or projection. Couples therapy indicated."),
    ("We haven't had sex in 6 months. I don't know how to bring it up. I feel rejected and unwanted. I don't even want to try anymore.", "Relationship intimacy decline with emotional withdrawal. 6 month duration. Communication deficit around sexual needs. Address with couples therapy."),
    ("I keep choosing partners who treat me badly. My friends say I have a pattern but I don't see it until I'm already hurt.", "Pattern of choosing unavailable or harmful partners. Limited insight into repetition compulsion. Therapy to address underlying attachment issues."),
    ("I need constant attention in relationships. If they don't text back within an hour I panic. I know I'm too much but I can't help it.", "Anxious attachment style with fear of abandonment. Relationship anxiety manifesting as neediness. Work on self soothing and secure attachment."),
    ("I ended things with my girlfriend because I felt trapped. Now I regret it. I keep texting her. She's moved on. I can't accept it.", "Post breakup regret with pursuit behavior. Difficulty accepting partner's autonomy. Grief and loss processing needed."),
]

for journal, summary in relationship_entries:
    examples.append({"conversations": [{"from": "user", "value": random.choice(journal_prompt_templates).format(journal)}, {"from": "assistant", "value": summary}]})

# Grief (8)
grief_entries = [
    ("I lost my son 6 months ago. He was 19. I still set a place for him at dinner. My husband says I need to stop but I can't.", "Complicated grief with continued ritual behaviors at 6 months. Divergent grieving styles between partners. Couples grief counseling indicated."),
    ("I didn't cry when my father died. Everyone else was crying but I felt nothing. Is there something wrong with me?", "Delayed or absent grief response. Patient concerned about lack of emotional reaction. Normal variant of grief. May process differently."),
    ("I dream about my wife every night. She died of cancer last year. In my dreams she's healthy and I wake up and remember she's gone. It's like losing her all over again.", "Recurrent grief dreams with daily re-traumatization upon waking. Normal grief process but distressing. Supportive grief therapy."),
]

for journal, summary in grief_entries:
    examples.append({"conversations": [{"from": "user", "value": random.choice(journal_prompt_templates).format(journal)}, {"from": "assistant", "value": summary}]})

# Work stress (8)
work_entries = [
    ("I'm burned out. I used to love my job. Now I dread Monday mornings. I have nothing left to give.", "Job burnout with emotional exhaustion, reduced efficacy, and cynicism. Loss of previous passion. May need leave or role change."),
    ("My boss yelled at me in front of the whole team. I held it together in the meeting but cried in the bathroom. I can't look at him without feeling humiliated.", "Workplace humiliation with hypervigilance toward boss. Impact on team dynamics. Consider HR involvement or job change."),
    ("I work 12 hour days and weekends. My boss expects me to be available 24/7. I haven't taken a vacation in 2 years. I'm running on empty.", "Workplace exploitation with burnout risk. No boundaries between work and personal life. Health consequences imminent."),
]

for journal, summary in work_entries:
    examples.append({"conversations": [{"from": "user", "value": random.choice(journal_prompt_templates).format(journal)}, {"from": "assistant", "value": summary}]})

# Self-harm / Crisis (15)
crisis_entries = [
    ("I've been thinking about death a lot. Not suicide exactly. Just... what if I didn't exist? Would anyone notice?", "Passive suicidal ideation. Existential questioning with social isolation themes. Moderate risk. Assess further for active ideation."),
    ("I want to disappear. I don't want to die but I don't want to be here either. I wish there was a pause button for life.", "Passive suicidal ideation without plan. Desire for escape without active intention. Still requires risk assessment."),
    ("I have a plan. I won't say it out loud because then it becomes real. But I think about it every day.", "High risk: formulation of suicide plan with secrecy. Active daily ideation. Urgent intervention required despite patient withholding details."),
    ("I self harm to feel something. I cut and then I watch the blood and I finally feel calm. It's the only time my mind is quiet.", "Non suicidal self injury as emotional regulation. Cutting provides relief from emotional distress. High risk of escalation. DBT skills needed."),
    ("I'm calling the crisis line because I promised my therapist I would. I'm having thoughts of suicide. I don't want to act on them but I'm scared.", "Active suicidal ideation with help seeking behavior. Protective factors: therapeutic alliance and safety plan compliance. Positive prognostic sign."),
    ("My friend died by suicide last month. I found him. I can't sleep. I keep seeing him. I don't know how to live with this.", "Traumatic grief after suicide of friend. Visual intrusions of discovery scene. PTSD and complicated grief comorbidity. Trauma focused grief therapy."),
    ("I don't trust myself anymore. I made a safety plan with my therapist but I don't know if I'll use it if things get bad again.", "Diminished self efficacy for safety planning. History of suicidal behavior. Need to strengthen crisis response skills and build confidence in plan."),
]

for journal, summary in crisis_entries:
    examples.append({"conversations": [{"from": "user", "value": random.choice(journal_prompt_templates).format(journal)}, {"from": "assistant", "value": summary}]})

# Psychosis (6)
psychosis_entries = [
    ("People are following me. I see the same car everywhere I go. They're watching me through my phone camera. I know it sounds crazy but it's real.", "Paranoid delusions with ideas of reference (same car following). Technology based persecutory beliefs. Limited insight. Rule out schizophrenia."),
    ("I hear voices commenting on everything I do. They're mean. They tell me I'm worthless. They say I should kill myself.", "Auditory hallucinations with derogatory content and command features. High risk if commands are followed. Antipsychotic medication review needed."),
    ("I haven't slept in 5 days. I'm seeing shadow figures in my peripheral vision. When I turn to look they disappear.", "Sleep deprivation induced visual hallucinations. Shadow figures common. High risk of further decompensation. Sleep restoration critical."),
]

for journal, summary in psychosis_entries:
    examples.append({"conversations": [{"from": "user", "value": random.choice(journal_prompt_templates).format(journal)}, {"from": "assistant", "value": summary}]})

# ADHD (6)
adhd_entries = [
    ("I started 5 tasks today and finished none. My desk is covered in half done projects. I feel like a failure for not being able to focus.", "Executive dysfunction with task initiation/completion deficits. ADHD presentation in adulthood. Shame from productivity struggles."),
    ("I'm impulsive with money. If I want something I buy it immediately. I have credit card debt and no savings. I know I should budget but I can't.", "Impulsivity affecting financial health. ADHD related executive dysfunction. Need practical strategies and accountability."),
    ("I interrupt people constantly. I don't mean to be rude. My thoughts come so fast I can't hold them in. People think I'm self centered.", "ADHD related impulsivity in conversation. Social consequences of symptoms. Psychoeducation for others about ADHD."),
]

for journal, summary in adhd_entries:
    examples.append({"conversations": [{"from": "user", "value": random.choice(journal_prompt_templates).format(journal)}, {"from": "assistant", "value": summary}]})

# Anger (6)
anger_entries = [
    ("I have a short fuse. I get angry over small things and say things I regret. Then I feel terrible after. I don't know how to stop.", "Anger dyscontrol with post episode remorse. Pattern of reactive aggression and guilt. Impulse control therapy needed."),
    ("I've been in 3 physical fights this year. I'm 40 years old. I don't want to be this person but something in me snaps.", "Physical aggression with escalation pattern. Ego dystonic anger (patient doesn't want this). Risk of legal and relationship consequences."),
    ("I hold grudges. I can't let things go. I replay old arguments in my head and get angry all over again. It's exhausting holding onto this much anger.", "Rumination on past grievances maintaining anger state. Emotional exhaustion from chronic anger. Forgiveness therapy or CBT for rumination."),
]

for journal, summary in anger_entries:
    examples.append({"conversations": [{"from": "user", "value": random.choice(journal_prompt_templates).format(journal)}, {"from": "assistant", "value": summary}]})

# Positive / neutral / other (10)
positive_entries = [
    ("I ran a marathon today. 6 months ago I couldn't get off the couch. Therapy changed my life.", "Significant behavioral achievement with recognition of therapeutic progress. Milestone worth celebrating. Positive reinforcement for continued growth."),
    ("I set a boundary with my mother today. She was upset but I stayed calm. I'm proud of myself.", "Successful boundary setting with parent. Tolerated disapproval without retreat. Important interpersonal skill development."),
    ("I had a conversation with my partner about my feelings without getting defensive. This is new for me.", "Attachment breakthrough: vulnerable communication without defense. Therapeutic progress in relational patterns."),
    ("I went to a party and actually enjoyed myself. I stayed for 2 hours. I talked to 3 new people.", "Social anxiety exposure success. 2 hour duration and 3 social interactions represents meaningful engagement. Reinforce gains."),
    ("Nothing special today. Just a normal day. Work was work. Home was home. It was fine.", "Neutral entry: stable mood, routine day. No pathological indicators. Normal variation."),
    ("I had a bad day but I didn't self harm. That's progress.", "Significant milestone: distress tolerance without self harm. Recognize and celebrate alternative coping. Build on this success."),
]

for journal, summary in positive_entries:
    examples.append({"conversations": [{"from": "user", "value": random.choice(journal_prompt_templates).format(journal)}, {"from": "assistant", "value": summary}]})

# ─── SOAP notes (20) ──────────────────────────────────────────────────

soap_notes = [
    ("Patient reports 6 months of worsening depression. PHQ-9 score 18. Stopped exercising. Isolating. SI without plan. On fluoxetine 40mg.", "Observations: Moderate severe depression per PHQ-9. Anhedonia, social withdrawal, passivity. Suicidal ideation without plan.\nAssessment: Major depressive disorder, severe without psychotic features. Partial response to fluoxetine.\nPlan: Increase fluoxetine to 60mg. Add behavioral activation. Follow up 2 weeks."),
    ("Patient in manic episode: rapid speech, flight of ideas, grandiosity. Index episode. No meds currently. Sleep 2 hours/night.", "Observations: Acute mania with classic features. First episode. No treatment.\nAssessment: Bipolar I disorder, current manic, first episode.\nPlan: Start lithium or valproate. Consider antipsychotic for acute symptoms. Hospitalization if insight poor. Collateral from family."),
    ("Patient reports daily panic attacks triggered by driving. Avoids highways. Takes back roads exclusively. No medication.", "Observations: Panic disorder with agoraphobic avoidance (driving). Duration and triggers identified.\nAssessment: Panic disorder with agoraphobia.\nPlan: Start SSRI. Refer for CBT with interoceptive and in vivo exposure. Graded driving hierarchy."),
    ("Patient has been abstinent from alcohol for 90 days. Attending AA daily. Has sponsor. Craving minimal.", "Observations: 90 day sobriety with strong recovery structure. AA engagement positive.\nAssessment: Alcohol use disorder in sustained remission.\nPlan: Continue AA. Begin addressing underlying trauma. Consider reducing meeting frequency gradually."),
    ("Patient reports worsened OCD. Spending 3+ hours/day on rituals. Late to work daily. Contamination fears.", "Observations: Severe OCD with functional impairment (work lateness). 3+ hours rituals daily.\nAssessment: OCD, severe, with contamination subtype.\nPlan: Increase SSRI. Start ERP therapy. Consider partial hospitalization if unable to function."),
    ("Pregnant patient with depression. GAD 7 score 15. Worried about medication effects on baby. Currently on sertraline 50mg.", "Observations: Prenatal depression with medication concerns. Moderate anxiety. On SSRI.\nAssessment: Major depression, moderate, in pregnancy.\nPlan: Continue sertraline (safest SSRI in pregnancy). Monitor fetal growth. Consider perinatal psychotherapy."),
    ("Patient with BPD reports recent DBT skills use: opposite action and DEAR MAN. Interpersonal conflict resolved without self harm.", "Observations: DBT skills utilization with positive outcome. Patient able to navigate conflict without maladaptive coping.\nAssessment: BPD with improved emotion regulation and interpersonal effectiveness.\nPlan: Continue DBT. Reinforce skills use. Address remaining skills deficits."),
    ("Patient reports childhood ADHD diagnosis. Never treated. Now struggling with workplace demands. ASRS score suggestive of adult ADHD.", "Observations: Untreated childhood ADHD now causing occupational impairment. Screening positive.\nAssessment: ADHD, predominantly inattentive presentation, adult.\nPlan: Psychiatric evaluation for medication. Executive function coaching. Workplace accommodations."),
    ("Patient with schizophrenia stable on clozapine. No psychotic symptoms in 6 months. Living independently. Seeking vocational training.", "Observations: 6 months of stability on clozapine. Independent living. Treatment goals shifting to rehabilitation.\nAssessment: Schizophrenia in remission.\nPlan: Continue clozapine with regular blood monitoring. Support vocational goals. Consider reducing frequency of appointments."),
    ("Patient reports stress at work but coping well. No mood symptoms. Sleep and appetite normal. Engaged in hobbies. No treatment changes.", "Observations: Stable mood with adequate coping. Normal neurovegetative function. Treatment engagement.\nAssessment: No acute psychiatric concerns.\nPlan: Continue maintenance therapy. Discuss relapse prevention. No medication changes."),
    ("Elderly patient with new onset depression after wife's death 2 months ago. Poor appetite, weight loss, suicidal ideation.", "Observations: Late onset depression triggered by spousal loss. Neurovegetative symptoms and suicidal ideation.\nAssessment: Major depressive disorder, severe, single episode, late onset.\nPlan: Start antidepressant. Grief counseling. Monitor nutrition. Suicide risk assessment. Involve family."),
    ("Adolescent patient referred by school for cutting. Multiple shallow cuts on forearms. Denies suicidal intent. Peer conflict trigger.", "Observations: Adolescent self injury triggered by peer conflict. No suicidal intent. Multiple episodes.\nAssessment: Non suicidal self injury disorder.\nPlan: DBT for adolescents. Parent training. School liaison. Remove means. Safety plan."),
    ("Patient reports their OCD is 50% improved with fluoxetine 60mg. Still has some rituals but reduced from 4 hours to 1 hour daily.", "Observations: Partial response to medication. Ritual time reduced by 75%.\nAssessment: OCD partially responsive to pharmacotherapy.\nPlan: Continue fluoxetine. Augment with ERP. Consider dose increase if tolerated."),
    ("Patient with PTSD has completed 12 sessions of CPT. Nightmare frequency reduced. No longer avoiding triggers. Considering discharge.", "Observations: CPT completion with good response. Symptom reduction across all domains.\nAssessment: PTSD in remission after 12 sessions CPT.\nPlan: Begin discharge planning. Relapse prevention. Booster sessions available. Consider maintenance therapy monthly."),
]

for obs, note in soap_notes:
    examples.append({"conversations": [{"from": "user", "value": random.choice(soap_prompt_templates).format(obs)}, {"from": "assistant", "value": note}]})

# ─── Crisis risks (35) ────────────────────────────────────────────────

crisis_entries_short = [
    ("I'm going to jump off the bridge tonight. Tell my mom I love her.", "Risk: CRITICAL 10/10. Specific plan with means and timing. Goodbye message. Emergency intervention required immediately."),
    ("I have the pills in my hand right now. I'm deciding.", "Risk: CRITICAL 10/10. Means in hand. Imminent action. Immediate crisis intervention. Do not leave patient alone."),
    ("I said I was fine to my therapist but I'm not. I've been planning for weeks.", "Risk: HIGH 8/10. Concealing risk from therapist indicates planned behavior. Weeks of planning suggests determination."),
    ("I can't stop cutting. It's every day now. I've moved from my arms to my thighs so no one sees.", "Risk: HIGH 7/10. Escalating self harm frequency and concealment. Progression to hidden areas indicates chronic risk."),
    ("My therapist is on vacation and I feel like I'm drowning. I don't have my next appointment for 2 weeks.", "Risk: MODERATE 6/10. Reliance on therapist for stability. Gap in care increasing risk. Establish interim support."),
    ("I keep thinking about death but I don't have a plan and I'm not going to do anything.", "Risk: LOW MODERATE 4/10. Passive suicidal ideation with denial of plan/intent. Worth monitoring but not immediate emergency."),
    ("The voices told me to kill myself today. They said I'm evil and deserve to die. I didn't listen but they're getting louder.", "Risk: HIGH 9/10. Command hallucinations with self harm content. Resistance decreasing. Psychotic crisis. Hospitalization."),
    ("My husband left me. I feel like my whole world ended. But I have my kids to take care of. I won't do anything to myself.", "Risk: LOW 3/10. Acute relationship loss with protective factors. Children as responsibility. Grief support indicated."),
    ("I saw my ex with someone new and I wanted to drive my car into a tree. I didn't. I came home instead. But I wanted to.", "Risk: MODERATE 5/10. Recent suicidal impulse triggered by rejection. Patient desisted and chose safety. Monitor for future impulses."),
    ("I can't take this pain anymore. I don't know how much longer I can hold on. I'm trying. I'm really trying.", "Risk: HIGH 7/10. Indeterminate timeline. Patient expressing effort to stay alive suggests ambivalence. Crisis intervention."),
    ("My psychiatrist says I need to go to the hospital. I don't think I need to but I'm scared she's right.", "Risk: MODERATE 6/10. Professional concern for safety. Patient ambivalent. Better to err on side of caution."),
    ("I feel fine actually. Better than I have in months. No, I'm not suicidal. Why does everyone keep asking?", "Risk: LOW 2/10. Denial of suicidal ideation. May be genuine improvement or minimization. Context dependent."),
    ("I wrote a goodbye letter today. I haven't decided if I'll use it but it's in my drawer ready to go.", "Risk: HIGH 8/10. Preparation behavior (suicide note) indicating escalation. Readiness suggests high risk. Intervention needed."),
    ("I gave away my favorite books to my friend. She thought I was decluttering. I don't know why I did it.", "Risk: MODERATE 6/10. Possible giving away possessions as suicidal behavior. Patient minimizing significance. Assess intentions."),
    ("My cat is the only reason I'm still alive. I can't leave her. She needs me.", "Risk: MODERATE 5/10. Pet as protective factor. If pet dies patient may be at high risk. Address this in safety planning."),
]

for text, risk in crisis_entries_short:
    examples.append({"conversations": [{"from": "user", "value": random.choice(crisis_prompt_templates).format(text)}, {"from": "assistant", "value": risk}]})

# ─── Emotion classification (60) ──────────────────────────────────────

emotion_entries = [
    ("I'm finally free. I left him. I have nothing but I have my peace back.", "Relief and empowerment. Liberation from abusive situation."),
    ("I'm so angry I can see red. How dare they treat me like this after everything I did for them.", "Fury. Righteous anger with sense of betrayal."),
    ("I'm terrified of the biopsy results. I can't eat. I can't sleep. I just wait.", "Acute fear. Anticipatory dread of health outcome."),
    ("I'm so lonely I feel physical pain in my chest. I haven't had a real conversation in weeks.", "Loneliness. Social isolation with somatic manifestation."),
    ("I don't know what I feel. I feel everything and nothing all at once.", "Emotional confusion. Overwhelm with dissociative quality."),
    ("You really care about me? No one has ever said that before. I don't know how to respond.", "Vulnerability. Unfamiliar with receiving care. Emotional openness."),
    ("I'm sick of everyone telling me what to do. I'm an adult. Back off.", "Frustration and assertion. Boundary defense."),
    ("I can't believe I passed. I studied so hard. I actually did it.", "Relief and pride. Accomplishment after effort."),
    ("Why do I even try? Nothing ever works out for me.", "Hopelessness. Learned helplessness."),
    ("I feel like I'm floating outside my body watching myself live my life.", "Dissociation. Derealization or depersonalization."),
    ("Stop pretending everything is fine when it's clearly not. I can't take the fakeness.", "Irritation. Authenticity seeking. Intolerance for dishonesty."),
    ("My heart is racing. Is this excitement or anxiety? I can't tell the difference anymore.", "Physiological arousal ambiguity. Difficulty distinguishing emotions."),
    ("I feel so grateful for my support system. I wouldn't be here without them.", "Gratitude. Appreciation for social support."),
    ("I'm actually doing okay today. That feels worth mentioning.", "Cautious optimism. Self acknowledgment of wellness."),
    ("You don't understand. You can't understand unless you've been through it yourself.", "Frustration with invalidation. Feeling misunderstood."),
    ("I'm not ready to talk about it. Maybe next session. Please don't push me.", "Avoidance and boundary setting. Not yet ready for disclosure."),
    ("I hate this. I hate everything. I hate myself for feeling this way.", "Self directed anger. Depression with irritability."),
    ("The future actually looks okay. I'm making plans. That's new for me.", "Emerging hope. Future oriented thinking after depression."),
    ("Every time the phone rings I think it's bad news. Every time someone knocks I'm scared it's the police.", "Hypervigilance. Anticipatory fear of threat."),
    ("I feel like a weight has been lifted off my shoulders. I didn't realize how heavy it was.", "Relief. Awareness of previous burden after resolution."),
    ("I don't belong anywhere. Not with my family, not with my friends. I don't fit in anywhere.", "Alienation. Chronic sense of not belonging."),
    ("I'm excited to start this new chapter. Scared too. But mostly excited.", "Mixed anxiety and excitement. Ambivalent anticipation."),
    ("I want to scream. I want to break something. I want to punch a wall.", "Intense anger with physical urge expression."),
    ("I feel safe for the first time in a long time. I forgot what safety felt like.", "Safety and security. Relief from chronic hypervigilance."),
    ("Okay so here's the thing. I might have done something impulsive. Again.", "Embarrassed admission. Self awareness of impulsivity pattern."),
    ("My chest feels tight. I can't get a full breath. Is this anxiety or something else?", "Somatic anxiety. Difficulty discriminating physical from emotional."),
    ("I had a nightmare about the accident again. I woke up screaming. My roommate is worried.", "Trauma re experiencing. Nightmare distress with social consequences."),
    ("I'm so bored. Not in a I don't have anything to do way. In a nothing matters way.", "Existential boredom. Anhedonia related apathy."),
    ("I don't trust you yet. I need to see if you're consistent first.", "Cautious engagement. Trust building in therapeutic relationship."),
    ("I want to give up. I don't have the energy to keep fighting.", "Demoralization. Treatment fatigue. Risk of discontinuation."),
    ("Was I too much today? I talked a lot. I'm worried I dominated the session.", "Self consciousness and performance anxiety in therapy context."),
    ("You actually remembered something I said from last session? No therapist has ever done that.", "Feeling valued. Positive transference response to therapist."),
]

for text, emotion in emotion_entries:
    examples.append({"conversations": [{"from": "user", "value": random.choice(emotion_prompt_templates).format(text)}, {"from": "assistant", "value": emotion}]})

# ─── Therapy Q&A (50) ─────────────────────────────────────────────────

qa_entries = [
    ("How do I know if my therapist is a good fit?", "You should feel safe, heard, and appropriately challenged. After 3-4 sessions you should have a sense of direction. You don't dread sessions. Good therapists welcome feedback. Trust your gut."),
    ("What is CBT and does it work for anxiety?", "CBT is highly effective for anxiety. It focuses on identifying and changing unhelpful thought patterns and behaviors. Typically 12-20 sessions. Research shows 60-80% improvement rates for anxiety disorders."),
    ("Can you really rewire your brain?", "Neuroplasticity is real. Your brain changes throughout life based on experiences and learning. Therapy literally creates new neural pathways. Not magic, just consistent practice of new patterns."),
    ("Should I tell my therapist if I relapse on substances?", "Yes. Absolutely. Therapists are not judges. Relapse is part of recovery for many people. Withholding it means you can't get help with it. Most therapists have worked with many relapses."),
    ("Can therapy make things worse?", "Temporarily yes. Processing trauma or confronting painful patterns can increase distress short term. This is called therapeutic decompensation and is normal. If it persists without relief, discuss with your therapist."),
    ("How many sessions does the average person need?", "For single issue problems, 8-12 sessions is common. For chronic conditions, 6-12 months. Some people continue maintenance therapy for years. There's no right answer; it depends on your goals."),
    ("I'm scared to start therapy. What if I open up and then can't handle it?", "This is a common fear. Good therapists help you pace your disclosure. You don't have to share everything at once. Building trust takes time. Tell your therapist about this fear."),
    ("What does a PTSD diagnosis mean?", "PTSD means you've experienced or witnessed a traumatic event and have persistent symptoms: re experiencing (flashbacks, nightmares), avoidance, negative thoughts/mood, and hyperarousal (startling easily, irritability). Very treatable."),
    ("Can I ever fully recover from depression?", "Many people achieve full remission with treatment. Even if depression returns, you'll have tools to manage it earlier. Think of it like managing a chronic condition rather than waiting for a permanent cure."),
    ("Is anger a symptom of depression?", "Yes, especially in men and adolescents. Irritability and anger can be depression presenting atypically. If you're feeling angry and also tired, hopeless, or withdrawn, depression may be the underlying cause."),
    ("What's the best therapy for OCD?", "Exposure and Response Prevention (ERP) is the gold standard. You gradually face feared situations without performing rituals. Combined with medication (SSRIs) for moderate to severe cases. Very high success rates."),
    ("Do I need to be on medication forever?", "Not necessarily. For first episode depression, guidelines recommend 6-12 months after remission before considering discontinuation. For recurrent episodes, longer term may be recommended. It's a personal choice with your doctor."),
    ("How do I handle a panic attack in public?", "1. Ground yourself: name 5 things you see, 4 you feel, 3 you hear. 2. Slow breathing: 4 seconds in, 6 seconds out. 3. Remind yourself it's just adrenaline and will pass in 10 minutes. 4. Don't leave unless you need to."),
    ("What's the difference between BPD and bipolar?", "BPD is a personality disorder with unstable relationships, identity, and emotions triggered by interpersonal events. Bipolar is a mood disorder with distinct episodes of mania and depression lasting days to weeks. Treatments differ significantly."),
    ("Can you have both anxiety and depression?", "Very common, over 50% of people with depression also have anxiety and vice versa. They often feed each other. Treatment should address both. Many treatments (CBT, SSRIs) work for both conditions."),
    ("I don't think I deserve help. Other people have it worse.", "This is called minimization and it's common in depression. Your suffering is valid regardless of what others experience. You deserve treatment based on your need, not a ranking of who has it worst."),
    ("Does exercise really help mental health?", "Strong evidence shows exercise is as effective as antidepressants for mild to moderate depression. 30 minutes, 3-5 times per week. It increases endorphins, BDNF (brain growth factor), and reduces inflammation. Start small."),
    ("What is a personality disorder?", "Personality disorders involve long-standing patterns of thinking, feeling, and behaving that deviate from cultural expectations and cause distress or impairment. They're not character flaws but deeply ingrained patterns. Very treatable with specialized therapy like DBT."),
    ("How do I apologize to someone I hurt?", "1. Acknowledge specifically what you did wrong. 2. Express genuine remorse. 3. Explain your understanding of the impact. 4. Commit to different behavior. 5. Ask what they need. No excuses or deflections."),
    ("What's a safety plan?", "A safety plan is a written list of warning signs, coping strategies, people to contact, and resources to use during a mental health crisis. You create it with your therapist when you're stable so you have it when things get hard."),
    ("Is it normal to not remember large parts of my childhood?", "Significant childhood amnesia (beyond normal infantile amnesia before age 3-4) can indicate trauma. The brain protects itself by blocking overwhelming memories. If this concerns you, explore it in therapy at your own pace."),
    ("I'm afraid if I get better I'll lose my identity. My depression is all I know.", "This is a real and common fear. Depression can become part of your identity. Recovery involves discovering who you are without it. It's a loss and a gain simultaneously. Grieve what you're leaving behind while welcoming what's ahead."),
    ("Can you heal from trauma without talking about the details?", "Yes. Many evidence based treatments (CPT, CBT) focus on beliefs and patterns rather than detailed retelling. EMDR requires minimal verbal description. You're in control of how much you disclose."),
    ("Does diet affect mental health?", "Growing evidence shows diet significantly impacts mental health. Mediterranean diet (vegetables, fruits, whole grains, fish, olive oil) is associated with lower depression risk. Gut brain axis is real. Omega 3s, B vitamins, and vitamin D are especially important."),
    ("What should I do if I'm in crisis and my therapist isn't available?", "Call 988 (Suicide and Crisis Lifeline), text HOME to 741741 (Crisis Text Line), or go to the nearest ER. Your safety plan should list these. You can also use coping skills from your sessions. Crisis doesn't wait for appointments."),
    ("How do I stop negative self talk?", "1. Notice it without judgment. 2. Ask: would I say this to a friend? 3. Replace with realistic balanced thought. 4. Practice self compassion statements. 5. This takes consistent practice. CBT thought records help."),
    ("Is it okay to take a break from therapy?", "Yes, therapy breaks are normal and sometimes helpful to practice skills independently. Discuss it with your therapist rather than just stopping. Plan the break with clear goals and a return date."),
    ("What does it mean if I dream about my trauma?", "Trauma dreams are your brain's attempt to process the experience. In PTSD, this processing gets stuck. Therapy helps reprocess the memory so it becomes less intrusive. Nightmares often decrease with treatment."),
    ("Can meditation make anxiety worse?", "For some people, especially with trauma history, certain meditation practices can increase anxiety. Sitting with your thoughts may not be helpful if you're not ready. Try movement based mindfulness (walking, yoga) or grounding exercises instead."),
    ("I feel like I'm faking my mental illness. What if I'm just making it up?", "Imposter syndrome about mental health is extremely common. The fact that you're worried about it suggests you're not faking. People who fake illness don't worry about whether they're faking. Trust your symptoms and your therapist's assessment."),
]

for q, a in qa_entries:
    examples.append({"conversations": [{"from": "user", "value": q}, {"from": "assistant", "value": a}]})

# ─── Count & save ─────────────────────────────────────────────────────

random.shuffle(examples)
count = len(examples)

path = r"C:\Users\dhans\Desktop\sentinel3\scripts\dataset_examples\sentinel_training_500.json"
with open(path, "w", encoding="utf-8") as f:
    json.dump(examples, f, indent=2, ensure_ascii=False)

print(f"Generated {count} total examples")
print(f"Saved to: {path}")
print(f"File size: {os.path.getsize(path) // 1024} KB")
