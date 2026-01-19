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

# --------- Extract Pickup & Dropoff IDs from route_id ---------
route_df[["PULocationID", "DOLocationID"]] = (
    route_df["route_id"]
    .str.split("_", expand=True)
    .astype(int)
)



# ---------------- LOAD LOCATION LOOKUP ----------------
lookup_path = "data/taxi_zone_lookup.csv"

if not os.path.exists(lookup_path):
    st.error("❌ taxi_zone_lookup.csv not found in data/ folder.")
    st.stop()

zone_df = pd.read_csv(lookup_path)
zone_df["display_name"] = zone_df["Zone"] + " (" + zone_df["Borough"] + ")"

zone_map = dict(zip(zone_df["display_name"], zone_df["LocationID"]))
id_to_zone = dict(zip(zone_df["LocationID"], zone_df["Zone"]))
id_to_borough = dict(zip(zone_df["LocationID"], zone_df["Borough"]))

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

        # ---------------- OLD OUTPUT (UNCHANGED) ----------------
        if oc_result.empty and ra_result.empty:
            st.success("✅ No anomalies detected for this route.")
        else:
            if not oc_result.empty:
                st.error("🚨 Overcharging Detected")
                st.dataframe(oc_result, use_container_width=True)

            if not ra_result.empty:
                st.warning("⚠️ Route Anomaly Detected")
                st.dataframe(ra_result, use_container_width=True)

        # =======================================================
        # 📊 ROUTE ANALYTICS & EXPLANATION (RATE-BASED)
        # =======================================================

        st.markdown("---")
        st.subheader("📊 Route Analytics & Explanation")

        route_data = route_df[route_df["route_id"] == route_id]

        if route_data.empty:
            st.info("Not enough historical data for deep analysis.")
        else:
            avg_rate = route_data["avg_fare_per_min"].mean()
            charged_rate = route_data["fare_per_min"].mean()
            avg_duration = route_data["trip_duration_minutes"].mean()
            total_trips = len(route_data)

            rate_diff_pct = ((charged_rate - avg_rate) / avg_rate) * 100

            st.write(f"**Expected Fare Rate:** ₹{avg_rate:.2f} per minute")
            st.write(f"**Observed Fare Rate:** ₹{charged_rate:.2f} per minute")
            st.write(f"**Average Trip Duration:** {avg_duration:.1f} minutes")
            st.write(f"**Trips Analysed:** {total_trips}")

            if rate_diff_pct > 10:
                st.error(
                    f"🚨 Overcharging detected: fare rate is "
                    f"**{rate_diff_pct:.1f}% higher** than historical average."
                )
            else:
                st.success(
                    "✅ Fare rate for this route is within the normal range."
                )

        # =======================================================
        # 🧭 ALTERNATIVE SAFER PICKUP SUGGESTION
        # =======================================================

        st.markdown("---")
        st.subheader("🧭 Suggested Safer Alternative Pickup")

        try:
            pickup_borough = id_to_borough[int(pickup_id)]

            nearby_ids = zone_df[
                (zone_df["Borough"] == pickup_borough) &
                (zone_df["LocationID"] != int(pickup_id))
            ]["LocationID"].tolist()

            alternatives = route_df[
                (route_df["PULocationID"].isin(nearby_ids)) &
                (route_df["DOLocationID"] == int(dropoff_id))
            ]

            if alternatives.empty:
                st.info("No better nearby alternative found.")
            else:
                alt_stats = (
                    alternatives
                    .groupby("PULocationID")
                    .agg(
                        avg_rate=("avg_fare_per_min", "mean"),
                        charged_rate=("fare_per_min", "mean"),
                        trips=("trip_duration_minutes", "count")
                    )
                    .reset_index()
                    .sort_values("avg_rate")
                    .head(1)
                )

                best_id = int(alt_stats.iloc[0]["PULocationID"])
                best_zone = id_to_zone[best_id]

                improvement_pct = (
                    (charged_rate - alt_stats.iloc[0]["avg_rate"])
                    / charged_rate
                ) * 100

                st.success(
                    f"""
                    ✅ **Better Pickup Option Found**

                    • Suggested Pickup: **{best_zone}**
                    • Average Fare Rate: ₹{alt_stats.iloc[0]['avg_rate']:.2f} / min
                    • Trips Analysed: {int(alt_stats.iloc[0]['trips'])}
                    • Estimated Reduction: **{improvement_pct:.1f}%**

                    👉 Recommendation: *Choosing this pickup point statistically
                    reduces overcharging risk.*
                    """
                )

        except Exception:
            st.info("Alternative route analysis not available.")
