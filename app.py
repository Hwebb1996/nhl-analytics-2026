import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# --- CONFIG ---
st.set_page_config(page_title="NHL PROTOTYPE 2026", layout="wide", page_icon="🏒")

# Auto-refresh every 5 minutes to keep things updated
st_autorefresh(interval=300000, key="nhl_refresher")

# --- DATA ENGINE (PAGINATED) ---
@st.cache_data(ttl=3600)  # Cache for 1 hour to keep performance snappy
def fetch_all_skaters():
    all_players = []
    start_index = 0
    limit = 100
    
    # Simple status indicator for the user
    loading_placeholder = st.empty()
    loading_placeholder.info("🔍 Connecting to NHL API and fetching full roster...")

    while True:
        # 2026 API Endpoint for all skater summaries
        url = f"https://api.nhle.com/stats/rest/en/skater/summary?cayenneExp=seasonId=20252026&start={start_index}&limit={limit}"
        try:
            r = requests.get(url, timeout=15)
            res = r.json()
            data = res.get('data', [])
            total = res.get('total', 0)
            
            if not data:
                break
                
            all_players.extend(data)
            
            # Show progress in real-time
            loading_placeholder.info(f"📥 Loading players: {len(all_players)} / {total}")
            
            start_index += limit
            if len(all_players) >= total:
                break
        except Exception as e:
            st.error(f"⚠️ API Error at index {start_index}: {e}")
            break
            
    loading_placeholder.empty() # Remove loading text when done
    return pd.DataFrame(all_players)

def get_player_edge_stats(player_name):
    # Mock EDGE stats (High-level skating/shot data integration)
    return {
        "labels": ['Speed', 'Shot Power', 'Zone Time', 'Stick Handling', 'Faceoff %'],
        "values": [95, 82, 88, 98, 55] if "McDavid" in player_name else [70, 75, 65, 60, 50]
    }

# --- APP UI ---
st.title("🏒 NHL Full League Dashboard (2025-26)")
st.markdown("---")

df = fetch_all_skaters()

if not df.empty:
    # --- DYNAMIC COLUMN SAFETY ---
    # This prevents the 'team_col' KeyError by checking multiple possible names
    team_col = next((c for c in ['teamAbbrev', 'teamAbbreviation', 'teamName'] if c in df.columns), None)
    name_col = next((c for c in ['skaterFullName', 'fullName'] if c in df.columns), 'skaterFullName')

    # --- SIDEBAR FILTERS ---
    st.sidebar.header("Roster Controls")
    
    # Search Box for 800+ players
    search_query = st.sidebar.text_input("🔍 Search Player Name", "")
    
    # Team Multiselect
    if team_col:
        team_list = sorted(df[team_col].unique())
        selected_teams = st.sidebar.multiselect("Select Teams", team_list, default=team_list)
    else:
        selected_teams = []

    # Points Slider
    max_pts = int(df['points'].max()) if 'points' in df.columns else 100
    min_pts = st.sidebar.slider("Minimum Points", 0, max_pts, 0)

    # --- APPLY FILTERS ---
    mask = (df['points'] >= min_pts)
    if team_col and selected_teams:
        mask = mask & (df[team_col].isin(selected_teams))
    if search_query:
        mask = mask & (df[name_col].str.contains(search_query, case=False))
    
    filtered_df = df[mask].copy()

    # --- TOP METRICS ---
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Skaters", len(df))
    col2.metric("Filtered Set", len(filtered_df))
    col3.metric("League Avg Pts", round(df['points'].mean(), 1) if 'points' in df.columns else 0)

    # --- TABS ---
    tab1, tab2, tab3 = st.tabs(["📊 Leaderboard", "🎯 EDGE Analysis", "🔥 Scoring Heatmaps"])

    with tab1:
        st.subheader("Performance Table")
        cols_to_show = [name_col, team_col, 'positionCode', 'gamesPlayed', 'goals', 'assists', 'points']
        # Filter only existing columns
        valid_cols = [c for c in cols_to_show if c in filtered_df.columns]
        st.dataframe(
            filtered_df[valid_cols].sort_values(by='points', ascending=False), 
            use_container_width=True,
            height=600
        )

    with tab2:
        if not filtered_df.empty:
            p_name = st.selectbox("Select Player for Analysis", filtered_df[name_col].unique())
            stats = get_player_edge_stats(p_name)
            
            fig = go.Figure(data=go.Scatterpolar(r=stats['values'], theta=stats['labels'], fill='toself', line_color='#1d4ed8'))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Use the sidebar filters to find a player.")

    with tab3:
        # High-density scoring zones
        fig_heat = go.Figure(go.Histogram2dContour(
            x=[82, 85, 90, 75, 88, 92, 70, 85, 87], y=[0, 5, -5, 12, -2, 3, -15, 2, -1], 
            colorscale='YlOrRd', name="Density", nbinsx=20, nbinsy=20
        ))
        fig_heat.update_layout(
            xaxis=dict(range=[0, 100], title="Ice Length"), 
            yaxis=dict(range=[-42.5, 42.5], title="Ice Width"), 
            template="plotly_white", 
            title="League Scoring Intensity (Offensive Zone)"
        )
        st.plotly_chart(fig_heat, use_container_width=True)

else:
    st.error("❌ Data Source Error: The NHL API returned an empty list. Try refreshing in a moment.")
