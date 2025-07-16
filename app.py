# app.py
import streamlit as st
import pandas as pd
import altair as alt
from pathlib import Path
from matplotlib.colors import LinearSegmentedColormap

# ─── 1) Page & Theme Config ────────────────────────────────────────────────────
st.set_page_config(
    page_title="CFB Stat Game",
    layout="wide",
    initial_sidebar_state="collapsed"
)
# a blue→light-gray colormap for our conditional gradients
cmap = LinearSegmentedColormap.from_list("blue_gray", ["#002060", "#d3d3d3"])


# ─── 2) Utility: Responsive, Styled Table ───────────────────────────────────────
def display_table(df: pd.DataFrame, highlight: str = None):
    """
    Renders df as a responsive HTML table with:
      • dark-blue headers + white text
      • centered cells
      • optional background_gradient on one column
      • comma separators, zero decimal places
    """
    # base CSS
    styles = [
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
    # force responsiveness
    st.markdown(
        """
        <style>
          .dataframe {width:100% !important; overflow-x:auto;}
        </style>
        """,
        unsafe_allow_html=True,
    )
    styler = (
        df.style
          .set_table_styles(styles)
          .format("{:,.0f}")
    )
    if highlight:
        styler = styler.background_gradient(cmap=cmap, subset=[highlight])
    st.markdown(styler.to_html(), unsafe_allow_html=True)


# ─── 3) Load Your Excel Sheets (skip the top “metadata” row) ─────────────────────
wb = Path("Stat Upload.xlsx")
# Info sheet: real header is on Excel row 2, so header=1
info = pd.read_excel(wb, sheet_name="Info", header=1)
info = info[["Player","Week","Role","Pick","Team","Opponent","Score"]]

# Logos sheet: header is also on row 2
logos = pd.read_excel(wb, sheet_name="Logos", header=1)
logos = logos.rename(columns={"Image URL":"Logo"}).drop(columns=[c for c in logos.columns if c not in ("Team","Logo")])

# Past Winners: header row 2 again
past = pd.read_excel(wb, sheet_name="Past Winners", header=1)
past = past[["Year","Rank","Player","Score"]]


# ─── 4) Sidebar Navigation ──────────────────────────────────────────────────────
tab = st.sidebar.radio(
    "Go to:",
    ["Standings", "Performance Breakdown", "Player Stats", "Recaps", "Past Results", "Submission Form"]
)


# ─── TAB 1: Standings ────────────────────────────────────────────────────────────
if tab == "Standings":
    st.title("🏆 Season Standings")
    # total up each player's score, rank ascending (lowest=1)
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

    st.subheader("🔀 Rankings by Week")
    # build a bump chart from per-week player scores → ranks
    week_scores = (
      info.pivot_table(
          index="Week",
          columns="Player",
          values="Score",
          aggfunc="sum",
      )
      .rank(axis=1, ascending=True, method="first")
      .reset_index()
      .melt("Week", var_name="Player", value_name="Rank")
    )
    bump = (
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
    st.altair_chart(bump, use_container_width=True)


# ─── TAB 2: Performance Breakdown ────────────────────────────────────────────────
elif tab == "Performance Breakdown":
    st.title("📊 Performance Breakdown")
    # filters
    player = st.selectbox("Player", sorted(info["Player"].unique()))
    week   = st.selectbox("Week",   sorted(info["Week"].unique()))

    st.subheader(f"Picks: {player} — Week {week}")
    picks = info.query("Player == @player and Week == @week")
    display_table(picks[["Role","Player","Team","Opponent","Score"]], highlight="Score")

    st.subheader("Full Season Overview by Category")
    pivot = (
      info.pivot_table(
        index="Week",
        columns="Role",
        values="Score",
        aggfunc="sum",
        fill_value=0
      )
    )
    # ensure all four roles exist
    for role in ["Passing","Rushing","Receiving","Defensive"]:
        if role not in pivot.columns:
            pivot[role] = 0
    pivot = pivot[["Passing","Rushing","Receiving","Defensive"]]
    pivot["Total"] = pivot.sum(axis=1)
    display_table(pivot.reset_index(), highlight="Total")


# ─── TAB 3: Player Stats ────────────────────────────────────────────────────────
elif tab == "Player Stats":
    st.title("📋 All Picks (Sorted by Score)")
    df = info[["Player","Pick","Team","Opponent","Score"]].sort_values("Score", ascending=True)

    # build a small HTML table so we can embed each logo image
    logo_map = logos.set_index("Team")["Logo"].to_dict()
    html_rows = []
    for _, r in df.iterrows():
        img = logo_map.get(r.Team, "")
        img_tag = f'<img src="{img}" width="24">' if img else r.Team
        html_rows.append({
            "Player": r.Player,
            "Pick":   r.Pick,
            "Team":   img_tag,
            "Opponent": r.Opponent,
            "Score":  r.Score
        })

    html = (
      pd.DataFrame(html_rows)
        .to_html(index=False, escape=False)
        .replace("<table","<table class='dataframe'")
    )
    # reuse our CSS from display_table
    st.markdown(
        """
        <style>
          .dataframe {width:100% !important; overflow-x:auto;}
          .dataframe th {
            background-color:#002060!important;
            color:white!important;
            text-align:center!important;
          }
          .dataframe td {
            text-align:center!important;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(html, unsafe_allow_html=True)


# ─── TAB 4: Recaps ───────────────────────────────────────────────────────────────
elif tab == "Recaps":
    st.title("📰 Weekly Recaps")
    recap_dir = Path("assets/recaps")
    if not recap_dir.exists():
        st.info("Drop your `Week 1 Recap.pdf`, `Week 2 Recap.pdf`, … into `assets/recaps/`.")
    else:
        for pdf in sorted(recap_dir.glob("Week *.pdf"), key=lambda p: p.stem):
            label = pdf.stem.replace("_"," ")
            st.markdown(f"- [{label}]({pdf.as_posix()})")


# ─── TAB 5: Past Results ────────────────────────────────────────────────────────
elif tab == "Past Results":
    st.title("📜 Past Winners (2017–2024)")
    for yr in [2017,2018,2019,2021,2022,2023,2024]:
        block = past.query("Year == @yr")[["Rank","Player","Score"]]
        if not block.empty:
            st.subheader(str(yr))
            display_table(block, highlight="Score")


# ─── TAB 6: Submission Form ─────────────────────────────────────────────────────
elif tab == "Submission Form":
    st.title("✍️ Submission Form")
    st.write("You can also submit via the embedded Google Form below:")
    st.components.v1.iframe(
        "https://docs.google.com/forms/d/e/1FAIpQLSdy_WqAQlK_0gPC1xwT2mQqQucHArM9Is8jbVH3l0bVMk-HKw/viewform?embedded=true",
        height=700,
        scrolling=True,
    )
