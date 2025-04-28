import streamlit as st
import pandas as pd
import json
import io
from google.cloud import storage
import os

# --- Load GCS credentials from Streamlit secrets ---
from google.oauth2 import service_account

gcs_creds = service_account.Credentials.from_service_account_info(dict(st.secrets["gcs"]))
gcs_bucket = st.secrets["gcs"]["bucket"]

# --- Helper: GCS client ---
def get_gcs_client():
    return storage.Client(credentials=gcs_creds)

# --- Helper: List JSON files in GCS bucket ---
def list_gcs_json_files(prefix=""):
    client = get_gcs_client()
    bucket = client.bucket(gcs_bucket)
    blobs = bucket.list_blobs(prefix=prefix)
    return [blob.name for blob in blobs if blob.name.endswith(".json")]

# --- Helper: Download JSON file from GCS ---
def load_gcs_json(blob_name):
    client = get_gcs_client()
    bucket = client.bucket(gcs_bucket)
    blob = bucket.blob(blob_name)
    data = blob.download_as_bytes()
    return json.load(io.BytesIO(data))

# --- Load car and track metadata ---
@st.cache_data
def load_metadata():
    # Adjust filenames/paths as needed
    cars = pd.read_csv("cars.csv")
    tracks = pd.read_csv("tracks.csv")
    return cars, tracks

cars_df, tracks_df = load_metadata()

# --- UI: Select session JSON file ---
st.sidebar.title("Session Selection")
json_files = list_gcs_json_files()
selected_json = st.sidebar.selectbox("Select a race session", json_files)

# --- Load selected session data ---
if selected_json:
    session_data = load_gcs_json(selected_json)
    # Assume session_data is a list of dicts, get car/track from first entry
    first_entry = session_data[0]
    car_code = first_entry.get("car_code") or first_entry.get("car") or ""
    track_code = first_entry.get("track_code") or first_entry.get("track") or ""

    # --- Filter car and track info ---
    car_info = cars_df[cars_df['Code'] == car_code].iloc[0] if car_code in cars_df['Code'].values else None
    track_info = tracks_df[tracks_df['Code'] == track_code].iloc[0] if track_code in tracks_df['Code'].values else None

    st.sidebar.markdown("### Car Used")
    if car_info is not None:
        st.sidebar.write(car_info)
    else:
        st.sidebar.write("Unknown car code:", car_code)

    st.sidebar.markdown("### Track Used")
    if track_info is not None:
        st.sidebar.write(track_info)
    else:
        st.sidebar.write("Unknown track code:", track_code)
else:
    st.warning("No session JSON selected.")

# --- Make session_data, car_info, track_info available for all tabs below ---
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt

# --- Convert session_data to DataFrame for analysis ---
if selected_json and session_data:
    df = pd.DataFrame(session_data)
    # Ensure timestamp is datetime if present
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
else:
    df = pd.DataFrame()

# --- Streamlit Tabs ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Single Race Analysis",
    "Leaderboards",
    "Lap/Car Comparison",
    "Average Lap Times",
    "Advanced Visualizations"
])
with tab1:
    st.header("Single Race Analysis")
    if df.empty:
        st.info("Select a session to view race analysis.")
    else:
        # Dropdowns for lap selection (if multiple laps)
        laps = df['current_lap'].unique() if 'current_lap' in df.columns else [0]
        selected_lap = st.selectbox("Select Lap", sorted(laps))
        lap_df = df[df['current_lap'] == selected_lap] if 'current_lap' in df.columns else df

        st.subheader("Speed vs. Time")
        fig = px.line(lap_df, x='timestamp', y='car_speed', title="Car Speed Over Time")
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Throttle, Brake, and Steering")
        fig = go.Figure()
        if 'throttle' in lap_df.columns:
            fig.add_trace(go.Scatter(x=lap_df['timestamp'], y=lap_df['throttle'], name='Throttle'))
        if 'brake' in lap_df.columns:
            fig.add_trace(go.Scatter(x=lap_df['timestamp'], y=lap_df['brake'], name='Brake'))
        if 'steering' in lap_df.columns:
            fig.add_trace(go.Scatter(x=lap_df['timestamp'], y=lap_df['steering'], name='Steering'))
        fig.update_layout(title="Inputs Over Time", xaxis_title="Time", yaxis_title="Value")
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Track Map (Driving Line)")
        if {'position_x', 'position_y'}.issubset(lap_df.columns):
            fig = px.scatter(lap_df, x='position_x', y='position_y', color='car_speed',
                             title="Driving Line (colored by speed)", color_continuous_scale='Viridis')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No position data available for driving line.")
with tab2:
    st.header("Leaderboards")
    # For demo: aggregate all available sessions in GCS
    st.info("Showing leaderboard for all available sessions in the bucket.")
    leaderboard = []
    for file in json_files:
        data = load_gcs_json(file)
        if not data: continue
        d = pd.DataFrame(data)
        if 'best_lap' in d.columns and d['best_lap'].min() > 0:
            best_lap = d['best_lap'].min()
        elif 'lap_time' in d.columns and d['lap_time'].min() > 0:
            best_lap = d['lap_time'].min()
        else:
            continue
        car_code = d.iloc[0].get("car_code") or d.iloc[0].get("car") or ""
        track_code = d.iloc[0].get("track_code") or d.iloc[0].get("track") or ""
        car_name = cars_df[cars_df['Code'] == car_code]['Name'].values[0] if car_code in cars_df['Code'].values else car_code
        track_name = tracks_df[tracks_df['Code'] == track_code]['Name'].values[0] if track_code in tracks_df['Code'].values else track_code
        leaderboard.append({
            "Session": file,
            "Car": car_name,
            "Track": track_name,
            "Best Lap (s)": best_lap
        })
    if leaderboard:
        lb_df = pd.DataFrame(leaderboard)
        selected_track = st.selectbox("Filter by Track", ["All"] + sorted(lb_df['Track'].unique()))
        if selected_track != "All":
            lb_df = lb_df[lb_df['Track'] == selected_track]
        st.dataframe(lb_df.sort_values("Best Lap (s)"), use_container_width=True)
    else:
        st.info("No leaderboard data available.")
with tab3:
    st.header("Lap/Car Comparison")
    st.info("Compare up to 4 laps (from different sessions/cars) on the same track.")

    # Select up to 4 sessions
    compare_files = st.multiselect("Select up to 4 sessions to compare", json_files, max_selections=4)
    compare_laps = []
    for file in compare_files:
        data = load_gcs_json(file)
        if not data: continue
        d = pd.DataFrame(data)
        car_code = d.iloc[0].get("car_code") or d.iloc[0].get("car") or ""
        car_name = cars_df[cars_df['Code'] == car_code]['Name'].values[0] if car_code in cars_df['Code'].values else car_code
        track_code = d.iloc[0].get("track_code") or d.iloc[0].get("track") or ""
        track_name = tracks_df[tracks_df['Code'] == track_code]['Name'].values[0] if track_code in tracks_df['Code'].values else track_code
        for lap in d['current_lap'].unique():
            compare_laps.append({
                "Session": file,
                "Car": car_name,
                "Track": track_name,
                "Lap": lap,
                "Data": d[d['current_lap'] == lap]
            })
    if compare_laps:
        selected_laps = st.multiselect(
            "Select up to 4 laps to compare",
            options=[f"{c['Car']} | {c['Track']} | Lap {c['Lap']} | {c['Session']}" for c in compare_laps],
            max_selections=4
        )
        # Plot driving lines
        st.subheader("Driving Line Comparison")
        fig = go.Figure()
        for c in compare_laps:
            label = f"{c['Car']} | Lap {c['Lap']}"
            if f"{c['Car']} | {c['Track']} | Lap {c['Lap']} | {c['Session']}" in selected_laps:
                d = c['Data']
                if {'position_x', 'position_y'}.issubset(d.columns):
                    fig.add_trace(go.Scatter(
                        x=d['position_x'], y=d['position_y'],
                        mode='lines', name=label,
                        line=dict(width=3)
                    ))
        fig.update_layout(title="Driving Line Comparison", xaxis_title="X", yaxis_title="Y")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Select sessions to compare laps.")
with tab4:
    st.header("Average Lap Times Per Car on Track")
    # Aggregate all sessions
    avg_laps = []
    for file in json_files:
        data = load_gcs_json(file)
        if not data: continue
        d = pd.DataFrame(data)
        car_code = d.iloc[0].get("car_code") or d.iloc[0].get("car") or ""
        car_name = cars_df[cars_df['Code'] == car_code]['Name'].values[0] if car_code in cars_df['Code'].values else car_code
        track_code = d.iloc[0].get("track_code") or d.iloc[0].get("track") or ""
        track_name = tracks_df[tracks_df['Code'] == track_code]['Name'].values[0] if track_code in tracks_df['Code'].values else track_code
        if 'lap_time' in d.columns:
            avg_lap = d['lap_time'].mean()
            avg_laps.append({
                "Car": car_name,
                "Track": track_name,
                "Avg Lap Time (s)": avg_lap
            })
    if avg_laps:
        avg_df = pd.DataFrame(avg_laps)
        st.dataframe(avg_df.sort_values("Avg Lap Time (s)"), use_container_width=True)
        st.bar_chart(avg_df.set_index("Car")["Avg Lap Time (s)"])
    else:
        st.info("No average lap time data available.")
with tab5:
    st.header("Advanced Visualizations & Insights")
    st.info("Heatmaps, brake/accel/coast maps, and more.")

    if not df.empty and {'position_x', 'position_y', 'car_speed'}.issubset(df.columns):
        st.subheader("Speed Heatmap on Track")
        fig = px.density_heatmap(
            df, x='position_x', y='position_y', z='car_speed',
            histfunc='avg', nbinsx=50, nbinsy=50,
            color_continuous_scale='Turbo',
            title="Speed Heatmap"
        )
        st.plotly_chart(fig, use_container_width=True)

    if not df.empty and {'brake', 'throttle', 'position_x', 'position_y'}.issubset(df.columns):
        st.subheader("Brake/Coast/Accelerate Map")
        # Classify each point
        def classify(row):
            if row['brake'] > 0.1:
                return 'Brake'
            elif row['throttle'] > 0.1:
                return 'Accelerate'
            else:
                return 'Coast'
        df['action'] = df.apply(classify, axis=1)
        fig = px.scatter(
            df, x='position_x', y='position_y', color='action',
            title="Brake/Coast/Accelerate Map",
            color_discrete_map={'Brake': 'red', 'Accelerate': 'green', 'Coast': 'yellow'}
        )
        st.plotly_chart(fig, use_container_width=True)

    # Add more creative visualizations as needed!
