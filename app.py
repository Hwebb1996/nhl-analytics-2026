import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# --- CONFIG ---
st.set_page_config(page_title="NHL PROTOTYPE 2026", layout="wide")
# Auto-refresh every 60 seconds to keep data fresh without hitting rate limits
st_autorefresh(interval=60000, key="nhl_refresher")

# --- DATA ENGINE ---
@st.cache_data(ttl=300) # Cache for 5 mins
def fetch_nhl_data():
    # Fetching summary stats for the 2025-26 Season
    url = "https://api.nhle.com/stats/rest/en/skater/summary?cayenneExp=seasonId=20252026"
    try:
        r = requests.get(url)
        return pd.DataFrame(r.json()['data'])
    except:
        return pd.DataFrame()

def get_player_edge_stats(player_name):
    # Mock EDGE stats (In production, use the /player/{id}/landing endpoint)
    return {
        "labels": ['Speed', 'Shot Power', 'Zone Time', 'Stick Handling', 'Faceoff %'],
        "values": [92, 85, 78, 95, 60] if "McDavid" in player_name else [70, 75, 60, 65, 50]
    }

# --- UI HEADER ---
st.title("🏒 NHL Elite Performance Dashboard (v2026.1)")
st.markdown("---")

df = fetch_nhl_data()

if not df.empty:
    # --- SIDEBAR FILTERS ---
    st.sidebar.header("Global Filters")
    team_list = sorted(df['teamAbbrev'].unique())
    selected_team = st.sidebar.multiselect("Teams", team_list, default=["EDM", "NYR", "TOR"])
    
    min_pts = st.sidebar.slider("Minimum Points", 0, 150, 20)
    
    # --- DATA PROCESSING ---
    filtered_df = df[(df['teamAbbrev'].isin(selected_team)) & (df['points'] >= min_pts)]

    # --- MAIN TABS ---
    tab1, tab2, tab3 = st.tabs(["📊 Player Leaderboard", "🎯 EDGE Analytics", "🔥 Scoring Heatmaps"])

    with tab1:
        st.subheader("Active Performance Metrics")
        st.dataframe(filtered_df[['skaterFullName', 'teamAbbrev', 'goals', 'assists', 'points', 'gamesPlayed']], use_container_width=True)

    with tab2:
        col_sel, col_viz = st.columns([1, 2])
        with col_sel:
            player_to_viz = st.selectbox("Select Player for EDGE Card", filtered_df['skaterFullName'])
            edge_data = get_player_edge_stats(player_to_viz)
        
        with col_viz:
            fig = go.Figure(data=go.Scatterpolar(
                r=edge_data['values'],
                theta=edge_data['labels'],
                fill='toself',
                line_color='#FF4B4B'
            ))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=False)
            st.plotly_chart(fig)

    with tab3:
        st.subheader("Shot Density & Goal Heatmap")
        # Creating a simulated heatmap for the prototype visualization
        # In a full build, this uses the x,y coordinates from the play-by-play API
        shot_x = [70, 85, 90, 75, 88, 92, 65, 77, 85]
        shot_y = [-10, 5, 2, -15, 0, 12, 20, -5, -2]
        
        fig_heat = go.Figure(go.Histogram2dContour(
            x=shot_x, y=shot_y, colorscale='Reds', name="Density"
        ))
        # Adding a star for the "Goal"
        fig_heat.add_trace(go.Scatter(x=[88], y=[0], mode='markers', marker=dict(symbol='star', size=15, color='gold')))
        
        fig_heat.update_layout(
            xaxis=dict(range=[0, 100], title="Ice X"),
            yaxis=dict(range=[-42.5, 42.5], title="Ice Y"),
            shapes=[dict(type="rect", x0=89, y0=-3, x1=90, y1=3, line=dict(color="blue"))] # The Net
        )
        st.plotly_chart(fig_heat, use_container_width=True)

else:
    st.error("Connection to NHL API failed. Check your internet or endpoint status.")
