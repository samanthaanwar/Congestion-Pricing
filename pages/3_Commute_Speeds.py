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
DATA_DIR = BASE_DIR / 'data'

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
    height=500,
    width=400,
    showlegend=False
)

st.title('Commute Times')

col1, col2 = st.columns(2)
col1.markdown('''
    How did congestion pricing impact driving times throughout the city? Congestion should
    improve traffic speeds. To answer this question, we look at E-Z Pass readers installed
    throughout the city. Congestion pricing is directly funding this data collection project.
    Data begins in July 2024. For an appropriate comparison between pre- and post-
    congestion pricing impact, the pre period is defined as the average speed per route
    in August and September 2024. The post period is defined as the last six weeks of data.
    A map of routes analyzed is to the right, followed by an interactive line plot below.
''')

col1.markdown('''
    A small selection of the EZ-Pass reader routes that are in the CRZ are used in this 
    analysis. For comparison, "Lexington Ave - Southbound - 96th St to 86th St," which does
    not fall in the CRZ is included.
''')
col2.plotly_chart(route_map, use_container_width = False)

st.markdown(
    ':orange-badge[:material/star: NOTE: Congestion pricing is in effect from 5 AM to ' \
    '9 PM on weekdays and 9 AM to 9 PM on weekends.] ')

col3, col4 = st.columns(2)
route_choice = col3.selectbox(
    'Select route',
    keep
)

day_choice = col4.selectbox(
    'Select day of week',
    ('Monday', 'Tuesday', 'Wednesday', 
    'Thursday', 'Friday', 'Saturday', 'Sunday')
)

commute_speeds['date'] = pd.to_datetime(commute_speeds['date'])
commute_speeds['hour'] = commute_speeds['date'].dt.hour
commute_speeds['hour_label'] = commute_speeds['date'].apply(lambda x: x.strftime('%I:%M %p'))
commute_speeds['weekday'] = commute_speeds['date'].dt.day_name()

period = []
for day in commute_speeds['date']:
    if day < datetime(2024, 12, 31):
        period.append('Pre-CP')
    else:
        period.append('CP in Effect')

commute_speeds['period'] = period

agg_hr_df = (commute_speeds
             .groupby(['link_name', 'date', 'hour', 'hour_label', 'weekday', 'period'])['mph']
             .mean()
             .reset_index())

choice = agg_hr_df[(agg_hr_df.link_name == route_choice) & (agg_hr_df.weekday == day_choice)]

choice = (choice
          .groupby(['weekday', 'hour', 'hour_label', 'period', 'link_name'])['mph']
          .mean()
          .reset_index())

choice = choice.sort_values(by='hour')

line_plot = px.line(choice, x = 'hour_label', y = 'mph', color = 'period', 
                    line_shape = 'spline',
                    color_discrete_map={
                        'Pre-CP': 'gray',        # light blue
                        'CP in Effect': 'blue'   # red
    })
line_plot.update_layout(height = 500, width = 900, 
    yaxis_title = 'Average Speed (mph)', xaxis_title = '',
    font_family='Arial', legend_title = 'Period', 
    hovermode = 'x unified',
    legend=dict(
        x=0.8,
        y=0.99,
        xanchor='left',
        yanchor='top'
    ))

line_plot.update_traces(hovertemplate = '%{y:.2f} mph<extra></extra>')

# Define sorted list of labels manually
hour_order = pd.date_range("00:00", "23:00", freq="1H").strftime("%I:%M %p").tolist()
visible_labels = ['12:00 AM', '03:00 AM', '06:00 AM', '09:00 AM',
                  '12:00 PM', '03:00 PM', '06:00 PM', '09:00 PM']

line_plot.update_xaxes(
    categoryorder='array',
    categoryarray=hour_order,
    tickvals=visible_labels,
    tickangle=0  # make them horizontal
)

##### STREAMLIT APP #####

st.plotly_chart(line_plot)