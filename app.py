import streamlit as st
import pandas as pd

# Read the CSVs (no skiprows needed)
cars_df = pd.read_csv('stm/gt7/db/cars.csv')
tracks_df = pd.read_csv('stm/gt7/db/course.csv')

# Show the actual column names for debugging
st.write("Cars columns:", cars_df.columns.tolist())
st.write("Tracks columns:", tracks_df.columns.tolist())

# Use only columns that actually exist
car_cols = [col for col in ['ID', 'ShortName', 'Maker'] if col in cars_df.columns]
track_cols = [col for col in ['ID', 'Name', 'Category', 'Length', 'NumCorners'] if col in tracks_df.columns]

st.title("GT7 Telemetry Dashboard (Starter)")

st.subheader("Preview: Cars Data")
st.dataframe(cars_df[car_cols])

st.subheader("Preview: Tracks Data")
st.dataframe(tracks_df[track_cols])

# Use correct columns for dropdowns
car_name_col = 'ShortName' if 'ShortName' in cars_df.columns else cars_df.columns[0]
track_name_col = 'Name' if 'Name' in tracks_df.columns else tracks_df.columns[0]

selected_track = st.selectbox("Select Track", tracks_df[track_name_col].tolist())
selected_car = st.selectbox("Select Car", cars_df[car_name_col].tolist())

# Show full info for selected items
track_info = tracks_df[tracks_df[track_name_col] == selected_track].iloc[0]
car_info = cars_df[cars_df[car_name_col] == selected_car].iloc[0]

st.subheader("Selected Track Info")
st.write(track_info)

st.subheader("Selected Car Info")
st.write(car_info)
