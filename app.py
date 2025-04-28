import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json
from google.cloud import storage
import plotly.graph_objects as go
import plotly.express as px
from matplotlib.colors import LinearSegmentedColormap

# Set up page config
st.set_page_config(page_title="GT7 Telemetry Dashboard", layout="wide")

# Initialize GCS client
@st.cache_resource
def get_storage_client():
    credentials_path = "gt7-telemetry-925485338b46.json"
    return storage.Client.from_service_account_json(credentials_path)

# List available telemetry files
@st.cache_data(ttl=300)
def list_telemetry_files():
    client = get_storage_client()
    bucket = client.bucket("gt7-telemetry")
    blobs = bucket.list_blobs()
    return [blob.name for blob in blobs if blob.name.endswith('.json')]

# Download telemetry file
@st.cache_data
def download_telemetry_file(filename):
    client = get_storage_client()
    bucket = client.bucket("gt7-telemetry")
    blob = bucket.blob(filename)
    data = blob.download_as_text()
    return json.loads(data)

# Load car and track data
@st.cache_data
def load_reference_data():
    cars_df = pd.read_csv('stm/gt7/db/cars.csv')
    tracks_df = pd.read_csv('stm/gt7/db/course.csv')
    return cars_df, tracks_df

# Create tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Single Race Analysis",
    "Lap Comparison",
    "Car Comparison",
    "Track Insights",
    "Leaderboards"
])

# Sidebar for file selection
st.sidebar.title("GT7 Telemetry Analysis")
cars_df, tracks_df = load_reference_data()

# Track and car selection
selected_track = st.sidebar.selectbox("Select Track", tracks_df['Name'].tolist())
selected_car = st.sidebar.selectbox("Select Car", cars_df['ShortName'].tolist())

# File selection
telemetry_files = list_telemetry_files()
selected_file = st.sidebar.selectbox("Select Telemetry File", telemetry_files)

# Load selected telemetry data
if selected_file:
    telemetry_data = download_telemetry_file(selected_file)
    df = pd.DataFrame(telemetry_data)

    # Display track and car info
    st.sidebar.subheader("Track Info")
    st.sidebar.write(tracks_df[tracks_df['Name'] == selected_track].iloc[0])

    st.sidebar.subheader("Car Info")
    st.sidebar.write(cars_df[cars_df['ShortName'] == selected_car].iloc[0])

    # Single Race Analysis Tab
    with tab1:
        st.header("Single Race Analysis")

        # Speed heatmap on track
        st.subheader("Speed Heatmap")
        fig = px.scatter(df, x="position_x", y="position_y", color="car_speed",
                         color_continuous_scale="viridis", title="Track Map with Speed Heatmap")
        fig.update_layout(height=600)
        st.plotly_chart(fig, use_container_width=True)

        # Throttle/Brake Analysis
        st.subheader("Throttle and Brake Application")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['distance'], y=df['throttle'],
                                 mode='lines', name='Throttle', line=dict(color='green')))
        fig.add_trace(go.Scatter(x=df['distance'], y=df['brake'],
                                 mode='lines', name='Brake', line=dict(color='red')))
        fig.update_layout(height=400, xaxis_title="Distance (m)", yaxis_title="Input %")
        st.plotly_chart(fig, use_container_width=True)

        # Speed Profile
        st.subheader("Speed Profile")
        fig = px.line(df, x="distance", y="car_speed", title="Speed vs Distance")
        fig.update_layout(height=400, xaxis_title="Distance (m)", yaxis_title="Speed (km/h)")
        st.plotly_chart(fig, use_container_width=True)

    # Lap Comparison Tab
    with tab2:
        st.header("Lap Comparison")

        # Select up to 4 laps to compare
        compare_files = st.multiselect("Select up to 4 sessions to compare",
                                      telemetry_files, default=[selected_file], max_selections=4)

        if compare_files:
            # Speed comparison
            st.subheader("Speed Comparison")
            fig = go.Figure()

            for i, file in enumerate(compare_files):
                comp_data = download_telemetry_file(file)
                comp_df = pd.DataFrame(comp_data)
                fig.add_trace(go.Scatter(x=comp_df['distance'], y=comp_df['car_speed'],
                                        mode='lines', name=f'Session {i+1}'))

            fig.update_layout(height=500, xaxis_title="Distance (m)", yaxis_title="Speed (km/h)")
            st.plotly_chart(fig, use_container_width=True)

            # Racing line comparison
            st.subheader("Racing Line Comparison")
            fig = go.Figure()

            for i, file in enumerate(compare_files):
                comp_data = download_telemetry_file(file)
                comp_df = pd.DataFrame(comp_data)
                fig.add_trace(go.Scatter(x=comp_df['position_x'], y=comp_df['position_y'],
                                        mode='lines', name=f'Session {i+1}'))

            fig.update_layout(height=600)
            st.plotly_chart(fig, use_container_width=True)

    # Car Comparison Tab
    with tab3:
        st.header("Car Comparison")
        st.info("Select different cars on the same track to compare performance.")

        # This would require multiple files with different cars on the same track
        # For now, we'll show a placeholder

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Top Speed Comparison")
            # Placeholder chart
            fig = go.Figure(go.Bar(
                x=['Car 1', 'Car 2', 'Car 3', 'Car 4'],
                y=[289, 276, 294, 265],
                marker_color=['blue', 'green', 'red', 'orange']
            ))
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("Acceleration Comparison")
            # Placeholder chart
            fig = go.Figure()
            x = np.linspace(0, 10, 100)
            fig.add_trace(go.Scatter(x=x, y=100*(1-np.exp(-0.5*x)), name='Car 1'))
            fig.add_trace(go.Scatter(x=x, y=100*(1-np.exp(-0.4*x)), name='Car 2'))
            fig.add_trace(go.Scatter(x=x, y=100*(1-np.exp(-0.6*x)), name='Car 3'))
            fig.add_trace(go.Scatter(x=x, y=100*(1-np.exp(-0.35*x)), name='Car 4'))
            fig.update_layout(height=400, xaxis_title="Time (s)", yaxis_title="Speed (km/h)")
            st.plotly_chart(fig, use_container_width=True)

    # Track Insights Tab
    with tab4:
        st.header("Track Insights")

        # Brake points visualization
        st.subheader("Brake Points")
        brake_points = df[df['brake'] > 20]
        fig = px.scatter(brake_points, x="position_x", y="position_y",
                         color="brake", size="brake",
                         color_continuous_scale="reds", size_max=15,
                         title="Brake Points on Track")
        fig.update_layout(height=600)
        st.plotly_chart(fig, use_container_width=True)

        # Acceleration points
        st.subheader("Acceleration Points")
        accel_points = df[df['throttle'] > 80]
        fig = px.scatter(accel_points, x="position_x", y="position_y",
                         color="throttle", size="throttle",
                         color_continuous_scale="greens", size_max=15,
                         title="Acceleration Points on Track")
        fig.update_layout(height=600)
        st.plotly_chart(fig, use_container_width=True)

    # Leaderboards Tab
    with tab5:
        st.header("Leaderboards")

        # Placeholder leaderboard data
        leaderboard_data = {
            'Driver': ['Player 1', 'Player 2', 'Player 3', 'Player 4', 'Player 5'],
            'Car': ['Ferrari', 'Porsche', 'McLaren', 'Aston Martin', 'Lamborghini'],
            'Best Lap': ['1:42.345', '1:43.012', '1:43.567', '1:44.123', '1:44.789'],
            'Gap': ['+0.000', '+0.667', '+1.222', '+1.778', '+2.444']
        }

        leaderboard_df = pd.DataFrame(leaderboard_data)
        st.dataframe(leaderboard_df, use_container_width=True)

        # Average lap times by car
        st.subheader("Average Lap Times by Car")
        avg_times = {
            'Car': ['Ferrari', 'Porsche', 'McLaren', 'Aston Martin', 'Lamborghini'],
            'Avg Time': [103.2, 104.5, 105.1, 106.3, 107.2]
        }

        avg_df = pd.DataFrame(avg_times)
        fig = px.bar(avg_df, x='Car', y='Avg Time', title="Average Lap Times by Car")
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)

else:
    st.info("Please select a telemetry file to analyze.")
