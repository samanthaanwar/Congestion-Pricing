import requests
import pandas as pd
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import streamlit as st
import polyline
import plotly.express as px
from shapely.geometry import LineString
from pathlib import Path
import plotly.graph_objects as go
import geopandas as gpd
from shapely import wkt

# url = 'https://data.cityofnewyork.us/resource/6a2s-2t65.json'

keep = ['3rd Avenue - Northbound - 49th St to 57th St',
        '8th Avenue - Northbound - 23rd St to 34th St',
        '2nd Avenue - Southbound - 34th St to 23rd St',
        '5th Avenue - Southbound - 49th St to 42th St',
        'Lexington Ave - Southbound - 96 St to 86 St',
        '57th Street - Eastbound - 6th Ave to 5th Ave',
        'Williamsburg Bridge - Westbound - Brooklyn @ Bedford Ave to Manhattan @ Delancey',
        '23rd Street - Westbound - 6th Ave to 7th Ave',
        '34th Street - Westbound - 3rd Ave to Madison Ave']

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'gtfs_m'

# Load multiple files
commute_speeds = pd.read_csv(DATA_DIR / 'commute_speeds.csv')
unique_routes = pd.read_csv(DATA_DIR / 'unique_routes.csv')
unique_routes['geometry'] = unique_routes['geometry'].apply(wkt.loads)
unique_routes = gpd.GeoDataFrame(unique_routes, geometry='geometry', crs="EPSG:4326")

traces=[]
for i, row in unique_routes.iterrows():
    lons, lats = map(list, row['geometry'].xy)
    
    traces.append(go.Scattermapbox(
        lon=lons,
        lat=lats,
        mode='lines',
        text = [row['link_name']] * len(lons),
        hovertemplate = "%{text}<extra></extra>"
    ))
    
route_map = go.Figure(data=traces)

route_map.update_layout(
    mapbox_style="carto-positron",
    mapbox_zoom=11.7,
    mapbox_center={"lat": 40.75, "lon": -73.985},
    margin={"r": 0, "t": 0, "l": 0, "b": 0},
    height=600,
    width=400,
    showlegend=False
)

st.plotly_chart(route_map)

# streamlit app

route_choice = st.selectbox(
    'Select route',
    keep
)

day_choice = st.selectbox(
    'Select day of week',
    ('Monday', 'Tuesday', 'Wednesday', 
    'Thursday', 'Friday', 'Saturday', 'Sunday')
)

commute_speeds['date'] = pd.to_datetime(commute_speeds['date'])
commute_speeds['hour'] = commute_speeds['date'].dt.time
commute_speeds['hour_label'] = commute_speeds['date'].apply(lambda x: x.strftime('%I:%M %p'))
commute_speeds['weekday'] = commute_speeds['date'].dt.day_name()

period = []
for day in commute_speeds['date']:
    if day < datetime(2024, 12, 31):
        period.append('Pre-CP')
    else:
        period.append('CP in Effect')

commute_speeds['period'] = period

agg_hr_df = commute_speeds.groupby(['link_name', 'date', 'hour', 'hour_label', 'weekday', 'period'])['mph'].mean().reset_index()

choice = agg_hr_df[(agg_hr_df.link_name == route_choice) & (agg_hr_df.weekday == day_choice)]

choice = (choice
          .groupby(['weekday', 'hour', 'hour_label', 'period', 'link_name'])['mph']
          .mean()
          .reset_index())

choice = choice.sort_values(by='hour')

line_plot = px.line(choice, x = 'hour_label', y = 'mph', color = 'period', line_shape = 'spline')
line_plot.update_layout(height = 500, width = 900, 
    yaxis_title = 'Average Speed (mph)', xaxis_title = '',
    font_family='Arial', legend_title = 'Period')

# Define sorted list of labels manually
hour_order = pd.date_range("00:00", "23:00", freq="1H").strftime("%I:%M %p").tolist()

line_plot.update_xaxes(
    categoryorder='array',
    categoryarray=hour_order
)

st.plotly_chart(line_plot)