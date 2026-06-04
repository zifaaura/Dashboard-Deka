import pandas as pd
from streamlit_echarts import st_echarts
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st
import calendar

##################################################################
# CSS
##################################################################

st.markdown("""
<style>

.st-key-kpi_nps,
.st-key-kpi_csi,
.st-key-kpi_loyalty,
.st-key-kpi_ces {
    background-color: #ffffff !important;
    border-radius: 18px !important;
    padding: 0.9rem !important;
    border: 1px solid rgba(15, 23, 42, 0.05) !important;
    box-shadow:
        0 1px 2px rgba(0, 0, 0, 0.2),
        0 2px 8px rgba(0, 0, 0, 0.2);
}

.st-key-heatmap_card {
    background-color: #ffffff !important;
    border-radius: 18px !important;
    padding: 1.2rem !important;
    border: 1px solid rgba(15, 23, 42, 0.05) !important;
    box-shadow:
        0 1px 2px rgba(0, 0, 0, 0.2),
        0 2px 8px rgba(0, 0, 0, 0.2);
}

.st-key-bar_chart_card {
    background-color: white !important;
    border-radius: 18px !important;
    padding: 1.2rem !important;
    border: 1px solid rgba(15,23,42,0.05) !important;
    box-shadow:
        0 1px 2px rgba(0, 0, 0, 0.2),
        0 2px 8px rgba(0, 0, 0, 0.2);
    min-height: 660px !important;
}

</style>
""", unsafe_allow_html=True)


##################################################################
# UI TUNING
##################################################################

CHART_VERTICAL_OFFSET = 28
LEFT_CONTENT_OFFSET = 22
CHART_HEIGHT = 45


##################################################################
# DATA
##################################################################

@st.cache_data
def load_data():
    return pd.read_csv("healthcare_clean.csv")


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
    "registration": "Registration",
    "doctor_consultation": "Doctor Consultation",
    "nurse_service": "Nurse Service",
    "pharmacy_service": "Pharmacy Service",
    "laboratory": "Laboratory",
    "emergency_response": "Emergency Response",
    "billing_process": "Billing Process",
    "facility_cleanliness": "Facility Cleanliness",
    "staff_friendliness": "Staff Friendliness",
    "waiting_time": "Waiting Time",
}


##################################################################
# HELPERS
##################################################################

def apply_branch_filter(df, selected_branches):
    if selected_branches:
        return df[df["branch"].isin(selected_branches)]
    return df.copy()


def get_previous_period_df(df, start_date, end_date):

    current_days = (end_date - start_date).days + 1

    prev_end = start_date - pd.Timedelta(days=1)
    prev_start = prev_end - pd.Timedelta(days=current_days - 1)

    prev_df = df[
        (df["datetime"] >= prev_start) &
        (df["datetime"] <= prev_end)
    ].copy()

    return prev_df


def get_previous_period_df(df, start_date, end_date):

    current_days = (end_date - start_date).days + 1

    prev_end = start_date - pd.Timedelta(days=1)
    prev_start = prev_end - pd.Timedelta(days=current_days - 1)

    prev_df = df[
        (df["datetime"] >= prev_start) &
        (df["datetime"] <= prev_end)
    ].copy()

    return prev_df


def get_kpi_avg(df, metric):
    if df is None or df.empty:
        return 0
    return df[metric].mean()


def get_delta(curr_val, prev_val):
    if prev_val is None or prev_val == 0:
        return "0.0%", "#94a3b8"

    delta_pct = ((curr_val - prev_val) / prev_val) * 100

    if delta_pct > 0:
        return f"▲ {delta_pct:.1f}%", "#16a34a"
    elif delta_pct < 0:
        return f"▼ {abs(delta_pct):.1f}%", "#dc2626"
    else:
        return "0.0%", "#94a3b8"


def get_badge_bg(delta_color):
    if delta_color == "#16a34a":
        return "#dcfce7"
    elif delta_color == "#dc2626":
        return "#fee2e2"
    return "#f1f5f9"


def get_sparkline_series(df, metric):
    if df is None or df.empty:
        return pd.Series(dtype=float)

    series = (
        df.groupby("date")[metric]
        .mean()
        .round(2)
    )

    series.index = pd.to_datetime(series.index)

    return series


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
                    month_num - 1,   # x
                    y_idx,           # y
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

    return bar_df.sort_values(
        by="score",
        ascending=True
    ).head(3)


##################################################################
# CHART
##################################################################

def plot_sparkline(series, color):
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=series.index,
            y=series.values,
            mode="lines",
            line=dict(
                color=color,
                width=2.5
            ),
            hovertemplate="%{x|%d %b %Y}<br>Value: %{y:.2f}<extra></extra>",
        )
    )

    fig.update_xaxes(
        visible=False,
        fixedrange=True
    )

    fig.update_yaxes(
        visible=False,
        fixedrange=True
    )

    fig.update_layout(
        showlegend=False,
        plot_bgcolor="white",
        paper_bgcolor="white",
        height=CHART_HEIGHT,
        margin=dict(
            t=0,
            l=0,
            r=0,
            b=0
        ),
    )

    return fig


##################################################################
# KPI CARD
##################################################################

def display_kpi_card(
    label,
    avg_val,
    delta_str,
    delta_color,
    spark_series,
    key_name
):

    badge_bg = get_badge_bg(delta_color)

    if delta_color == "#16a34a":
        line_color = "#16a34a"
    elif delta_color == "#dc2626":
        line_color = "#dc2626"
    else:
        line_color = "#94a3b8"

    with st.container(key=key_name):

        top_left, top_right = st.columns([1.7, 1.3])
        bottom_left, bottom_right = st.columns([1.1, 1])

        # TOP LEFT
        with top_left:
            st.markdown(
                f"""
                <div style="
                    font-size:18px;
                    font-weight:700;
                    color:#475569;
                ">
                    {label}
                </div>
                """,
                unsafe_allow_html=True
            )

        # TOP RIGHT
        with top_right:
            st.markdown(
                f"""
                <div style="
                    display:inline-flex;
                    align-items:center;
                    justify-content:center;
                    padding:4px 10px;
                    border-radius:999px;
                    background-color:{badge_bg};
                    color:{delta_color};
                    font-size:15px;
                    font-weight:700;
                    float:right;
                    white-space:nowrap;
                    line-height:1.1;
                ">
                    {delta_str}
                </div>
                """,
                unsafe_allow_html=True
            )

        # BOTTOM LEFT
        with bottom_left:

            st.markdown(
                f"<div style='height:{LEFT_CONTENT_OFFSET}px;'></div>",
                unsafe_allow_html=True
            )

            st.markdown(
                """
                <div style="
                    font-size:13px;
                    color:#94a3b8;
                    font-weight:500;
                ">
                    Average
                </div>
                """,
                unsafe_allow_html=True
            )

            st.markdown(
                f"""
                <div style="
                    font-size:26px;
                    font-weight:700;
                    color:#000000;
                    margin-top:2px;
                ">
                    {avg_val:.2f}
                </div>
                """,
                unsafe_allow_html=True
            )

        # BOTTOM RIGHT
        with bottom_right:

            st.markdown(
                f"<div style='height:{CHART_VERTICAL_OFFSET}px;'></div>",
                unsafe_allow_html=True
            )

            if not spark_series.empty:
                fig = plot_sparkline(
                    spark_series,
                    line_color
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True,
                    config={"displayModeBar": False}
                )


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

    selected_branches = st.multiselect(
        "Cabang",
        all_branches,
        default=all_branches
    )

    df_branch = apply_branch_filter(df, selected_branches)

    month_options = [
        "January 2025",
        "February 2025",
        "March 2025",
        "April 2025",
        "May 2025",
        "June 2025",
        "July 2025",
        "August 2025",
        "September 2025",
        "October 2025",
        "November 2025",
        "December 2025",
        "Custom"
    ]

    selected_period = st.selectbox(
        "Periode",
        month_options,
        index=11
    )

    if selected_period == "Custom":
        custom_range = st.date_input(
            "Custom Date Range",
            value=(
                df_branch["datetime"].min().date(),
                df_branch["datetime"].max().date()
            )
        )


##################################################################
# DATE RANGE LOGIC
##################################################################

if selected_period != "Custom":

    month_map = {
        "January 2025": "2025-01",
        "February 2025": "2025-02",
        "March 2025": "2025-03",
        "April 2025": "2025-04",
        "May 2025": "2025-05",
        "June 2025": "2025-06",
        "July 2025": "2025-07",
        "August 2025": "2025-08",
        "September 2025": "2025-09",
        "October 2025": "2025-10",
        "November 2025": "2025-11",
        "December 2025": "2025-12",
    }

    selected_month = pd.Period(
        month_map[selected_period],
        freq="M"
    )

    current_df = df_branch[
        df_branch["year_month"] == selected_month
    ].copy()

    months = sorted(df_branch["year_month"].unique())

    idx = months.index(selected_month)

    if idx == 0:
        prev_df = None
    else:
        prev_df = df_branch[
            df_branch["year_month"] == months[idx - 1]
        ].copy()

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

    prev_df = get_previous_period_df(
        df_branch,
        start_date,
        end_date
    )

        
##################################################################
# DATE RANGE LOGIC
##################################################################

if selected_period != "Custom":

    month_map = {
        "January 2025": "2025-01",
        "February 2025": "2025-02",
        "March 2025": "2025-03",
        "April 2025": "2025-04",
        "May 2025": "2025-05",
        "June 2025": "2025-06",
        "July 2025": "2025-07",
        "August 2025": "2025-08",
        "September 2025": "2025-09",
        "October 2025": "2025-10",
        "November 2025": "2025-11",
        "December 2025": "2025-12",
    }

    selected_month = pd.Period(
        month_map[selected_period],
        freq="M"
    )

    current_df = df_branch[
        df_branch["year_month"] == selected_month
    ].copy()

    months = sorted(df_branch["year_month"].unique())

    idx = months.index(selected_month)

    if idx == 0:
        prev_df = None
    else:
        prev_df = df_branch[
            df_branch["year_month"] == months[idx - 1]
        ].copy()

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

    prev_df = get_previous_period_df(
        df_branch,
        start_date,
        end_date
    )


##################################################################
# PAGE
##################################################################

st.title("🏥 Always Healthy Hospital Performance")
st.caption("Monitor performa layanan rumah sakit berdasarkan data survei pasien.")


##################################################################
# KPI CONFIG
##################################################################

KPI_CONFIG = [
    ("NPS", "nps", "kpi_nps"),
    ("CSI", "csi", "kpi_csi"),
    ("Loyalty", "loyalty", "kpi_loyalty"),
    ("CES", "ces", "kpi_ces"),
]


##################################################################
# RENDER KPI
##################################################################

cols = st.columns(4)

for col, (label, metric, key_name) in zip(cols, KPI_CONFIG):

    curr_val = get_kpi_avg(current_df, metric)
    prev_val = get_kpi_avg(prev_df, metric)

    delta_str, delta_color = get_delta(curr_val, prev_val)

    spark_series = get_sparkline_series(
        current_df,
        metric
    )

    with col:
        display_kpi_card(
            label=label,
            avg_val=curr_val,
            delta_str=delta_str,
            delta_color=delta_color,
            spark_series=spark_series,
            key_name=key_name
        )

##################################################################
# TOUCHPOINT SECTION
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
                "height": "72%",
                "top": "8%",
                "bottom": "12%",
                "left": "1%",
                "right": "4%",
            },
            "xAxis": {
                "type": "category",
                "data": month_labels,
                "axisLabel": {
                    "rotate": 0,
                    "interval": 0,
                    "fontSize": 11,
                },
            },
            "yAxis": {
                "type": "category",
                "data": touchpoint_labels,
                "axisLabel": {
                    "fontSize": 11,
                    "align": "left",
                    "margin": 120,
                },
            },
            "visualMap": {
                "type": "piecewise",
                "orient": "horizontal",
                "left": "center",
                "bottom": "0%",
                "pieces": [
                    {
                        "min": 1,
                        "max": 1.5,
                        "color": "#b91c1c"
                    },
                    {
                        "min": 1.51,
                        "max": 2.0,
                        "color": "#dc2626"
                    },
                    {
                        "min": 2.01,
                        "max": 2.5,
                        "color": "#ef4444"
                    },
                    {
                        "min": 2.51,
                        "max": 2.99,
                        "color": "#fca5a5"
                    },
                    {
                        "min": 3.0,
                        "max": 3.0,
                        "color": "#d1d5db"
                    },
                    {
                        "min": 3.01,
                        "max": 3.5,
                        "color": "#bbf7d0"
                    },
                    {
                        "min": 3.51,
                        "max": 4.0,
                        "color": "#86efac"
                    },
                    {
                        "min": 4.01,
                        "max": 4.5,
                        "color": "#22c55e"
                    },
                    {
                        "min": 4.51,
                        "max": 5.0,
                        "color": "#15803d"
                    },
                ]
            },
            "series": [
                {
                    "name": "Touchpoint Score",
                    "type": "heatmap",
                    "data": heatmap_data,
                    "label": {
                        "show": True,
                        "fontSize": 10,
                        "color": "#111827",
                    },
                    "emphasis": {
                        "itemStyle": {
                            "shadowBlur": 10,
                            "shadowColor": "rgba(0,0,0,0.25)"
                        }
                    },
                }
            ],
        }

        st_echarts(
            options=heatmap_opts,
            height="520px",
            key="touchpoint_heatmap",
            theme="light"
        )

with right_col:
    with st.container(key="bar_chart_card"):

        # TITLE
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

            score_pct = (row["score"] / 5) * 100
            touchpoint_name = str(row["touchpoint"])
            score_val = str(row["score"])
            bar_color = reds[idx]
            bar_width = f"{score_pct:.1f}%"

            item_html = (
                "<div style='margin-bottom:32px;'>"

                    "<div style='"
                        "font-size:14px;"
                        "font-weight:600;"
                        "color:#374151;"
                        "margin-bottom:10px;"
                    "'>"
                        + touchpoint_name +
                    "</div>"

                    "<div style='"
                        "display:flex;"
                        "align-items:center;"
                        "gap:10px;"
                    "'>"

                        "<div style='"
                            "flex:1;"
                            "background:#f3f4f6;"
                            "border-radius:999px;"
                            "height:14px;"
                            "overflow:hidden;"
                        "'>"

                            "<div style='"
                                "width:" + bar_width + ";"
                                "height:100%;"
                                "background:" + bar_color + ";"
                                "border-radius:999px;"
                            "'></div>"

                        "</div>"

                        "<div style='"
                            "font-size:12px;"
                            "font-weight:600;"
                            "color:#111827;"
                            "min-width:28px;"
                        "'>"
                            + score_val +
                        "</div>"

                    "</div>"

                "</div>"
            )

            improvement_items.append(item_html)

        st.markdown(
            "".join(improvement_items),
            unsafe_allow_html=True
        )