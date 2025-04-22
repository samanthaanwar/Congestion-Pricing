import os
import sys
import pandas as pd
import pydeck as pdk
import streamlit as st
import matplotlib.pyplot as plt
from PIL import Image

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import load_data

# --- Data Processing ---
def preprocess_data(df):
    if df.empty:
        return df

    # convert columns (otherwise most default to strings)
    df['crash_date'] = pd.to_datetime(df['crash_date'], errors='coerce')
    df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
    df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
    df['year'] = df['crash_date'].dt.year
    df['month'] = df['crash_date'].dt.strftime('%B')

    df.dropna(subset=['crash_date', 'latitude', 'longitude'], inplace=True)

    # Manhattan below 60th Street (easiest way to bound the congestion zone without working with SHP files)
    manhattan_filter = (
        (df['latitude'] >= 40.7000) & (df['latitude'] <= 40.7660) &
        (df['longitude'] >= -74.0200) & (df['longitude'] <= -73.9500)
    )

    # Queens: Long Island City and east of Queensboro Bridge
    queens_filter = (
        (df['latitude'] >= 40.735) & (df['latitude'] <= 40.770) &
        (df['longitude'] >= -73.9600) & (df['longitude'] <= -73.9300)
    )

    # Brooklyn: DUMBO, Brooklyn Heights, near Brooklyn Bridge
    brooklyn_filter = (
        (df['latitude'] >= 40.6900) & (df['latitude'] <= 40.7050) &
        (df['longitude'] >= -73.9950) & (df['longitude'] <= -73.9700)
    )

    df_filtered = df[(manhattan_filter | queens_filter | brooklyn_filter)].copy()
    return df_filtered

def get_monthly_crash_count_fig(crash_df):
    # group and pivot to get crashes per year + month combo
    month_order = ['January', 'February', 'March']
    
    pivot_plot = (
        crash_df
        .groupby(['year', 'month'])
        .size()
        .reset_index(name='crash_count')
        .pivot(index='month', columns='year', values='crash_count')
        .fillna(0)
        .astype(int)
        .reindex(month_order)
        .reset_index()
    )
    pivot_plot['month'] = pd.Categorical(pivot_plot['month'], categories=month_order, ordered=True)
    pivot_plot = pivot_plot.sort_values('month').rename(columns={'month': 'Month'})

    fig, ax = plt.subplots(figsize=(12, 6))

    # add a line for each year
    for year in pivot_plot.columns[1:]:
        ax.plot(pivot_plot['Month'], pivot_plot[year], label=str(year), marker='o')
        for i, value in enumerate(pivot_plot[year]):
            ax.text(i, value - 8, str(value), ha='center', va='bottom', fontsize=8)

    ax.set_title("Monthly Crash Counts by Year")
    ax.set_xlabel("Month")
    ax.set_ylabel("Crash Count")
    ax.set_xticks(range(len(pivot_plot['Month'])))
    ax.set_xticklabels(pivot_plot['Month'], rotation=45)
    ax.legend(title="Year")
    ax.grid(True)
    return fig

# data loading & processing 
crashes_api_url = 'https://data.cityofnewyork.us/resource/h9gi-nx95.json'
start_date_str = "2024-01-01T00:00:00" # from 01/01/2024
end_date_str = pd.Timestamp.now().strftime("%Y-%m-%dT%H:%M:%S") # to now
params = {
    '$where': f"crash_date >= '{start_date_str}' AND crash_date < '{end_date_str}'",
    '$limit': 200000
}
raw_crash_df = load_data(BASE_URL=crashes_api_url, params=params)
crz_crashes = preprocess_data(raw_crash_df)

# Streamlit Subsection #1: Introduction & Motor Deaths section
st.title("NYC Motor Vehicle Collisions (Congestion Zone & Surrounding Area)")
st.write("Comparing crash densities across 2024 vs 2025. Use sidebar controls to select specific month.")
st.markdown('''
In 2024, 226 people were killed and 49,364 were injured as a result of motor vehicles collisions across NYC. 21 of those deaths occurred within the congestion zone and surrounding areas in Queens and Brooklyn. As a result, a large factor in the success of congestion pricing is whether the number of motor crashes saw a decrease or not. 
''')
image = Image.open("./images/motor_deaths_in_2024.png")
st.image(image, caption='Deaths via Motor Vehicle Collisions (2024)', use_container_width=True)

# Streamlit Subsection #2: Monthly Crash Comparison viz
st.markdown("---")
st.subheader("Monthly Crash Comparison: 2024 vs 2025")
st.markdown('''
We begin with a comparison of the number of crashes across corresponding months in 2024 and 2025. This crash data is filtered down to crashes that occurred in the Congestion Relief zone and areas surrounding major infrastructure entering and exiting the zone from outer boroughs (e.g. Queensboro Bridge, Brooklyn Bridge, Williamsburg Bridge). 

Based on this initial analysis, we can see that for each month that the congestion pricing was in effect (Jan - March 2025), there were less accidents in the same month of the previous year. However, we are seeing that gap slowly narrow with only a reduction of 3.04% from March 2024 to March 2025. 
''')

fig = get_monthly_crash_count_fig(crz_crashes)
st.pyplot(fig)

# Streamlit Subsection #3: Crash density comparison maps
st.markdown("---")
st.subheader("Crash Density Shift After Congestion Pricing")

month_options = {"January": 1, "February": 2, "March": 3}
month_choice = st.selectbox('Select month', options=["January", "February", "March"])

df_2024 = crz_crashes[
    (crz_crashes['crash_date'].dt.year == 2024) &
    (crz_crashes['crash_date'].dt.month == month_options[month_choice])
]

df_2025 = crz_crashes[
    (crz_crashes['crash_date'].dt.year == 2025) &
    (crz_crashes['crash_date'].dt.month ==  month_options[month_choice])
]

# configure map
view_state = pdk.ViewState(
    latitude=40.74,
    longitude=-73.985,
    zoom=11.0,
    pitch=0,
    bearing=0
)

common_layer_props = {
    "auto_highlight": True,
    "pickable": True,
    "radius": 200,
    "elevation_scale": 1,
    "opacity": 0.3
}

before_layer = pdk.Layer(
    "HexagonLayer",
    data=df_2024,
    id='2024_layer',
    get_position='[longitude, latitude]',
    get_fill_color=[0, 100, 255, 160], # blues
    **common_layer_props
)

after_layer = pdk.Layer(
    "HexagonLayer",
    data=df_2025,
    id='2025_layer',
    get_position='[longitude, latitude]',
    get_fill_color=[255, 50, 50, 160], # reds
    **common_layer_props
)

tooltip = {
    "html": "<b>Number of Crashes:</b> {elevationValue}<br/>"
            "<b>Location approx:</b> {position}",
    "style": {"backgroundColor": "steelblue", "color": "white"}
}

col1, col2 = st.columns(2)

with col1:
    st.subheader(f"{month_choice} 2024")
    st.pydeck_chart(pdk.Deck(
        layers=[before_layer],
        initial_view_state=view_state,
        map_provider='mapbox',
        map_style=pdk.map_styles.MAPBOX_DARK,
        tooltip=tooltip
    ))

with col2:
    st.subheader(f"{month_choice} 2025")
    st.pydeck_chart(pdk.Deck(
        layers=[after_layer],
        initial_view_state=view_state,
        map_provider='mapbox',
        map_style=pdk.map_styles.MAPBOX_DARK,
        tooltip=tooltip
    ))
