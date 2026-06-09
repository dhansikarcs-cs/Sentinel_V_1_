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


def metric_card(label, value, unit, color, delta=None):
    delta_str = f" ({delta})" if delta else ""
    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, {color}18, {color}08);
            padding: 16px;
            border-radius: 12px;
            border: 1px solid {color}30;
            text-align: center;
            backdrop-filter: blur(4px);
        ">
            <div style="color:#7a8aaa;font-size:0.8125rem;margin-bottom:4px;font-weight:500;">{label}</div>
            <div style="color:#f0f4ff;font-size:1.75rem;font-weight:700;">{value}</div>
            <div style="color:#7a8aaa;font-size:0.75rem;">{unit}{delta_str}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def trend_chart(username, metric, label, color, hours=24):
    values = safe(get_seeded_history, [], username, metric, hours)
    if not values:
        return
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        y=values, mode="lines", name=label,
        line=dict(color=color, width=1.5, shape="spline"),
        opacity=0.75,
    ))
    fig.update_layout(
        margin=dict(l=4, r=4, t=4, b=4), height=90,
        showlegend=False, paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False, showgrid=False),
        yaxis=dict(visible=False, showgrid=False),
        hovermode="x unified", dragmode=False,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False, "displaylogo": False})
