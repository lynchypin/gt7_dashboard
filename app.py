import streamlit as st
import pandas as pd
import json
import io
from google.cloud import storage
import os

from google.oauth2 import service_account

gcs_creds = service_account.Credentials.from_service_account_info(dict(st.secrets["gcs"]))
gcs_bucket = st.secrets["gcs"]["bucket"]

def get_gcs_client():
    return storage.Client(credentials=gcs_creds)

def list_gcs_json_files(prefix=""):
    client = get_gcs_client()
    bucket = client.bucket(gcs_bucket)
    blobs = bucket.list_blobs(prefix=prefix)
    return [blob.name for blob in blobs if blob.name.endswith(".json")]

def load_gcs_json(blob_name):
    client = get_gcs_client()
    bucket = client.bucket(gcs_bucket)
    blob = bucket.blob(blob_name)
    data = blob.download_as_bytes()
    return json.load(io.BytesIO(data))

@st.cache_data
def load_metadata():
    cars = pd.read_csv("cars.csv")
    tracks = pd.read_csv("tracks.csv")
    return cars, tracks

cars_df, tracks_df = load_metadata()

st.sidebar.title("Session Selection")
json_files = list_gcs_json_files()
selected_json = st.sidebar.selectbox("Select a race session", json_files)

if selected_json:
    session_data = load_gcs_json(selected_json)
    first_entry = session_data[0]
    car_code = first_entry.get("car_code") or first_entry.get("car_id") or first_entry.get("car") or ""
    track_code = first_entry.get("track_code") or first_entry.get("track_id") or first_entry.get("track") or ""

    car_info = cars_df[cars_df['ID'] == car_code].iloc[0] if car_code in cars_df['ID'].values else None
    track_info = tracks_df[tracks_df['ID'] == track_code].iloc[0] if track_code in tracks_df['ID'].values else None

    st.sidebar.markdown("### Car Used")
    if car_info is not None:
        st.sidebar.write(car_info['ShortName'])
    else:
        st.sidebar.write("Unknown car code:", car_code)

    st.sidebar.markdown("### Track Used")
    if track_info is not None:
        st.sidebar.write(track_info['Name'])
    else:
        st.sidebar.write("Unknown track code:", track_code)
else:
    st.warning("No session JSON selected.")

import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt

if selected_json and session_data:
    df = pd.DataFrame(session_data)
    if 'time_on_track' in df.columns:
        df['time_on_track_seconds'] = pd.to_timedelta(df['time_on_track']).dt.total_seconds()
else:
    df = pd.DataFrame()

# Tabs: Single Race, Inputs, Driving Line, Heatmaps, Car/Track, Advanced, Extra
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "Speed & Laps",
    "Inputs",
    "Driving Line",
    "Heatmaps",
    "Gear/RPM/Fuel",
    "Tyre & Suspension",
    "Elevation & Histogram",
    "Comparison"
])

with tab1:
    st.header("Speed & Laps")
    if df.empty:
        st.info("Select a session to view race analysis.")
    else:
        laps = df['current_lap'].unique() if 'current_lap' in df.columns else [0]
        selected_lap = st.selectbox("Select Lap", sorted(laps))
        lap_df = df[df['current_lap'] == selected_lap] if 'current_lap' in df.columns else df
        if 'time_on_track' in lap_df.columns:
            lap_df['time_on_track_seconds'] = pd.to_timedelta(lap_df['time_on_track']).dt.total_seconds()

        st.subheader("Speed vs. Time")
        if 'time_on_track_seconds' in lap_df.columns:
            fig = px.line(lap_df, x='time_on_track_seconds', y='car_speed', title="Car Speed Over Time")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No time data available for speed plot.")

with tab2:
    st.header("Inputs: Throttle & Brake")
    if df.empty:
        st.info("Select a session to view input analysis.")
    else:
        laps = df['current_lap'].unique() if 'current_lap' in df.columns else [0]
        selected_lap = st.selectbox("Select Lap (Inputs)", sorted(laps), key="inputs_lap")
        lap_df = df[df['current_lap'] == selected_lap] if 'current_lap' in df.columns else df
        if 'time_on_track' in lap_df.columns:
            lap_df['time_on_track_seconds'] = pd.to_timedelta(lap_df['time_on_track']).dt.total_seconds()

        st.subheader("Throttle, Brake Over Time")
        fig = go.Figure()
        if 'throttle' in lap_df.columns:
            fig.add_trace(go.Scatter(x=lap_df['time_on_track_seconds'], y=lap_df['throttle'], name='Throttle'))
        if 'brake' in lap_df.columns:
            fig.add_trace(go.Scatter(x=lap_df['time_on_track_seconds'], y=lap_df['brake'], name='Brake'))
        fig.update_layout(title="Inputs Over Time", xaxis_title="Time (s)", yaxis_title="Value")
        st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.header("Driving Line")
    if df.empty:
        st.info("Select a session to view driving line.")
    else:
        laps = df['current_lap'].unique() if 'current_lap' in df.columns else [0]
        selected_lap = st.selectbox("Select Lap (Line)", sorted(laps), key="line_lap")
        lap_df = df[df['current_lap'] == selected_lap] if 'current_lap' in df.columns else df
        st.subheader("Track Map (Driving Line)")
        if {'position_x', 'position_y'}.issubset(lap_df.columns):
            fig = px.scatter(lap_df, x='position_x', y='position_y', color='car_speed',
                             title="Driving Line (colored by speed)", color_continuous_scale='Viridis')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No position data available for driving line.")

with tab4:
    st.header("Heatmaps & Action Maps")
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

with tab5:
    st.header("Gear, RPM, and Fuel")
    if not df.empty:
        st.subheader("Gear Usage Over Time")
        if 'current_gear' in df.columns and 'time_on_track_seconds' in df.columns:
            fig = px.step(df, x='time_on_track_seconds', y='current_gear', title="Gear Usage Over Time")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No gear/time data available.")

        st.subheader("RPM vs. Speed")
        if 'rpm' in df.columns and 'car_speed' in df.columns:
            fig = px.scatter(df, x='car_speed', y='rpm', title="RPM vs. Car Speed")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No RPM or speed data available.")

        st.subheader("Fuel Usage Over Time")
        if 'current_fuel' in df.columns and 'time_on_track_seconds' in df.columns:
            fig = px.line(df, x='time_on_track_seconds', y='current_fuel', title="Fuel Usage Over Time")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No fuel/time data available.")

with tab6:
    st.header("Tyre Temperatures & Suspension")
    if not df.empty:
        st.subheader("Tyre Temperatures Over Time")
        tyre_cols = ['tyre_temp_FL', 'tyre_temp_FR', 'tyre_temp_rl', 'tyre_temp_rr']
        present_tyre_cols = [col for col in tyre_cols if col in df.columns]
        if present_tyre_cols and 'time_on_track_seconds' in df.columns:
            fig = go.Figure()
            for col in present_tyre_cols:
                fig.add_trace(go.Scatter(x=df['time_on_track_seconds'], y=df[col], name=col))
            fig.update_layout(title="Tyre Temperatures Over Time", xaxis_title="Time (s)", yaxis_title="Temp (°C)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No tyre temp/time data available.")

        st.subheader("Suspension Travel Over Time")
        susp_cols = ['suspension_fl', 'suspension_fr', 'suspension_rl', 'suspension_rr']
        present_susp_cols = [col for col in susp_cols if col in df.columns]
        if present_susp_cols and 'time_on_track_seconds' in df.columns:
            fig = go.Figure()
            for col in present_susp_cols:
                fig.add_trace(go.Scatter(x=df['time_on_track_seconds'], y=df[col], name=col))
            fig.update_layout(title="Suspension Travel Over Time", xaxis_title="Time (s)", yaxis_title="Travel")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No suspension/time data available.")

with tab7:
    st.header("Elevation & Speed Histogram")
    if not df.empty:
        st.subheader("Elevation Map")
        if {'position_x', 'position_y', 'position_z'}.issubset(df.columns):
            fig = px.scatter(df, x='position_x', y='position_y', color='position_z',
                             title="Track Elevation Map", color_continuous_scale='Viridis')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No elevation data available.")

        st.subheader("Speed Distribution Histogram")
        if 'car_speed' in df.columns:
            fig = px.histogram(df, x='car_speed', nbins=40, title="Speed Distribution")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No speed data available.")

with tab8:
    st.header("Lap/Car Comparison")
    st.info("Compare up to 4 laps (from different sessions/cars) on the same track.")
    compare_files = st.multiselect("Select up to 4 sessions to compare", json_files, max_selections=4)
    compare_laps = []
    for file in compare_files:
        data = load_gcs_json(file)
        if not data: continue
        d = pd.DataFrame(data)
        if 'time_on_track' in d.columns:
            d['time_on_track_seconds'] = pd.to_timedelta(d['time_on_track']).dt.total_seconds()
        car_code = d.iloc[0].get("car_code") or d.iloc[0].get("car_id") or d.iloc[0].get("car") or ""
        car_name = cars_df[cars_df['ID'] == car_code]['ShortName'].values[0] if car_code in cars_df['ID'].values else car_code
        track_code = d.iloc[0].get("track_code") or d.iloc[0].get("track_id") or d.iloc[0].get("track") or ""
        track_name = tracks_df[tracks_df['ID'] == track_code]['Name'].values[0] if track_code in tracks_df['ID'].values else track_code
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
