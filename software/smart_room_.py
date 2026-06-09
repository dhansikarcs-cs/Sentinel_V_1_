import streamlit as st


def render_smart_room(mode: str = "calm", intensity: float = 1.0):
    st.markdown("### 🧠 Smart Room")

    if mode == "calm":
        st.markdown(
            """
            <div style="display:flex;flex-direction:column;align-items:center;padding:30px 0;">
                <div style="
                    width:180px;height:180px;border-radius:50%;
                    background: radial-gradient(circle at 35% 35%, #ffd700, #b8860b);
                    box-shadow: 0 0 80px rgba(255,215,0,0.25), 0 0 160px rgba(255,215,0,0.08);
                "></div>
                <div style="margin-top:16px;font-size:14px;color:#aab;text-align:center;">
                    <div style="font-size:18px;font-weight:600;color:#e0e8ff;margin-bottom:4px;">Calming Mode</div>
                    Ambient lighting · Low stimulus · Relaxed atmosphere
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        glow_intensity = min(1, intensity / 2)
        st.markdown(
            f"""
            <div style="display:flex;flex-direction:column;align-items:center;padding:30px 0;">
                <div style="position:relative;display:flex;align-items:center;justify-content:center;">
                    <div style="
                        position:absolute;width:300px;height:300px;border-radius:50%;
                        border:1.5px solid rgba(0,150,255,{0.08 * intensity});
                        animation:none;
                    "></div>
                    <div style="
                        position:absolute;width:250px;height:250px;border-radius:50%;
                        border:1.5px solid rgba(0,150,255,{0.15 * intensity});
                        animation:none;
                    "></div>
                    <div style="
                        position:absolute;width:200px;height:200px;border-radius:50%;
                        border:1.5px solid rgba(0,150,255,{0.25 * intensity});
                        animation:none;
                    "></div>
                    <div style="
                        width:150px;height:150px;border-radius:50%;
                        background: radial-gradient(circle at 35% 35%, #5599ff, #0033aa);
                        box-shadow: 0 0 {60 + 40 * intensity}px rgba(0,100,255,{0.3 + 0.1 * intensity});
                    "></div>
                    <div style="
                        position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);
                        display:flex;gap:2px;opacity:0.2;
                    ">
                        <div style="width:4px;height:40px;background:white;border-radius:2px;"></div>
                        <div style="width:4px;height:60px;background:white;border-radius:2px;"></div>
                        <div style="width:4px;height:50px;background:white;border-radius:2px;"></div>
                        <div style="width:4px;height:65px;background:white;border-radius:2px;"></div>
                        <div style="width:4px;height:45px;background:white;border-radius:2px;"></div>
                        <div style="width:4px;height:55px;background:white;border-radius:2px;"></div>
                        <div style="width:4px;height:38px;background:white;border-radius:2px;"></div>
                    </div>
                </div>
                <div style="margin-top:16px;font-size:14px;color:#aab;text-align:center;">
                    <div style="font-size:18px;font-weight:600;color:#e0e8ff;margin-bottom:4px;">Focused Mode</div>
                    Active monitoring · Diffuser engaged · High awareness
                </div>
                <div style="display:flex;gap:24px;margin-top:10px;font-size:12px;color:#668;">
                    <span>💧 Humidifier</span>
                    <span>🔊 Sound scan</span>
                    <span>📡 Full sensor array</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.caption("Smart room responds to emotional state and environmental stress levels.")
