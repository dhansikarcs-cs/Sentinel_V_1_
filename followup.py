import streamlit as st
import os
from data_manager import load_followups, save_followup, update_followup_status, update_followup_grade

DATA_DIR = "data"
FOLLOWUP_FILES = os.path.join(DATA_DIR, "followup_files")
PROOF_FILES = os.path.join(DATA_DIR, "followup_proofs")
os.makedirs(FOLLOWUP_FILES, exist_ok=True)
os.makedirs(PROOF_FILES, exist_ok=True)


def _save_uploaded(uploaded, folder, prefix, suffix=""):
    ext = os.path.splitext(uploaded.name)[1]
    fname = f"{prefix}{suffix}{ext}"
    dest = os.path.join(folder, fname)
    with open(dest, "wb") as f:
        f.write(uploaded.getbuffer())
    return dest


def _feedback_download_data(feedback_text, grade_label):
    content = f"Psychologist's Feedback\n{'='*40}\n\nGrade: {grade_label}\nFeedback: {feedback_text}\n"
    return content.encode("utf-8")


def render_psychologist_followup(psychologist_username: str):
    st.markdown("### 📋 Follow-Up Tasks")
    patients = [p for p in ["alice", "bob", "charlie"]]

    with st.expander("➕ Assign New Task", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            sel_patient = st.selectbox("Patient", patients, key="fu_psych_patient")
            fu_title = st.text_input("Task title", placeholder="e.g. Breathing exercise")
        with col2:
            fu_desc = st.text_area("Description", placeholder="What should the patient do?", height=100)
            uploaded = st.file_uploader("Attach video/doc/pdf", type=["pdf", "mp4", "mov", "png", "jpg", "mp3"],
                                        key="fu_psych_upload")

        if st.button("Assign Task", type="primary", use_container_width=True, key="fu_psych_assign"):
            file_path = ""
            if uploaded:
                file_path = _save_uploaded(uploaded, FOLLOWUP_FILES, f"{sel_patient}_{fu_title[:20]}")
            save_followup(sel_patient, psychologist_username, fu_title or "Untitled", fu_desc, file_path)
            st.success("Task assigned!")
            st.rerun()

    tasks = load_followups()
    my_tasks = [t for t in tasks if t["psychologist"] == psychologist_username]
    if not my_tasks:
        st.caption("No tasks assigned yet.")
        return

    st.markdown("#### Assigned Tasks")
    for t in reversed(my_tasks):
        status_icon = {"pending": "⏳", "completed": "✅", "not_yet": "❌"}.get(t["status"], "⏳")
        grade_icon = {"green": "🟢", "yellow": "🟡", "red": "🔴"}.get(t.get("grade", "none"), "")
        label = f"{status_icon} {t['title']} → {t['patient']}"
        if grade_icon:
            label = f"{grade_icon} {label}"
        with st.expander(label):
            st.markdown(f"**Patient:** {t['patient']}")
            st.markdown(f"**Description:** {t['description']}")
            if t["file_path"] and os.path.exists(t["file_path"]):
                with open(t["file_path"], "rb") as f:
                    st.download_button("⬇ Download Attachment", f.read(),
                                       file_name=os.path.basename(t["file_path"]),
                                       key=f"fu_dl_{t['id']}")
            st.caption(f"Status: **{t['status'].replace('_', ' ').title()}**")

            if t["proof_file"] and os.path.exists(t["proof_file"]):
                with open(t["proof_file"], "rb") as f:
                    st.download_button("📎 View Proof", f.read(),
                                       file_name=os.path.basename(t["proof_file"]),
                                       key=f"fu_proof_{t['id']}")

            # Grading section — only when patient submitted with proof
            if t["status"] == "completed" and t["proof_file"]:
                st.markdown("---")
                st.markdown("#### Grade & Feedback")
                current_grade = t.get("grade", "none")
                gcols = st.columns(3)
                with gcols[0]:
                    if st.button("🟢 Correct", type="primary" if current_grade == "green" else "secondary",
                                 key=f"fu_green_{t['id']}", use_container_width=True):
                        update_followup_grade(t["id"], "green")
                        st.rerun()
                with gcols[1]:
                    if st.button("🟡 Partial", type="primary" if current_grade == "yellow" else "secondary",
                                 key=f"fu_yellow_{t['id']}", use_container_width=True):
                        update_followup_grade(t["id"], "yellow")
                        st.rerun()
                with gcols[2]:
                    if st.button("🔴 Wrong", type="primary" if current_grade == "red" else "secondary",
                                 key=f"fu_red_{t['id']}", use_container_width=True):
                        update_followup_grade(t["id"], "red")
                        st.rerun()

                current_feedback = t.get("feedback", "")
                fb = st.text_area("Feedback for patient", value=current_feedback,
                                  key=f"fu_fb_{t['id']}", placeholder="Write feedback here...",
                                  height=80)
                if fb != current_feedback:
                    update_followup_grade(t["id"], t.get("grade", "none"), fb)
                    st.rerun()

                if current_grade != "none":
                    grade_labels = {"green": "🟢 Correctly done", "yellow": "🟡 Partially done", "red": "🔴 Needs improvement"}
                    st.caption(f"Current grade: **{grade_labels.get(current_grade, 'Not graded')}**")
                else:
                    grade_labels = {"green": "🟢 Correctly done", "yellow": "🟡 Partially done", "red": "🔴 Needs improvement"}

                fb_data = _feedback_download_data(current_feedback,
                                                   grade_labels.get(current_grade, "Not graded"))
                st.download_button("⬇ Download Feedback", fb_data,
                                   file_name=f"feedback_{t['id']}.txt",
                                   key=f"fu_fb_dl_{t['id']}")

            st.caption(f"Assigned: {t['created_at'][:10]}")


def render_patient_followup(patient_username: str):
    st.markdown("### 📋 My Follow-Up Tasks")
    tasks = load_followups()
    my_tasks = [t for t in tasks if t["patient"] == patient_username]

    if not my_tasks:
        st.info("No tasks assigned yet.")
        return

    for t in reversed(my_tasks):
        border_color = {"pending": "#ffa500", "completed": "#44ff44", "not_yet": "#ff4444"}.get(t["status"], "#2a3050")
        grade = t.get("grade", "none")
        if t["status"] == "completed" and grade != "none":
            border_color = {"green": "#44ff44", "yellow": "#ffd93d", "red": "#ff4444"}.get(grade, border_color)

        with st.container():
            st.markdown(
                f"<div style='border:1px solid {border_color};border-radius:10px;padding:14px;margin-bottom:10px;"
                f"background:#111827;'>",
                unsafe_allow_html=True,
            )
            st.markdown(f"**{t['title']}**")
            if t["description"]:
                st.markdown(f"<span style='color:#99aabb;font-size:13px;'>{t['description']}</span>",
                            unsafe_allow_html=True)

            if t["file_path"] and os.path.exists(t["file_path"]):
                with open(t["file_path"], "rb") as f:
                    st.download_button("⬇ View Attachment", f.read(),
                                       file_name=os.path.basename(t["file_path"]),
                                       key=f"fu_pat_dl_{t['id']}")

            if t["status"] == "pending":
                proof_key = f"fu_proof_up_{t['id']}"
                uploaded_proof = st.file_uploader("Upload proof (photo/file) then mark done",
                                                  key=proof_key,
                                                  type=["png", "jpg", "jpeg", "pdf", "mp4"])

                c1, c2 = st.columns(2)
                with c1:
                    can_complete = uploaded_proof is not None
                    if st.button("✅" if can_complete else "✅ (upload first)",
                                 use_container_width=True,
                                 key=f"fu_done_{t['id']}",
                                 disabled=not can_complete):
                        dest = _save_uploaded(uploaded_proof, PROOF_FILES, patient_username, f"_{t['id']}")
                        update_followup_status(t["id"], "completed", dest)
                        st.rerun()
                with c2:
                    if st.button("❌", key=f"fu_skip_{t['id']}", use_container_width=True):
                        update_followup_status(t["id"], "not_yet")
                        st.rerun()

            elif t["status"] == "completed":
                if t["proof_file"] and os.path.exists(t["proof_file"]):
                    with open(t["proof_file"], "rb") as f:
                        st.download_button("📎 View My Proof", f.read(),
                                           file_name=os.path.basename(t["proof_file"]),
                                           key=f"fu_pat_proof_{t['id']}")

                grade = t.get("grade", "none")
                if grade != "none":
                    grade_labels = {"green": "🟢 Correctly done", "yellow": "🟡 Partially done", "red": "🔴 Needs improvement"}
                    grade_colors = {"green": "#44ff44", "yellow": "#ffd93d", "red": "#ff4444"}
                    st.markdown(
                        f"<span style='color:{grade_colors.get(grade, '#99aabb')};font-weight:bold;font-size:15px;'>"
                        f"{grade_labels.get(grade, '')}</span>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.success("✅ **Completed** — Awaiting psychologist review.")

                feedback = t.get("feedback", "")
                if feedback:
                    st.markdown(
                        f"<div style='background:#1a1f2e;border:1px solid #2a3050;border-radius:8px;padding:10px;margin-top:6px;'>"
                        f"<span style='color:#99aabb;font-size:12px;'>Psychologist's feedback:</span><br>"
                        f"<span style='color:#e0e8ff;'>{feedback}</span></div>",
                        unsafe_allow_html=True,
                    )
                    grade_labels = {"green": "🟢 Correctly done", "yellow": "🟡 Partially done", "red": "🔴 Needs improvement"}
                    fb_data = _feedback_download_data(feedback, grade_labels.get(grade, "Not graded"))
                    st.download_button("⬇ Download Feedback", fb_data,
                                       file_name=f"feedback_{t['id']}.txt",
                                       key=f"fu_pat_fb_dl_{t['id']}")
            else:
                st.error("❌ **Not Completed**")

            st.caption(f"Assigned: {t['created_at'][:10]}")
            st.markdown("</div>", unsafe_allow_html=True)
