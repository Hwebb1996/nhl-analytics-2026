import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# --- CONFIG ---
st.set_page_config(page_title="NHL PROTOTYPE 2026", layout="wide", page_icon="🏒")

# Auto-refresh every 60 seconds to keep data live
st_autorefresh(interval=60000, key="nhl_refresher")

# --- DATA ENGINE ---
@st.cache_data(ttl=300)
def fetch_nhl_data():
    # Fetching summary stats for the 2025-26 Season
    url = "https://api.nhle.com/stats/rest/en/skater/summary?cayenneExp=seasonId=20252026"
    try:
        r = requests.get(url, timeout=10)
        data = r.json().get('data', [])
        if not data:
            return pd.DataFrame()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"API Connection Error: {e}")
        return pd.DataFrame()

def get_player_edge_stats(player_name):
    # Mock EDGE stats (Placeholder for NHL EDGE Percentile API)
    return {
        "labels": ['Speed', 'Shot Power', 'Zone Time', 'Stick Handling', 'Faceoff %'],
        "values": [92, 85, 78, 95, 60] if "McDavid" in player_name else [70, 75, 82, 65, 50]
    }

# --- APP UI ---
st.title("🏒 NHL Elite Performance Dashboard (v2026.1)")
st.markdown("---")

df = fetch_nhl_data()

if not df.empty:
    # --- 1. DEFENSIVE COLUMN CHECKING ---
    # We look for whatever the NHL decided to name the 'team' column today
    team_cols = ['teamAbbrev', 'teamAbbreviation', 'teamName']
    team_col = next((col for col in team_cols if col in df.columns), None)
    
    name_cols = ['skaterFullName', 'fullName', 'lastName']
    name_col = next((col for col in name_cols if col in df.columns), 'skaterFullName')

    # --- 2. SIDEBAR FILTERS ---
    st.sidebar.header("Global Filters")
    
    if team_col:
        team_list = sorted(df[team_col].unique())
        selected_teams = st.sidebar.multiselect("Select Teams", team_list, default=team_list[:3])
    else:
        selected_teams = []
        st.sidebar.warning("Team data unavailable")

    min_pts = st.sidebar.slider("Minimum Points Threshold", 0, int(df['points'].max()), 10)

    # --- 3. FILTER LOGIC ---
    mask = df['points'] >= min_pts
    if selected_teams and team_col:
        mask = mask & df[team_col].isin(selected_teams)
    
    filtered_df = df[mask].copy()

    # --- 4. MAIN TABS ---
    tab1, tab2, tab3 = st.tabs(["📊 Leaderboard", "🎯 EDGE Analytics", "🔥 Scoring Heatmaps"])

    with tab1:
        st.subheader("Active Performance Metrics")
        display_cols = [name_col, team_col, 'goals', 'assists', 'points', 'gamesPlayed']
        # Only show columns that actually exist
        final_cols = [c for c in display_cols if c in filtered_df.columns]
        st.dataframe(filtered_df[final_cols].sort_values(by='points', ascending=False), use_container_width=True)

    with tab2:
        if not filtered_df.empty:
            col_sel, col_viz = st.columns([1, 2])
            with col_sel:
                player_to_viz = st.selectbox("Select Player for EDGE Card", filtered_df[name_col])
                edge_data = get_player_edge_stats(player_to_viz)
            
            with col_viz:
                fig = go.Figure(data=go.Scatterpolar(
                    r=edge_data['values'],
                    theta=edge_data['labels'],
                    fill='toself',
                    line_color='#FF4B4B'
                ))
                fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Adjust filters to select a player for analysis.")

    with tab3:
        st.subheader("Shot Density & Goal Heatmap")
        # Simulated heatmap data (mapping to offensive zone)
        # In full production, pull x,y from api-web.nhle.com/v1/gamecenter/{id}/play-by-play
        shot_x = [70, 85, 90, 75, 88, 92, 65, 77, 85, 80, 82]
        shot_y = [-10, 5, 2, -15, 0, 12, 20, -5, -2, 8, -8]
        
        fig_heat = go.Figure(go.Histogram2dContour(
            x=shot_x, y=shot_y, colorscale='Reds', name="Density", nbinsx=20, nbinsy=20
        ))
        
        # Overlay a "Goal" star
        fig_heat.add_trace(go.Scatter(x=[88], y=[0], mode='markers', marker=dict(symbol='star', size=15, color='gold', line=dict(width=1, color='black'))))
        
        fig_heat.update_layout(
            xaxis=dict(range=[0, 100], title="Ice X (Feet)", showgrid=False),
            yaxis=dict(range=[-42.5, 42.5], title="Ice Y (Feet)", showgrid=False),
            template="plotly_white",
            shapes=[dict(type="rect", x0=89, y0=-3, x1=90, y1=3, line=dict(color="blue", width=3))] # Net
        )
        st.plotly_chart(fig_heat, use_container_width=True)

else:
    st.error("Data Source Offline: The NHL API did not return any skater stats.")
