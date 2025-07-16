# app.py
import streamlit as st
import pandas as pd
import altair as alt
from pathlib import Path
from matplotlib.colors import LinearSegmentedColormap

# ─── 1) Page & theme config ─────────────────────────────────────────────────────
st.set_page_config(
    page_title="CFB Stat Game",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# a blue→light-gray colormap for our “Score”‐style gradients
cmap = LinearSegmentedColormap.from_list("blue_gray", ["#002060", "#d3d3d3"])

# a helper to render ANY DataFrame with:
#  • dark-blue headers + white text
#  • centered cells
#  • optional background_gradient on one column
#  • commas + no decimals
def display_table(df: pd.DataFrame, highlight: str = None):
    base_styles = [
        {
            "selector": "th",
            "props": [
                ("background-color", "#002060"),
                ("color", "white"),
                ("text-align", "center"),
            ],
        },
        {
            "selector": "td",
            "props": [("text-align", "center")],
        },
    ]
    st.markdown(
        """
        <style>
          /* make tables responsive on mobile */
          .dataframe {width:100% !important; overflow-x:auto;}
        </style>
        """,
        unsafe_allow_html=True,
    )
    styler = (
        df.style
        .set_table_styles(base_styles)
        .format("{:,.0f}")
    )
    if highlight:
        styler = styler.background_gradient(cmap=cmap, subset=[highlight])
    st.markdown(styler.to_html(), unsafe_allow_html=True)


# ─── 2) Load your Excel sheets ───────────────────────────────────────────────────
xlsx = pd.read_excel(
    Path("data") / "Stat Upload.xlsx",
    sheet_name=["Info", "Logos", "Past Winners"],
)
info         = xlsx["Info"]          # your week-by-week picks & scores
logos        = xlsx["Logos"]         # if you need team-logo URLs
past_winners = xlsx["Past Winners"]  # 2017–2024 history


# ─── 3) Sidebar navigation ──────────────────────────────────────────────────────
tab = st.sidebar.radio(
    "Navigate",
    [
        "Standings",
        "Performance Breakdown",
        "Player Stats",
        "Recaps",
        "Past Results",
        "Submission Form",
    ],
)


# ─── TAB 1: Standings ────────────────────────────────────────────────────────────
if tab == "Standings":
    st.header("Season Standings")
    # compute total score, rank ascending (lowest first)
    df = (
        info.groupby("Player")["Score"]
        .sum()
        .reset_index()
        .sort_values("Score", ascending=True)
        .reset_index(drop=True)
    )
    df.insert(0, "Rank", df.index + 1)
    df["Pts. From 1st"] = df["Score"] - df.loc[0, "Score"]

    display_table(df, highlight="Score")

    st.subheader("Rankings by Week")
    # build a bump‐chart: week × player ranked by that week's score
    week_scores = (
        info.pivot_table(
            index="Week",
            columns="Player",
            values="Score",
            aggfunc="sum",
        )
        .rank(axis=1, method="first", ascending=True)
        .reset_index()
        .melt("Week", var_name="Player", value_name="Rank")
    )
    chart = (
        alt.Chart(week_scores)
        .mark_line(point=True)
        .encode(
            x=alt.X("Week:O", axis=alt.Axis(labelAngle=90)),
            y=alt.Y("Rank:Q", sort="descending", title="Rank"),
            color="Player:N",
            order=alt.Order("Rank:Q"),
        )
        .properties(height=400)
    )
    st.altair_chart(chart, use_container_width=True)


# ─── TAB 2: Performance Breakdown ────────────────────────────────────────────────
elif tab == "Performance Breakdown":
    st.header("Performance Breakdown")
    # filters
    player = st.selectbox("Player", sorted(info["Player"].unique()))
    week   = st.selectbox("Week",   sorted(info["Week"].unique()))

    st.subheader(f"Picks for {player} – Week {week}")
    picks = info.query("Player == @player and Week == @week")
    display_table(picks[["Category","Player","Team","Opponent","Score"]], highlight="Score")

    st.subheader("Full Season Overview")
    season = (
        info.groupby("Week")
        [["Passing","Rushing","Receiving","Defensive"]]
        .sum()
    )
    season["Total"] = season.sum(axis=1)
    display_table(season.reset_index(), highlight="Total")


# ─── TAB 3: Player Stats ────────────────────────────────────────────────────────
elif tab == "Player Stats":
    st.header("All Picks (Sorted by Score)")
    df = info[["Player","Pick","Team","Opponent","Score"]].sort_values("Score", ascending=True)
    # if you have real URLs in logos, you can replace the Team column with an <img> tag
    display_table(df, highlight="Score")


# ─── TAB 4: Recaps ───────────────────────────────────────────────────────────────
elif tab == "Recaps":
    st.header("Weekly Recaps")
    recap_dir = Path("assets") / "recaps"
    if not recap_dir.exists():
        st.info("Create an `assets/recaps/` folder and upload your `Week #.pdf` files there.")
    else:
        for pdf in sorted(recap_dir.glob("Week *.pdf")):
            label = pdf.stem  # e.g. “Week 1 Recap”
            st.markdown(f"- [{label}]({pdf.as_posix()})")


# ─── TAB 5: Past Results ────────────────────────────────────────────────────────
elif tab == "Past Results":
    st.header("Past Winners (2017–2024)")
    years = [2017,2018,2019,2021,2022,2023,2024]
    for yr in years:
        block = past_winners.query("Year == @yr")[["Rank","Player","Score"]]
        if not block.empty:
            st.subheader(str(yr))
            display_table(block, highlight="Score")


# ─── TAB 6: Submission Form ─────────────────────────────────────────────────────
elif tab == "Submission Form":
    st.header("Make Your Picks")
    st.write("If you’d rather use a Google Form, it’s embedded here:")
    st.components.v1.iframe(
        "https://docs.google.com/forms/d/e/1FAIpQLSdy_WqAQlK_0gPC1xwT2mQqQucHArM9Is8jbVH3l0bVMk-HKw/viewform?embedded=true",
        height=800,
        scrolling=True,
    )
