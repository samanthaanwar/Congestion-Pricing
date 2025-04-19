import requests
import pandas as pd
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import streamlit as st
import polyline

url = 'https://data.cityofnewyork.us/resource/6a2s-2t65.json'

keep = ['3rd Avenue - Northbound - 49th St to 57th St',
        '8th Avenue - Northbound - 23rd St to 34th St',
        '2nd Avenue - Southbound - 34th St to 23rd St',
        '5th Avenue - Southbound - 49th St to 42th St',
        'Lexington Ave - Southbound - 96 St to 86 St',
        '57th Street - Eastbound - 6th Ave to 5th Ave',
        'Williamsburg Bridge - Westbound - Brooklyn @ Bedford Ave to Manhattan @ Delancey',
        '23rd Street - Westbound - 6th Ave to 7th Ave',
        '34th Street - Westbound - 3rd Ave to Madison Ave']

# fetch data concurrently
def fetch_chunk(route, current, next_day):
    where_clause = (
        f"link_name = '{route}' AND n_samples > 5"
        f"AND median_calculation_timestamp BETWEEN '{current.isoformat()}' AND '{next_day.isoformat()}'"
    )
    params = {
        "$where": where_clause,
        "$limit": 50000
    }
    response = requests.get(url, params=params)
    data = response.json()
    if data:
        return pd.DataFrame(data)
    return None

def get_data(routes, time_ranges, step_days=7):
    all_data = []
    tasks = []

    with ThreadPoolExecutor(max_workers=10) as executor:
        for route in routes:
            for start_date, end_date in time_ranges:
                current = start_date
                while current < end_date:
                    next_day = current + timedelta(days=step_days)
                    tasks.append(executor.submit(fetch_chunk, route, current, next_day))
                    current = next_day

        for future in as_completed(tasks):
            try:
                result = future.result()
                if result is not None:
                    all_data.append(result)
            except Exception as e:
                print("Error during request:", e)

    return pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()

time_ranges = [
    (datetime(2024, 8, 1), datetime(2024, 10, 1)),  # August and September 2024
    (datetime.now() - timedelta(weeks=6), datetime.now())  # Last 6 weeks
]

df = get_data(keep, time_ranges)

unique_routes = df[['link_name', 'polyline']].drop_duplicates()
unique_routes['coords'] = unique_routes['polyline'].apply(polyline.decode)
unique_routes['geometry'] = unique_routes['coords'].apply(lambda pts: LineString([(lon, lat) for lat, lon in pts]))

df['median_speed_fps'] = df['median_speed_fps'].astype(float)
df['mph'] = df['median_speed_fps'] * 0.681818
df = df[['link_name', 'median_calculation_timestamp', 'mph']]

df['median_calculation_timestamp'] = pd.to_datetime(df['median_calculation_timestamp'])

df['date'] = df['median_calculation_timestamp'].dt.floor('H')
df['hour'] = df['date'].apply(lambda x: x.strftime('%H:%M'))
df['hour_label'] = df['date'].apply(lambda x: x.strftime('%I:%M %p'))
df['weekday'] = df['date'].dt.day_name()

period = []
for day in df['date']:
    if day < datetime(2024, 12, 31):
        period.append('Pre-CP')
    else:
        period.append('CP in Effect')

df['period'] = period

# aggregate by hour to smooth over data which is collected every minute
agg_hr_df = df.groupby(['link_name', 'date', 'hour', 'hour_label', 'weekday', 'period'])['mph'].mean().reset_index()

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

choice = agg_hr_df[(agg_hr_df.link_name == route_choice) & (agg_hr_df.weekday == day_choice)]
choice = (choice
    .groupby(['weekday', 'hour', 'hour_label', 'period', 'link_name'])['mph']
    .mean()
    .reset_index()
    .sort_values(by='hour'))

line_plot = px.line(choice, x = 'hour_label', y = 'mph', color = 'period', line_shape = 'spline')
line_plot.update_layout(height = 500, width = 900, 
    yaxis_title = 'Average Speed (mph)', xaxis_title = '',
    font_family='Arial', legend_title = 'Period')

st.plotly_chart(line_plot)