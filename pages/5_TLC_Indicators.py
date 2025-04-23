import os
import sys
import pandas as pd
import streamlit as st
import altair as alt

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import load_data, plot_tlc_metric

# helper functions
def preprocess_tlc_data(df, metrics):
    # specifiy data types 
    df['month_year'] = pd.to_datetime(df['month_year'])
    for col in metrics:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
    # filter data to Jan/Feb/March 2024 & 2025
    df_filtered = df[df['month_year'].dt.month.isin([1, 2, 3]) & df['month_year'].dt.year.isin([2024, 2025])].copy()
    df_filtered['Month'] = df_filtered['month_year'].dt.strftime('%B')
    df_filtered['Year'] = df_filtered['month_year'].dt.year

    return df_filtered

# load data from NYC open data
tlc_indicators_url = "https://data.cityofnewyork.us/resource/v6kb-cqej.json"
params = {'$limit': 20000}
metrics = [
    'trips_per_day',
    'farebox_per_day',
    # 'unique_drivers',
    # 'unique_vehicles',
    # 'vehicles_per_day',
    # 'avg_days_vehicles_on_road',
    # 'avg_hours_per_day_per_vehicle',
    # 'avg_days_drivers_on_road',
    # 'avg_hours_per_day_per_driver',
    'avg_minutes_per_trip',
    # 'percent_of_trips_paid_with_credit_card',
    # 'trips_per_day_shared'
]

tlc_df = load_data(tlc_indicators_url, params)
filtered_df = preprocess_tlc_data(tlc_df, metrics)

# get specific licenese classes
df_yellow = filtered_df[filtered_df['license_class'] == 'Yellow'].copy()
df_fhv = filtered_df[filtered_df['license_class'] == 'FHV - High Volume'].copy()


st.title("TLC Industry Indicators (2024 vs 2025)")
st.write("Comparing select monthly metrics tabulated from trip records submitted for all TLC industries.")
st.markdown(
    """
    <div style="color: gray; font-size: 0.9em; font-style: italic;">
        NOTE: TLC defines the 'FHV-High Volume' license class to include Uber, Lyft, and other ride-hailing apps.
    </div>
    """,
    unsafe_allow_html=True
)


# Streamlit Section #1: Trips per Day
st.subheader("Trips per Day")
col1, col2 = st.columns(2)

with col1:
    st.markdown("**Yellow**")
    fig_trips_all = plot_tlc_metric(df_yellow, 'trips_per_day', "Trips per Day (Yellow)", "Trips")
    st.altair_chart(fig_trips_all, use_container_width=True)

with col2:
    st.markdown("**FHV - High Volume**")
    fig_trips_fhv = plot_tlc_metric(df_fhv, 'trips_per_day', "Trips per Day (FHV)", "Trips")
    st.altair_chart(fig_trips_fhv, use_container_width=True)


st.markdown('''
In both January and February, 2025 trip volumes exceeded those in 2024, with February 2025 trips reaching nearly 125,000 per day, roughly a 15–20% increase over the same month in 2024. This indicates a strong growth in ridership potentially influenced by post-congestion pricing dynamics.

FHV trip volumes saw less significant gains from 2024 to 2025 (~2-4%). 
''')

# Streamlit Section #2: Average Minutes per Trip
st.subheader("Average Trip Duration")
col1, col2 = st.columns(2)

with col1:
    st.markdown("**Yellow**")
    fig_duration_all = plot_tlc_metric(df_yellow, 'avg_minutes_per_trip', "Avg Trip Duration (All TLC)", "Minutes")
    st.altair_chart(fig_duration_all, use_container_width=True)

with col2:
    st.markdown("**FHV - High Volume**")
    fig_duration_fhv = plot_tlc_metric(df_fhv, 'avg_minutes_per_trip', "Avg Trip Duration (FHV)", "Minutes")
    st.altair_chart(fig_duration_fhv, use_container_width=True)

st.markdown('''
For yellow cars, trip duration in 2025 is slightly lower than in 2024. For example, January 2025 trips averaged under 14.5 minutes, compared to over 14.5 in 2024. FHV vehicles saw a much more noticeable reduction. For example, riders saved almost half a minute across all rides in January 2025 vs. January 2024. This may indicate that congestion pricing has achieved its goal of decreasing congestion by causing less cars on the road. 
''')

# Streamlit Section #3: Farebox per Day
st.subheader("Farebox per Day (Yellow)")

st.markdown(
    """
    <div style="color: gray; font-size: 0.9em; font-style: italic;">
        NOTE: TLC does not provide data on farebox amounts for FHV - High Volume vehicles (likely due to a lack of availability and privacy factors). However, based off the other matrics we have access to, it is safe to assume FHV vehicles follow similar trends to yellow cabs.
    </div>
    """,
    unsafe_allow_html=True
)
fig_farebox = plot_tlc_metric(df_yellow, 'farebox_per_day', "Total Farebox Revenue per Day (Yellow)", "Farebox ($m)")
st.altair_chart(fig_farebox)


st.markdown('''
Farebox revenue for Yellow Taxis in 2025 was consistently higher than in 2024:
- January 2025: ~\$2.5M/day vs ~$2.2M/day in 2024
- February 2025: ~$2.8M/day

This rise in farebox revenue, despite only modest increases in trip volume, suggests higher average fares per trip, likely due to new surcharges introduced under congestion pricing ($2.50 per trip). Regardless, the trend may point to an unintended but notable side effect of congestion pricing: a slow revitalization of the yellow cab industry, as more riders may be opting for taxis over personal vehicles to navigate the city.

However, it's difficult to isolate the effects of congestion pricing alone. The TLC has introduced other policy and operational changes in recent years that could also be contributing to increased ridership and revenue.
''')