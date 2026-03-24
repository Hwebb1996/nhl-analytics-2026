import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# --- CONFIG ---
st.set_page_config(page_title="NHL PROTOTYPE 2026", layout="wide", page_icon="🏒")

# Auto-refresh every 5 minutes to keep things smooth
st_autorefresh(interval=300000, key="nhl_refresher")

# --- DATA ENGINE (PAGINATED) ---
@st.cache_data(ttl=3600)  # Cache for 1 hour since full rosters don't change fast
def fetch_all_skaters():
    all_players = []
    start_index = 0
    limit = 100
    
    # Placeholder for a loading message in the UI
    status_text = st.empty()
    status_text.text("Connecting to NHL API...")

    while True:
        url = f"https://api.nhle.com/stats/rest/en/skater/summary?cayenneExp=seasonId=20252026&start={start_index}&limit={limit}"
        try:
            r = requests.get(url, timeout=10)
            res = r.json()
            data = res.get('data', [])
            total = res.get('total', 0)
            
            if not data:
                break
                
            all_players.extend(data)
            status_text.text(f"📥 Loading players: {len(all_players)} / {total}")
            
            start_index += limit
            if len(all_players) >= total:
                break
        except Exception as e:
            st.error(f"Error fetching data: {e}")
            break
            
    status_text.empty() # Remove loading text when done
    return pd.DataFrame(all_players)

def get_player_edge_stats(player_name):
    # Mock EDGE stats (Placeholder for NHL EDGE tracking integration)
    return {
        "labels": ['Speed', 'Shot Power', 'Zone Time', 'Stick Handling', 'Faceoff %'],
        "values": [95, 82, 88, 98, 55] if "McDavid" in player_name else [70, 75, 65, 60, 50]
    }

# --- APP UI ---
st.title("🏒 NHL Full League Analytics (2025-26)")
st.markdown("---")

df = fetch_all_skaters()

if not df.empty:
    # --- DYNAMIC COLUMN DETECTOR ---
    name_col = next((c for c in ['skaterFullName', 'fullName'] if c in df.columns), 'skaterFullName')
    team_col = next((c for c in ['teamAbbrev', 'teamAbbreviation'] if c in df.columns), 'teamAbbrev')

    # --- SIDEBAR FILTERS ---
    st.sidebar.header("Filter Roster")
    
    # 1. Search Box
    search_query = st.sidebar.text_input("🔍 Search Player Name", "")
    
    # 2. Team Filter
    team_list = sorted(df[team_col].unique())
    selected_teams = st.sidebar.multiselect("Select Teams", team_list, default=team_list)
    
    # 3. Points Filter
    max_pts = int(df['points'].max())
    min_pts = st.sidebar.slider("Minimum Points", 0, max_pts, 0)

    # --- APPLY FILTERS ---
    mask = (df['points'] >= min_pts) & (df[team_col].isin(selected_teams))
    if search_query:
        mask = mask & (df[name_col].str.contains(search_query, case=False))
    
    filtered_df = df[mask].copy()

    # --- TOP METRICS ---
    m1, m2, m3 = st.columns(3)
    m1.metric("Players Loaded", len(df))
    m2.metric("Filtered Set", len(filtered_df))
    m3.metric("League Avg Points", round(df['points'].mean(), 1))

    # --- TABS ---
    tab1, tab2, tab3 = st.tabs(["📊 Full Leaderboard", "🎯 EDGE Player Card", "🔥 Scoring Zones"])

    with tab1:
        st.dataframe(
            filtered_df[[name_col, team_col, 'positionCode', 'gamesPlayed', 'goals', 'assists', 'points']]
            .sort_values(by='points', ascending=False), 
            use_container_width=True,
            height=500
        )

    with tab2:
        if not filtered_df.empty:
            p_name = st.selectbox("Analyze Player", filtered_df[name_col].unique())
            stats = get_player_edge_stats(p_name)
            
            fig = go.Figure(data=go.Scatterpolar(r=stats['values'], theta=stats['labels'], fill='toself', line_color='#1d4ed8'))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No players found with current filters.")

    with tab3:
        # Static heatmap for prototype; update with API x,y coords for live tracking
        fig_heat = go.Figure(go.Histogram2dContour(
            x=[80, 85, 90, 70, 88, 92, 75], y=[0, 5, -5, 10, -2, 3, -12], 
            colorscale='YlOrRd', name="Density"
        ))
        fig_heat.update_layout(xaxis=dict(range=[0, 100]), yaxis=dict(range=[-42.5, 42.5]), template="plotly_white", title="Scoring Intensity")
        st.plotly_chart(fig_heat, use_container_width=True)

else:
    st.error("Could not load player data. Please check your NHL API connection.")
