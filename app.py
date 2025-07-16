import streamlit as st
import pandas as pd
import altair as alt
from pathlib import Path
from matplotlib.colors import LinearSegmentedColormap

cmap_blue = LinearSegmentedColormap.from_list("blue_gray", ["#002060", "#d3d3d3"])
cmap_green = LinearSegmentedColormap.from_list("green_gray", ["#217346", "#e0f2e0"])

import itertools
import numpy as np

#---WEEK ORDER-----------------------------------
WEEK_ORDER = [f"Week {i}" for i in range(1, 17)] + ["Bowls"]

# ─── 1) Page & Theme Config ────────────────────────────────────────────────────
st.set_page_config(
    page_title="CFB Stat Game",
    layout="wide",
    initial_sidebar_state="collapsed"
)
# a blue→light-gray colormap for our conditional gradients
cmap = LinearSegmentedColormap.from_list("blue_gray", ["#002060", "#d3d3d3"])

# ─── 2) Utility: Responsive, Styled Table ───────────────────────────────────────
def display_table(
    df: pd.DataFrame,
    highlight: str = None,
    highlight_cols: list = None,
    bold_row: str = None,
    short_weeks: bool = False,
):
    base_css = [
        {"selector": "th", "props": [
            ("background-color", "#002060"),
            ("color", "white"),
            ("text-align", "center"),
            ("font-weight", "bold"),
            ("font-size", "14px"),
        ]},
        {"selector": "td", "props": [
            ("text-align", "center"),
            ("font-size", "13px"),
            ("padding", "4px 2px"),
        ]},
        {"selector": "table", "props": [
            ("width", "100%"),
            ("table-layout", "fixed"),
        ]},
    ]

    num_cols = df.select_dtypes(include="number").columns

    def fmt(val):
        try:
            if pd.isna(val): return ""
            return f"{int(val):,}"
        except Exception:
            return val

    styler = (
        df.style
        .set_table_styles(base_css)
        .format({col: fmt for col in num_cols})
        .hide(axis="index")
    )
    if short_weeks and "Week" in df.columns:
        def short_week_label(w):
            if w == "Bowls": return "BS"
            if isinstance(w, str) and w.startswith("Week "):
                return w.replace("Week ", "")
            return w
        styler.format({"Week": short_week_label})

    # ---- CONDITIONAL FORMATTING ONLY: ----
    # highlight_cols uses blue, highlight uses green
    if highlight_cols:
        for col in highlight_cols:
            if col in df.columns:
                styler = styler.background_gradient(cmap=cmap_blue, subset=[col])
    
    if highlight and highlight in df.columns:
        styler = styler.background_gradient(cmap=cmap_green, subset=[highlight])
        # For bold text only:
        styler = styler.set_properties(subset=[highlight], **{'font-weight': 'bold'})

    # Bold the Total row if present
    if bold_row and "Week" in df.columns:
        if bold_row in df["Week"].values:
            idx = df.index[df["Week"] == bold_row][0]
            styler = styler.set_properties(subset=pd.IndexSlice[idx, :], **{'font-weight': 'bold', 'background-color': '#dae3f3'})

    st.markdown(styler.to_html(), unsafe_allow_html=True)

# ─── 3) Load Your Excel Sheets ─────────────────────────────────────────────────
wb = Path("Stat Upload.xlsx")

# ---- Info sheet: header row is Excel row 2 (so header=1), then pick only the columns you need
info = pd.read_excel(wb, sheet_name="Info", header=1)
info = info[["Player", "Week", "Role", "Pick", "Team", "Opponent", "Score"]]
info["Player"] = info["Player"].str.strip()

# ---- Logos sheet: the real header labels live on Excel row 2 but row 1 is blank, so read header=None and promote row 1
_raw = pd.read_excel(wb, sheet_name="Logos", header=None)
_raw.columns = _raw.iloc[1]           # row index 1 has ["Team", "Image URL", NaN]
_logos = _raw.iloc[2:]                # drop the two header rows
_logos = _logos.loc[:, ~_logos.columns.isna()]  # drop the unnamed column
logos = _logos.rename(columns={"Image URL": "Logo"})[["Team", "Logo"]]

# ---- Past Winners sheet: header row is Excel row 2
past = pd.read_excel(wb, sheet_name="Past Winners", header=1)
past = past[["Year", "Rank", "Player", "Score"]]


# ─── 4) Sidebar Navigation ──────────────────────────────────────────────────────
tab = st.sidebar.radio(
    "Go to:",
    ["Standings", "Performance Breakdown", "Player Stats", "Recaps", "Past Results", "Submission Form"]
)


# ─── TAB 1: Standings ────────────────────────────────────────────────────────────
if tab == "Standings":
    st.title("🏆 Season Standings")
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

    info["CumulativeScore"] = info.groupby("Player")["Score"].cumsum()
    info["Week"] = info["Week"].astype(str)
    info["Player"] = info["Player"].str.strip()
    
    players = sorted(info["Player"].unique())
    weeks = WEEK_ORDER
    
    # Create grid for every (Player, Week) pair
    grid = pd.DataFrame(list(itertools.product(players, weeks)), columns=["Player", "Week"])
    tmp = (
        info[["Player", "Week", "CumulativeScore"]]
        .drop_duplicates(subset=["Player", "Week"], keep="last")
        .copy()
    )
    full_cum = pd.merge(grid, tmp, how="left", on=["Player", "Week"])
    full_cum["Week"] = pd.Categorical(full_cum["Week"], categories=WEEK_ORDER, ordered=True)
    full_cum = full_cum.sort_values(["Player", "Week"])
    full_cum["CumulativeScore"] = full_cum.groupby("Player")["CumulativeScore"].ffill()
    
    # NEW: Don't show ranks for weeks after player stopped playing
    last_played = (
        info.groupby("Player")["Week"]
        .apply(lambda x: max([WEEK_ORDER.index(str(w)) for w in x if str(w) in WEEK_ORDER]))
        .to_dict()
    )
    full_cum["week_idx"] = full_cum["Week"].apply(lambda w: WEEK_ORDER.index(str(w)) if not pd.isnull(w) else -1).astype(int)
    full_cum["LastPlayed"] = full_cum["Player"].map(last_played).astype(int)
    full_cum.loc[full_cum["week_idx"] > full_cum["LastPlayed"], "CumulativeScore"] = float('nan')
    
    # Compute ranks by cumulative score each week
    def compute_weekly_ranks(df, week_col="Week", group_col="Player", score_col="CumulativeScore"):
        out = []
        for week in WEEK_ORDER:
            week_df = df[df[week_col] == week].copy()
            week_df = week_df[week_df[score_col].notna()]
            week_df["Rank"] = week_df[score_col].rank(method="min", ascending=True)
            out.append(week_df)
        return pd.concat(out, ignore_index=True)
    
    rankings = compute_weekly_ranks(full_cum)
    rankings = rankings.sort_values(["Player", "Week"])
    rankings["Week"] = pd.Categorical(rankings["Week"], categories=WEEK_ORDER, ordered=True)
    rankings["week_idx"] = rankings["Week"].apply(lambda w: WEEK_ORDER.index(str(w)))

    chart = (
        alt.Chart(rankings)
        .mark_line(point=True)
        .encode(
            x=alt.X(
                "Week:O",
                sort=WEEK_ORDER,
                axis=alt.Axis(labelAngle=90, labelFontSize=8, titleFontSize=8)
            ),
            y=alt.Y(
                "Rank:Q",
                sort="descending",
                title=None,
                axis=alt.Axis(labelFontSize=8, titleFontSize=8),
                scale=alt.Scale(domain=[1, rankings["Rank"].max()])
            ),
            color=alt.Color(
                "Player:N",
                legend=alt.Legend(
                    orient="bottom",
                    direction="horizontal",
                    labelFontSize=8,
                    titleFontSize=8,
                    symbolLimit=30,
                    symbolSize=30,
                    columns=7
                )
            ),
            order=alt.Order("week_idx:O"),
        )
        .properties(height=400)
    )

    st.altair_chart(chart, use_container_width=True)

# ─── TAB 2: Performance Breakdown ────────────────────────────────────────────────
elif tab == "Performance Breakdown":
    st.title("📊 Performance Breakdown")

    # Player select (alphabetical)
    player = st.selectbox("Player", sorted(info["Player"].unique()))

    # Week select (chronological, based on what's in the data)
    week_options = [w for w in WEEK_ORDER if w in info["Week"].unique()]
    week = st.selectbox("Week", week_options)

    # ---- Picks Table (filtered by player & week) ----
    st.subheader(f"Picks: {player} — {week}")
    picks = info.query("Player == @player and Week == @week")

    DEFAULT_LOGO_URL = "https://a3.espncdn.com/combiner/i?img=%2Fi%2Fteamlogos%2Fncaa_conf%2F500%2F32.png"
    logo_map = logos.set_index("Team")["Logo"].to_dict()

    rows = []
    for _, r in picks.iterrows():
        team_logo = logo_map.get(r.Team, DEFAULT_LOGO_URL)
        opp_logo  = logo_map.get(r.Opponent, DEFAULT_LOGO_URL)
        team_html = f'<img src="{team_logo}" width="24">' if team_logo else ""
        opp_html  = f'<img src="{opp_logo}" width="24">' if opp_logo else ""
        rows.append({
            "Role": r.Role,
            "Pick": r.Pick,
            "Team": team_html,
            "Opponent": opp_html,
            "Score": r.Score,
        })
    df_html = pd.DataFrame(rows)
    html = (
        df_html.to_html(index=False, escape=False)
        .replace("<table","<table class='dataframe slim-table'")
    )
    # Slim, scroll-free table for picks
    st.markdown(
        """
        <style>
          .slim-table {
            width: 100% !important;
            table-layout: fixed;
            margin-bottom: 1em;
          }
          .slim-table th, .slim-table td {
            text-align: center !important;
            padding: 4px 2px !important;
            font-size: 13px;
            max-width: 60px;
            word-break: break-word;
            overflow: hidden;
          }
          .slim-table th {
            background-color:#002060!important;
            color:white!important;
          }
          .slim-table img {
            display: inline-block;
            vertical-align: middle;
            max-width: 24px;
            max-height: 24px;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(html, unsafe_allow_html=True)

    # ---- Full Season by Category Table (filtered by player only) ----
    st.subheader(f"Full Season by Category")

    player_info = info.query("Player == @player")
    pivot = (
        player_info.pivot_table(
            index="Week",
            columns="Role",
            values="Score",
            aggfunc="sum",
            fill_value=0
        )
    )
    for role in ["Passing", "Rushing", "Receiving", "Defensive"]:
        if role not in pivot.columns:
            pivot[role] = 0
    pivot = pivot[["Passing", "Rushing", "Receiving", "Defensive"]]
    pivot["Total"] = pivot.sum(axis=1)
    pivot = pivot.reindex(WEEK_ORDER)
    pivot.loc["Total"] = pivot.sum(numeric_only=True)

    # Format for display_table
    pivot_reset = pivot.reset_index()
    cols = ["Week"] + [col for col in pivot_reset.columns if col != "Week"]
    pivot_reset = pivot_reset[cols]
    pivot_reset = pivot_reset.replace({np.nan: ""})

    pivot_reset = pivot_reset.rename(columns={
        "Passing": "Pass",
        "Rushing": "Rush",
        "Receiving": "Rec",
        "Defensive": "Def",
        "Total": "Tot"
        
    display_table(
        pivot_reset,
        highlight="Tot",
        highlight_cols=["Pass", "Rush", "Rec", "Def"],
        bold_row="Total",
        short_weeks=True
    )
        
# ─── TAB 3: Player Stats ────────────────────────────────────────────────────────
elif tab == "Player Stats":
    st.title("📋 All Picks (Sorted by Score)")
    df = info[["Player","Pick","Team","Opponent","Score"]].sort_values("Score", ascending=True)

    # build an HTML table that embeds each logo image
    logo_map = logos.set_index("Team")["Logo"].to_dict()
    rows = []
    for _, r in df.iterrows():
        img = logo_map.get(r.Team, "")
        team_html = f'<img src="{img}" width="24">' if img else r.Team
        rows.append({
            "Player": r.Player,
            "Pick":    r.Pick,
            "Team":    team_html,
            "Opponent":r.Opponent,
            "Score":   r.Score
        })
    html = (
        pd.DataFrame(rows)
          .to_html(index=False, escape=False)
          .replace("<table","<table class='dataframe'")
    )
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
    recap_dir = Path("assets")/"recaps"
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
    st.write("Or submit via the embedded Google Form below:")
    st.components.v1.iframe(
        "https://docs.google.com/forms/d/e/1FAIpQLSdy_WqAQlK_0gPC1xwT2mQqQucHArM9Is8jbVH3l0bVMk-HKw/viewform?embedded=true",
        height=700,
        scrolling=True,
    )
