import streamlit as st
import pandas as pd
import json
from google.cloud import storage

# --- Load car and track data ---
cars_df = pd.read_csv('stm/gt7/db/cars.csv')
tracks_df = pd.read_csv('stm/gt7/db/course.csv')

# --- Show column names for debugging ---
st.write("Cars columns:", cars_df.columns.tolist())
st.write("Tracks columns:", tracks_df.columns.tolist())

# --- Use only columns that actually exist ---
car_cols = [col for col in ['ID', 'ShortName', 'Maker'] if col in cars_df.columns]
track_cols = [col for col in ['ID', 'Name', 'Category', 'Length', 'NumCorners'] if col in tracks_df.columns]

st.title("GT7 Telemetry Dashboard (Starter)")

st.subheader("Preview: Cars Data")
st.dataframe(cars_df[car_cols])

st.subheader("Preview: Tracks Data")
st.dataframe(tracks_df[track_cols])

# --- Dropdowns for selection ---
car_name_col = 'ShortName' if 'ShortName' in cars_df.columns else cars_df.columns[0]
track_name_col = 'Name' if 'Name' in tracks_df.columns else tracks_df.columns[0]

selected_track = st.selectbox("Select Track", tracks_df[track_name_col].tolist())
selected_car = st.selectbox("Select Car", cars_df[car_name_col].tolist())

# --- Show full info for selected items ---
track_info = tracks_df[tracks_df[track_name_col] == selected_track].iloc[0]
car_info = cars_df[cars_df[car_name_col] == selected_car].iloc[0]

st.subheader("Selected Track Info")
st.write(track_info)

st.subheader("Selected Car Info")
st.write(car_info)

# --- GCS Integration ---
# Load GCS credentials from Streamlit secrets
gcs_credentials = st.secrets["gcs"]
storage_client = storage.Client.from_service_account_info(gcs_credentials)

# Set your bucket name
BUCKET_NAME = "gt7-telemetry"

# List JSON telemetry files in the bucket
def list_telemetry_files():
    bucket = storage_client.bucket(BUCKET_NAME)
    blobs = bucket.list_blobs()
    return [blob.name for blob in blobs if blob.name.endswith('.json')]

# Download a selected telemetry file
def download_telemetry_file(filename):
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(filename)
    data = blob.download_as_text()
    return json.loads(data)

# --- Telemetry file selection and preview ---
st.subheader("Select a Telemetry Session File")
telemetry_files = list_telemetry_files()
selected_file = st.selectbox("Telemetry File", telemetry_files)

if selected_file:
    st.write(f"Selected file: {selected_file}")
    telemetry_data = download_telemetry_file(selected_file)
    st.write("First 3 data points:", telemetry_data[:3])  # Show a preview
