import streamlit as st
import plotly.graph_objects as go

try:
    from ring_ import get_seeded_history
except Exception:
    get_seeded_history = None


def safe(func, default=None, *args, **kwargs):
    try:
        if func is not None:
            return func(*args, **kwargs)
    except Exception as e:
        import sys; print(f"[safe] {func.__name__ if func else 'None'}: {e}", file=sys.stderr)
    return default if default is not None else {}


def psych_metric(label, value, unit, color):
    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, {color}15, {color}08);
            padding: 14px;
            border-radius: 10px;
            border: 1px solid {color}30;
            text-align: center;
            backdrop-filter: blur(4px);
        ">
            <div style="color:#7a8aaa;font-size:0.75rem;font-weight:500;">{label}</div>
            <div style="color:#f0f4ff;font-size:1.5rem;font-weight:700;">{value}</div>
            <div style="color:#7a8aaa;font-size:0.6875rem;">{unit}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def mini_chart(username, metric, color):
    values = safe(get_seeded_history, [], username, metric, 24)
    if not values:
        return
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        y=values, mode="lines",
        line=dict(color=color, width=1.5, shape="spline"),
        opacity=0.6,
    ))
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0), height=50,
        showlegend=False, paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False, showgrid=False),
        yaxis=dict(visible=False, showgrid=False),
        hovermode="x unified", dragmode=False,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False, "displaylogo": False})


def read_crisis_state():
    try:
        from data_manager_ import get_crisis_state
        return get_crisis_state()
    except Exception:
        pass
    return {}
