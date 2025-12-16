import streamlit as st
import pandas as pd
import os

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="Taxi Route Anomaly Detection",
    layout="centered"
)

st.title("🚖 Taxi Route Anomaly & Overcharging Detection")
st.write(
    "This application allows users to check overcharging and route anomalies "
    "in NYC taxi trips using Big Data analytics results."
)

# ---------------- LOAD RESULT FILES ----------------
overcharge_path = "outputs/results/overcharging_cases.csv"
route_anomaly_path = "outputs/results/route_anomalies.csv"

if not os.path.exists(overcharge_path) or not os.path.exists(route_anomaly_path):
    st.error("❌ Result files not found. Please run the data processing pipeline first.")
    st.stop()

overcharge_df = pd.read_csv(overcharge_path)
route_df = pd.read_csv(route_anomaly_path)

# ---------------- LOAD LOCATION LOOKUP ----------------
lookup_path = "data/taxi_zone_lookup.csv"

if not os.path.exists(lookup_path):
    st.error("❌ taxi_zone_lookup.csv not found in data/ folder.")
    st.stop()

zone_df = pd.read_csv(lookup_path)
zone_df["display_name"] = zone_df["Zone"] + " (" + zone_df["Borough"] + ")"
zone_map = dict(zip(zone_df["display_name"], zone_df["LocationID"]))

# ---------------- INPUT MODE TOGGLE ----------------
st.subheader("🔍 Select Route Input Mode")

use_location_name = st.toggle(
    "Use Location Name instead of Location ID",
    value=False
)

# ---------------- INPUT FIELDS ----------------
st.subheader("📍 Enter Route Details")

if not use_location_name:
    col1, col2 = st.columns(2)
    with col1:
        pickup_id = st.text_input("Pickup Location ID")
    with col2:
        dropoff_id = st.text_input("Dropoff Location ID")
else:
    col1, col2 = st.columns(2)
    with col1:
        pickup_name = st.selectbox("Pickup Location", list(zone_map.keys()))
    with col2:
        dropoff_name = st.selectbox("Dropoff Location", list(zone_map.keys()))

    pickup_id = str(zone_map[pickup_name])
    dropoff_id = str(zone_map[dropoff_name])

# ---------------- CHECK BUTTON ----------------
if st.button("Check Anomalies"):
    if pickup_id == "" or dropoff_id == "":
        st.warning("⚠️ Please provide both Pickup and Dropoff details.")
    else:
        route_id = f"{pickup_id}_{dropoff_id}"

        st.subheader(f"📌 Results for Route ID: {route_id}")

        oc_result = overcharge_df[overcharge_df["route_id"] == route_id]
        ra_result = route_df[route_df["route_id"] == route_id]

        if oc_result.empty and ra_result.empty:
            st.success("✅ No anomalies detected for this route.")
        else:
            if not oc_result.empty:
                st.error("🚨 Overcharging Detected")
                st.dataframe(oc_result, use_container_width=True)

            if not ra_result.empty:
                st.warning("⚠️ Route Anomaly Detected")
                st.dataframe(ra_result, use_container_width=True)
