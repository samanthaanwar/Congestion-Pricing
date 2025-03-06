# import streamlit as st
# import sys
# sys.path.insert(0, '/visualizations')

# from visualizations import bus_lanes_plot

# bus_lanes = bus_lanes_plot.bus_lanes()

# st.title('Preliminary Impacts of Congestion Pricing in New York City')
# st.plotly_chart(bus_lanes)

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import geopandas as gpd
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union, linemerge
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'gtfs_m'

# Load multiple files
shapes = pd.read_csv(DATA_DIR / 'shapes.txt')
trips = pd.read_csv(DATA_DIR / 'trips.txt')
routes = pd.read_csv(DATA_DIR / 'routes.txt')

# Merge trips with routes to add route_short_name (bus route number)
trips_routes = trips.merge(routes[['route_id', 'route_short_name']], on='route_id', how='left')

# Drop duplicates to get a unique mapping of shape_id to route number
shape_to_route = trips_routes[['shape_id', 'route_short_name']].drop_duplicates()

gdf_stops = gpd.GeoDataFrame(shapes, geometry = gpd.points_from_xy(shapes.shape_pt_lon,shapes.shape_pt_lat))

# Define CRZ
zone_coords = [(-74.02, 40.70), (-73.93, 40.70), (-73.93, 40.768), (-74.02, 40.768)]
zone_polygon = Polygon(zone_coords)

gdf_zone = gpd.GeoDataFrame({'zone': ['Congestion Pricing']}, geometry=[zone_polygon], crs="EPSG:4326")

# Filter bus stops to only those within the CRZ polygon.
# Make sure gdf_stops is in EPSG:4326
gdf_stops_in_zone = gdf_stops[gdf_stops.geometry.within(zone_polygon)]

def create_line_string(group):
    # Ensure the points are sorted by shape_pt_sequence
    coords = group.sort_values('shape_pt_sequence')[['shape_pt_lon', 'shape_pt_lat']].values
    return LineString(coords)

gdf_routes = gdf_stops_in_zone.groupby('shape_id').apply(create_line_string, include_groups=False).reset_index()
gdf_routes.columns = ['shape_id', 'geometry']
gdf_routes = gpd.GeoDataFrame(gdf_routes, geometry='geometry', crs="EPSG:4326")
# gdf_routes is now a df of route geometries rather than bus stops

gdf_routes = gdf_routes.merge(shape_to_route, on = 'shape_id')

# take first route of each route name
route_dict = {}
for index, row in gdf_routes.iterrows():
    if row['route_short_name'] not in route_dict:
        route_dict[row['route_short_name']] = row['geometry']

dedupe = pd.DataFrame({'route_id':route_dict.keys(), 'geometry':route_dict.values()})
# dedupe = dedupe.rename_columns({'route_short_name': 'route_id'})
dedupe = gpd.GeoDataFrame(dedupe, geometry = 'geometry', crs = 'EPSG:4326')

# mta bus speeds data
bus_speeds = pd.read_csv('https://data.ny.gov/resource/6ksi-7cxr.csv?$limit=10000&borough=Manhattan')
bus_speeds_2025 = pd.read_csv('https://data.ny.gov/resource/4u4b-jge6.csv?$limit=10000&borough=Manhattan')

bus_speeds = pd.concat([bus_speeds, bus_speeds_2025])
bus_speeds['month'] = pd.to_datetime(bus_speeds.month)

bus_speeds['year'] = bus_speeds.month.apply(lambda x:x.year)
bus_speeds['month_code'] = bus_speeds.month.apply(lambda x:x.month)

# Filter to Peak Weekdays, January for YoY comparison
plot = bus_speeds.loc[(bus_speeds.period == 'Peak') &
                      (bus_speeds.day_type == 1) &
                      (bus_speeds.month_code == 1)]

improve = {}
for route in plot.route_id.unique():
    slice_df = plot.loc[plot.route_id == route]
    speeds = dict(zip(slice_df.year, slice_df.average_speed))
    if speeds[2025] > speeds[2024]:
        improve[route] = 'Improved'
    else:
        improve[route] = 'No Improvement'

# Don't need speed specifics for the map
map_plot = plot[['route_id']].drop_duplicates()
map_plot['performance'] = map_plot['route_id'].map(improve)
map_plot = map_plot.merge(dedupe, on = 'route_id')

# Bus Lanes data
bus_lanes = pd.read_csv('https://data.cityofnewyork.us/api/views/ycrg-ses3/rows.csv?')
bus_lanes['geometry'] = gpd.GeoSeries.from_wkt(bus_lanes['the_geom'])
bus_lanes = gpd.GeoDataFrame(bus_lanes, geometry = 'geometry', crs = 'EPSG:4326')
bus_lanes = bus_lanes[bus_lanes.geometry.within(zone_polygon)].reset_index(drop=True)

# Combine bus lane points into single trace
combined = unary_union(bus_lanes.geometry)
merged = linemerge(combined)


fig = go.Figure()

lons, lats = [], []
for line in merged.geoms:  # Each piece is a LineString
    x, y = line.xy
    lons.extend(x)
    lats.extend(y)
    # Add None to separate segments in a single trace
    lons.append(None)
    lats.append(None)

fig.add_trace(go.Scattermapbox(
    mode='lines',
    lon=lons,
    lat=lats,
    name='Bus Lanes',
    line=dict(width=4, color='blue'),
    opacity = 0.3
))

improved = map_plot[map_plot['performance'] == 'Improved']
for idx, row in improved.iterrows():
    x, y = row['geometry'].xy
    fig.add_trace(go.Scattermapbox(
        mode="lines",
        lon=list(x),
        lat=list(y),
        name=str(row['route_id']),
        line=dict(width=2, color = 'green')
    ))

no_improvement = map_plot[map_plot['performance'] == 'No Improvement']
for idx, row in no_improvement.iterrows():
    x, y = row['geometry'].xy
    fig.add_trace(go.Scattermapbox(
        mode="lines",
        lon=list(x),
        lat=list(y),
        name=str(row['route_id']),
        line=dict(width=2, color = 'red')
    ))

# Number of traces in each group
improved_count = len(improved)
not_improved_count = len(no_improvement)

# Update menus for filtering
fig.update_layout(
    updatemenus=[
        dict(
            type='buttons',
            direction='left',
            buttons=[
                dict(
                    label='Show All',
                    method='update',
                    args=[
                        {'visible': [True] * len(fig.data)}
                    ]
                ),
                dict(
                    label='Improved Routes',
                    method='update',
                    args=[
                        {'visible': [True] + [True]*improved_count + [False] * not_improved_count}
                    ]
                ),
                dict(
                    label='No Improvement Routes',
                    method='update',
                    args=[
                        {'visible': [True] + [False]*improved_count + [True] * not_improved_count}
                    ]
                ),
                dict(
                    label='Bus Lanes',
                    method='update',
                    args=[
                        {'visible': [True] + [False]*(improved_count + not_improved_count)}
                    ]
                )
            ],
            pad={"r": 10, "t": 10},
            showactive=True,
            x=0.02,
            xanchor="left",
            y=1,
            yanchor="top"
        )
    ],
    mapbox_style="carto-positron",
    mapbox_zoom=12.1,
    mapbox_center={"lat": 40.735, "lon": -73.995},
    showlegend=False,
    height = 800, width = 800,
    yaxis_range = [4, 12],
    font_family = 'Arial'
)

st.title('Buses moved faster in Jan 2025 vs. Jan 2024')
st.plotly_chart(fig)
'''
TO-DO: Update hover data. Remove coordinates, add in speed improvement.
'''