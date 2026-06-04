import pandas as pd
from streamlit_echarts import st_echarts
import plotly.graph_objects as go
import plotly.express as px
import plotly.io as pio
import streamlit as st
import calendar

##################################################################
# CSS
##################################################################

st.markdown("""
<style>

.st-key-heatmap_card {
    background-color: #ffffff !important;
    border-radius: 18px !important;
    padding: 1.2rem !important;
    border: 1px solid rgba(15, 23, 42, 0.05) !important;
    box-shadow:
        0 1px 3px rgba(0, 0, 0, 0.08),
        0 4px 12px rgba(0, 0, 0, 0.08);
}

.st-key-bar_chart_card, 
.st-key-quadrant_card {
    background-color: white !important;
    border-radius: 18px !important;
    padding: 1.2rem !important;
    border: 1px solid rgba(15,23,42,0.05) !important;
    box-shadow:
        0 1px 3px rgba(0, 0, 0, 0.08),
        0 4px 12px rgba(0, 0, 0, 0.08);
    min-height: 660px !important;
}

</style>
""", unsafe_allow_html=True)


##################################################################
# DATA
##################################################################

@st.cache_data
def load_data():
    df = pd.read_csv("healthcare_clean.csv")
    return df


@st.cache_data
def transform_data(df):
    df = df.copy()
    df["datetime"] = pd.to_datetime(df["datetime"])
    for col in ["nps", "csi", "loyalty", "ces"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["date"] = df["datetime"].dt.date
    df["year_month"] = df["datetime"].dt.to_period("M")
    return df


TOUCHPOINT_COLUMNS = {
    "registration":       "Registration",
    "doctor_consultation":"Doctor Consultation",
    "nurse_service":      "Nurse Service",
    "pharmacy_service":   "Pharmacy Service",
    "laboratory":         "Laboratory",
    "emergency_response": "Emergency Response",
    "billing_process":    "Billing Process",
    "facility_cleanliness":"Facility Cleanliness",
    "staff_friendliness": "Staff Friendliness",
    "waiting_time":       "Waiting Time",
}


##################################################################
# HELPERS
##################################################################

def apply_branch_filter(df, selected_branches):
    if selected_branches:
        return df[df["branch"].isin(selected_branches)]
    return df.copy()


def get_kpi_avg(df, metric):
    if df is None or df.empty:
        return 0
    return df[metric].mean()


def build_touchpoint_heatmap_data(df):
    month_labels = list(calendar.month_abbr[1:13])
    touchpoint_labels = list(TOUCHPOINT_COLUMNS.values())
    heatmap_data = []
    for y_idx, (col_name, display_name) in enumerate(TOUCHPOINT_COLUMNS.items()):
        monthly_avg = (
            df.groupby(df["datetime"].dt.month)[col_name]
            .mean()
            .reindex(range(1, 13))
        )
        for month_num, value in monthly_avg.items():
            if pd.notna(value):
                heatmap_data.append([
                    month_num - 1,
                    y_idx,
                    round(float(value), 1)
                ])
    return heatmap_data, month_labels, touchpoint_labels


def build_improvement_bar_data(df):
    touchpoint_scores = []
    for col_name, display_name in TOUCHPOINT_COLUMNS.items():
        avg_score = df[col_name].mean()
        if pd.notna(avg_score):
            touchpoint_scores.append({
                "touchpoint": display_name,
                "score": round(float(avg_score), 1)
            })
    bar_df = pd.DataFrame(touchpoint_scores)
    return bar_df.sort_values(by="score", ascending=True).head(3)


##################################################################
# MAIN
##################################################################

raw_df = load_data()
df = transform_data(raw_df)


##################################################################
# SIDEBAR
##################################################################

with st.sidebar:
    all_branches = sorted(df["branch"].unique())

    branch_display = {
        b: b.split("Always Healthy Hospital ")[-1] + " Always Healthy Hospital"
        for b in all_branches
    }

    selected_display = st.selectbox(
        "Branch",
        options=list(branch_display.values())
    )

    selected_branches = [
        k for k, v in branch_display.items()
        if v in selected_display
    ]
    df_branch = apply_branch_filter(df, selected_branches)

    month_options = [
        "January 2025", "February 2025", "March 2025", "April 2025",
        "May 2025", "June 2025", "July 2025", "August 2025",
        "September 2025", "October 2025", "November 2025", "December 2025",
        "Custom"
    ]
    selected_period = st.selectbox("Period", month_options, index=11)

    if selected_period == "Custom":
        custom_range = st.date_input(
            "Custom Date Range",
            value=(df_branch["datetime"].min().date(), df_branch["datetime"].max().date())
        )


##################################################################
# DATE RANGE LOGIC
##################################################################

if selected_period != "Custom":
    month_map = {
        "January 2025": "2025-01", "February 2025": "2025-02",
        "March 2025": "2025-03", "April 2025": "2025-04",
        "May 2025": "2025-05", "June 2025": "2025-06",
        "July 2025": "2025-07", "August 2025": "2025-08",
        "September 2025": "2025-09", "October 2025": "2025-10",
        "November 2025": "2025-11", "December 2025": "2025-12",
    }
    selected_month = pd.Period(month_map[selected_period], freq="M")
    current_df = df_branch[df_branch["year_month"] == selected_month].copy()
    months = sorted(df_branch["year_month"].unique())
    idx = months.index(selected_month)
    prev_df = None if idx == 0 else df_branch[df_branch["year_month"] == months[idx - 1]].copy()
else:
    if len(custom_range) == 2:
        start_date = pd.to_datetime(custom_range[0])
        end_date = pd.to_datetime(custom_range[1])
    else:
        start_date = df_branch["datetime"].min()
        end_date = df_branch["datetime"].max()
    current_df = df_branch[
        (df_branch["datetime"] >= start_date) &
        (df_branch["datetime"] <= end_date)
    ].copy()


##################################################################
# PAGE
##################################################################

st.title("🔬 Touchpoint Performance")
st.caption("Analysis of touchpoint performance across hospital services.")


##################################################################
# HEATMAP + BAR CHART
##################################################################

left_col, right_col = st.columns([2.99, 0.98])

with left_col:
    with st.container(key="heatmap_card"):

        st.markdown("### Touchpoint Performance Heatmap")
        st.caption(
            "Average touchpoint score by month across all years "
            "(filtered by selected branches only)."
        )

        heatmap_data, month_labels, touchpoint_labels = build_touchpoint_heatmap_data(df_branch)

        max_val = max([row[2] for row in heatmap_data]) if heatmap_data else 5

        heatmap_opts = {
            "tooltip": {
                "position": "top",
                "formatter": """
                function (params) {
                    return 'Touchpoint: ' + params.name +
                        '<br/>Month: ' + params.value[0] +
                        '<br/>Value: ' + params.value[2];
                }
                """,
            },
            "grid": {
                "height": "72%", "top": "8%",
                "bottom": "12%", "left": "1%", "right": "4%",
            },
            "xAxis": {
                "type": "category",
                "data": month_labels,
                "axisLabel": {"rotate": 0, "interval": 0, "fontSize": 11},
            },
            "yAxis": {
                "type": "category",
                "data": touchpoint_labels,
                "axisLabel": {"fontSize": 11, "align": "left", "margin": 120},
            },
            "visualMap": {
                "type": "piecewise",
                "orient": "horizontal",
                "left": "center",
                "bottom": "0%",
                "pieces": [
                    {"min": 1,    "max": 1.5,  "color": "#b91c1c"},
                    {"min": 1.51, "max": 2.0,  "color": "#dc2626"},
                    {"min": 2.01, "max": 2.5,  "color": "#ef4444"},
                    {"min": 2.51, "max": 2.99, "color": "#fca5a5"},
                    {"min": 3.0,  "max": 3.0,  "color": "#d1d5db"},
                    {"min": 3.01, "max": 3.5,  "color": "#bbf7d0"},
                    {"min": 3.51, "max": 4.0,  "color": "#86efac"},
                    {"min": 4.01, "max": 4.5,  "color": "#22c55e"},
                    {"min": 4.51, "max": 5.0,  "color": "#15803d"},
                ]
            },
            "series": [{
                "name": "Touchpoint Score",
                "type": "heatmap",
                "data": heatmap_data,
                "label": {"show": True, "fontSize": 10, "color": "#111827"},
                "emphasis": {"itemStyle": {"shadowBlur": 10, "shadowColor": "rgba(0,0,0,0.25)"}},
            }],
        }

        st_echarts(options=heatmap_opts, height="520px", key="touchpoint_heatmap", theme="light")

with right_col:
    with st.container(key="bar_chart_card"):

        st.markdown(
            "<div style='text-align:center; margin-bottom:32px;'>"
                "<div style='font-size:18px; font-weight:700; color:#111827;'>"
                    "Area of Improvement"
                "</div>"
                "<div style='font-size:12px; color:#6b7280; margin-top:4px;'>"
                    "Lowest touchpoint scores"
                "</div>"
            "</div>",
            unsafe_allow_html=True
        )

        bar_df = build_improvement_bar_data(current_df)

        improvement_items = []
        reds = ["#b91c1c", "#ef4444", "#fca5a5"]

        for idx, (_, row) in enumerate(bar_df.iterrows()):
            score_pct      = (row["score"] / 5) * 100
            touchpoint_name = str(row["touchpoint"])
            score_val      = str(row["score"])
            bar_color      = reds[idx]
            bar_width      = f"{score_pct:.1f}%"

            item_html = (
                "<div style='margin-bottom:32px;'>"
                    "<div style='font-size:14px; font-weight:600; color:#374151; margin-bottom:10px;'>"
                        + touchpoint_name +
                    "</div>"
                    "<div style='display:flex; align-items:center; gap:10px;'>"
                        "<div style='flex:1; background:#f3f4f6; border-radius:999px; height:14px; overflow:hidden;'>"
                            "<div style='width:" + bar_width + "; height:100%; background:" + bar_color + "; border-radius:999px;'></div>"
                        "</div>"
                        "<div style='font-size:12px; font-weight:600; color:#111827; min-width:28px;'>"
                            + score_val +
                        "</div>"
                    "</div>"
                "</div>"
            )
            improvement_items.append(item_html)

        st.markdown("".join(improvement_items), unsafe_allow_html=True)

##################################################################
# COMPLAINTS VS IMPACT
##################################################################
touchpoints = [
    "registration",
    "doctor_consultation",
    "nurse_service",
    "pharmacy_service",
    "laboratory",
    "emergency_response",
    "billing_process",
    "facility_cleanliness",
    "staff_friendliness",
    "waiting_time"
]

touchpoint_labels = {
    "registration": "Registration",
    "doctor_consultation": "Doctor Consultation",
    "nurse_service": "Nurse Service",
    "pharmacy_service": "Pharmacy Service",
    "laboratory": "Laboratory",
    "emergency_response": "Emergency Response",
    "billing_process": "Billing Process",
    "facility_cleanliness": "Facility Cleanliness",
    "staff_friendliness": "Staff Friendliness",
    "waiting_time": "Waiting Time"
}

impact_data = []

for tp in touchpoints:

    performance = current_df[tp].mean()

    impact = current_df[[tp, "loyalty"]].corr().iloc[0, 1]

    impact_data.append({
        "Touchpoint": touchpoint_labels[tp],
        "Performance": performance,
        "Impact": impact
    })

impact_df = pd.DataFrame(impact_data)

avg_perf = impact_df["Performance"].mean()
avg_imp = impact_df["Impact"].mean()

def get_quadrant(row):

    if row["Performance"] < avg_perf and row["Impact"] >= avg_imp:
        return "Priority Improvement"

    elif row["Performance"] >= avg_perf and row["Impact"] >= avg_imp:
        return "Keep It Up"

    elif row["Performance"] < avg_perf and row["Impact"] < avg_imp:
        return "Low Priority"

    else:
        return "Maintain"

impact_df["Quadrant"] = impact_df.apply(
    get_quadrant,
    axis=1
)

with st.container(key="quadrant_card"):

    st.markdown("### Touchpoint Quadrant Analysis")

    st.caption(
        "Touchpoints are classified based on performance and impact on loyalty."
    )

    fig = px.scatter(
        impact_df,
        x="Performance",
        y="Impact",
        color="Quadrant",
        text="Touchpoint",
        height=550
    )

    fig.update_traces(
        textposition="top center",
        marker=dict(size=18)
    )

    fig.add_vline(
        x=avg_perf,
        line_dash="dash"
    )

    fig.add_hline(
        y=avg_imp,
        line_dash="dash"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )