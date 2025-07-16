import streamlit as st
import pandas as pd
import altair as alt
import streamlit.components.v1 as components

# 1) Page config
st.set_page_config(
    page_title="CFB Stat Game",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2) Load all sheets at once
xls = pd.read_excel("data/Stat Upload.xlsx", sheet_name=None)

info           = xls["Info"]            # week-by-week picks & scores
logos          = xls["Logos"]           # (if you grab URLs or local filenames)
past_winners   = xls["Past Winners"]
# …and any other sheets: Expected Wins, Charts, Recaps, etc.

# 3) Sidebar tabs
tab = st.sidebar.radio(
    "Navigate",
    ["Standings", "Performance Breakdown", "Player Stats", "Recaps", "Past Results", "Submission Form"],
    index=0
)

# --------------- TAB: Standings ---------------
if tab == "Standings":
    # build a standings table
    df = info.groupby("Player")["Score"].sum().reset_index()
    df = df.sort_values("Score", ascending=True)  # lowest = rank 1
    df["Rank"] = range(1, len(df)+1)
    df["Pts. From 1st"] = df["Score"] - df.iloc[0]["Score"]
    
    # conditional formatting: e.g. using st_aggrid for mobile
    from st_aggrid import AgGrid, GridOptionsBuilder

    gb = GridOptionsBuilder.from_dataframe(df[["Rank","Player","Score","Pts. From 1st"]])
    gb.configure_column("Score", type=["numericColumn","numberColumnFilter"], 
                        cellStyle=cellStyleJs=["value < 0 ? {'color':'white','background':'#002060'} : {'color':'black','background':'#d3d3d3'}"])
    gridOptions = gb.build()
    AgGrid(df, gridOptions=gridOptions, fit_columns_on_grid_load=True)

    # bump chart: Rankings by Week
    # we need a long-form DataFrame: one row per Player×Week with their rank
    week_ranks = (
      info.pivot_table(index="Week", 
                       columns="Player", 
                       values="Score", 
                       aggfunc="sum")
          .rank(axis=1, method="first", ascending=True)
          .reset_index()
          .melt(id_vars="Week", var_name="Player", value_name="Rank")
    )
    chart = alt.Chart(week_ranks).mark_line(point=True).encode(
        x=alt.X("Week:O", axis=alt.Axis(labelAngle=90)),
        y=alt.Y("Rank:Q", sort="descending"),  # first place=1 at top
        color="Player:N",
        order=alt.Order("Rank:Q")
    ).properties(height=300)
    st.altair_chart(chart, use_container_width=True)

# --------------- TAB: Performance Breakdown ---------------
elif tab == "Performance Breakdown":
    player = st.selectbox("Player", sorted(info["Player"].unique()))
    week   = st.selectbox("Week", sorted(info["Week"].unique()))
    # filter for picks
    picks = info[(info.Player==player)&(info.Week==week)]
    st.table(picks[["Category","Player","Team","Opponent","Score"]])
    # full-season table with same styling as above
    season = info.groupby("Week")[["Passing","Rushing","Receiving","Defensive"]].sum()
    season["Total"] = season.sum(axis=1)
    # …apply same color scales as Score above…

# --------------- TAB: Player Stats ---------------
elif tab == "Player Stats":
    df = info[["Player","Pick","Team","Opponent","Score"]]
    df = df.sort_values("Score", ascending=True)
    # if you have logo URLs, you can do:
    # df["Team"] = df["Team"].apply(lambda url: f"![logo]({url})")
    st.table(df.style.background_gradient(subset=["Score"], cmap="Blues"))

# --------------- TAB: Recaps ---------------
elif tab == "Recaps":
    st.write("### Weekly Recaps")
    for pdf in sorted((st.sidebar.resource("assets/recaps")).glob("Week *.pdf")):
        week = pdf.stem
        st.markdown(f"- [{week}]({pdf.as_posix()})")

# --------------- TAB: Past Results ---------------
elif tab == "Past Results":
    for year in [2017,2018,2019,2021,2022,2023,2024]:
        df = past_winners[past_winners.Year==year]
        df = df.sort_values("Score", ascending=True)
        st.write(f"#### {year}")
        st.table(df[["Rank","Player","Score"]])

# --------------- TAB: Submission Form ---------------
elif tab == "Submission Form":
    st.write("### Enter Your Picks")
    components.iframe(
        "https://docs.google.com/forms/d/e/1FAIpQLSdy_WqAQlK_0gPC1xwT2mQqQucHArM9Is8jbVH3l0bVMk-HKw/viewform?embedded=true",
        width="100%",
        height=800
    )
