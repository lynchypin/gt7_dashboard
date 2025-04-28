import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json
from google.cloud import storage
from google.oauth2 import service_account
import plotly.graph_objects as go

# --- Google Cloud Storage client using Streamlit secrets ---
@st.cache_resource
def get_storage_client():
    credentials_dict = st.secrets["gcs"]
    credentials = service_account.Credentials.from_service_account_info(dict(credentials_dict))
    return storage.Client(credentials=credentials, project=credentials.project_id)

# --- List available telemetry files in your GCS bucket ---
@st.cache_data(ttl=300)
def list_telemetry_files():
    client = get_storage_client()
    bucket = client.bucket("gt7-telemetry")
    blobs = bucket.list_blobs()
    return [blob.name for blob in blobs if blob.name.endswith('.json')]

# --- Download and load a telemetry file from GCS ---
@st.cache_data(ttl=300)
def load_telemetry_file(file_name):
    client = get_storage_client()
    bucket = client.bucket("gt7-telemetry")
    blob = bucket.blob(file_name)
    data = blob.download_as_text()
    return json.loads(data)

# --- Load car and track data from CSVs in the repo ---
@st.cache_data
def load_cars():
    return pd.read_csv("cars.csv")

@st.cache_data
def load_tracks():
    return pd.read_csv("tracks.csv")

# --- Streamlit UI ---
st.title("GT7 Telemetry Dashboard")

# Sidebar: Car and Track selection
cars_df = load_cars()
tracks_df = load_tracks()

selected_car = st.sidebar.selectbox("Select Car", cars_df['ShortName'])
selected_track = st.sidebar.selectbox("Select Track", tracks_df['Name'])

# Sidebar: Telemetry file selection
telemetry_files = list_telemetry_files()
if not telemetry_files:
    st.warning("No telemetry files found in your GCS bucket.")
    st.stop()

selected_file = st.sidebar.selectbox("Select Telemetry File", telemetry_files)

# Load selected telemetry data
telemetry_data = load_telemetry_file(selected_file)

# --- Example: Show raw telemetry data ---
if st.checkbox("Show raw telemetry data"):
    st.json(telemetry_data)

# --- Example: Plot speed over time if available ---
if isinstance(telemetry_data, list) and len(telemetry_data) > 0 and 'speed' in telemetry_data[0]:
    speeds = [point['speed'] for point in telemetry_data]
    times = np.arange(len(speeds))
    st.subheader("Speed Over Time")
    fig, ax = plt.subplots()
    ax.plot(times, speeds)
    ax.set_xlabel("Time (frames)")
    ax.set_ylabel("Speed (km/h)")
    st.pyplot(fig)
else:
    st.info("No speed data found in this telemetry file.")

# --- Example: Plot with Plotly ---
if isinstance(telemetry_data, list) and len(telemetry_data) > 0 and 'speed' in telemetry_data[0]:
    st.subheader("Speed Over Time (Plotly)")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=times, y=speeds, mode='lines', name='Speed'))
    fig.update_layout(xaxis_title="Time (frames)", yaxis_title="Speed (km/h)")
    st.plotly_chart(fig)

# --- Add more analysis/visualizations below as needed ---
