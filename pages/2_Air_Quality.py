import pandas as pd
import plotly.graph_objects as go
import streamlit as st

dfs = []

for year in [2022, 2023, 2024, 2025]:
    if year == 2025:
        for month in range(1,4):  
            url = f'https://azdohv2staticweb.blob.core.windows.net/$web/hist/csv/{year}/{month}/hourlyMonitoring.csv'
            dfs.append(pd.read_csv(url))
    else:
        for month in range(1,13):
            url = f'https://azdohv2staticweb.blob.core.windows.net/$web/hist/csv/{year}/{month}/hourlyMonitoring.csv'
            dfs.append(pd.read_csv(url))

# Concatenate all data into one DataFrame
combined_df = pd.concat(dfs, ignore_index=True)
combined_df['ObservationTimeUTC'] = pd.to_datetime(combined_df['ObservationTimeUTC'])

siteinfo = pd.read_csv('https://azdohv2staticweb.blob.core.windows.net/$web/hist/csv/location.csv')
combined_df = combined_df.merge(siteinfo, on = 'SiteID')

combined_df['Date'] = combined_df.ObservationTimeUTC.dt.date
combined_df['Hour'] = combined_df.ObservationTimeUTC.dt.hour
combined_df['Year'] = combined_df.ObservationTimeUTC.dt.year
combined_df['Month'] = combined_df.ObservationTimeUTC.dt.month
combined_df['Day'] = combined_df.ObservationTimeUTC.dt.day

iso = combined_df['ObservationTimeUTC'].dt.isocalendar()  # Returns a DataFrame with year, week, and weekday
combined_df['iso_year'] = iso['year']
combined_df['iso_week'] = iso['week']
combined_df['iso_weekday'] = iso['day']  # Monday=1, Sunday=7

for col in combined_df.columns:
    if 'no data available' in col:
        combined_df = combined_df.drop(columns = col)

# we want to compare full ISO weeks across years. If current data has incomplete data for the week,
# use previous week as most recent. Data will update Monday morning with previous ISO week.

# week_no: dataframe's lastest iso_week
week_no = combined_df.loc[combined_df.Date == combined_df.Date.max()].iso_week.unique()[0]

most_recent_weekday = (combined_df.loc[
                           (combined_df.iso_year == combined_df.iso_year.max()) & 
                           (combined_df.iso_week == week_no)].iso_weekday.max())

# week_df: pull data from each year for the appropriate iso_week
# data has hourly frequency. most granular YoY comparison.
if most_recent_weekday == 7:        
    week_df = combined_df.loc[combined_df.iso_week == week_no]
else:
    week_df = combined_df.loc[combined_df.iso_week == week_no - 1]

last7days = go.Figure()

# We'll store trace indices for each year so we can control visibility in the dropdown.
year_trace_indices = {}

# Sort the data for consistency.
week_df.sort_values(['ObservationTimeUTC'], inplace=True)

# Iterate over each year and add one trace per category.
unique_years = sorted(week_df['Year'].unique())
for yr in unique_years:
    df_year = week_df[week_df['Year'] == yr]
    # Find unique categories for this year.
    cats = df_year['SiteName'].unique()
    # Initialize a list to store indices for this year.
    trace_indices = []
    for cat in cats:
        df_sub = df_year[df_year['SiteName'] == cat]
        # Add a scatter trace for this category with stackgroup enabled.
        trace = go.Scatter(
            x=df_sub['ObservationTimeUTC'],
            y=df_sub['Value'],
            mode='lines',
            name=cat,
            visible=(yr == unique_years[0]),  # Only the first year's traces are visible initially.
            hovertemplate=f'<b>{cat}</b><br>Air Quality: %{{y:.2f}}<extra></extra>'
        )
        last7days.add_trace(trace)
        trace_indices.append(len(last7days.data) - 1)
    year_trace_indices[yr] = trace_indices

# --- Build Dropdown Buttons ---
buttons = []

# Create a button for each individual year.
for yr in unique_years:
    vis = [False] * len(last7days.data)
    for idx in year_trace_indices[yr]:
        vis[idx] = True
    buttons.append(dict(
        label=str(yr),
        method="update",
        args=[{"visible": vis},
              {"title": f"Air Quality Index - {yr}"}]
    ))

last7days.update_layout(
    updatemenus=[dict(
        active=0,
        buttons=buttons,
        x=0.9,
        xanchor="left",
        y=0.99,
        yanchor="top"
    )],
    yaxis_title="Air Quality (PM2.5) (µg/m3)",
    margin={"r":0, "t":60, "l":0, "b":0},
    height= 600, width = 1000,
    plot_bgcolor='white',
    font_family='Arial'
)

last7days.update_yaxes(range=[0, 40])

grouping = ['Latitude', 'Longitude', 'SiteName', 'iso_year', 'iso_week']
weekly_avg = week_df[['Value'] + grouping].groupby(by = grouping).mean().reset_index()

week_start = week_df.loc[week_df.Year == week_df.Year.max()].Date.min().strftime('%b %d')
week_end = week_df.loc[week_df.Year == week_df.Year.max()].Date.max().strftime('%b %d')

# Create a scattermapbox figure
aqi_map = go.Figure()

unique_years = sorted(weekly_avg['iso_year'].unique())
year_trace_indices = {}

for yr in unique_years:
    df_year = weekly_avg[weekly_avg['iso_year'] == yr]
    trace = go.Scattermapbox(
        lat=df_year['Latitude'],
        lon=df_year['Longitude'],
        text='<b>' + df_year['SiteName'] + ' (' + str(yr) + ')' + ":</b> " + round(df_year['Value'], 2).astype(str),
        mode='markers',
        marker=go.scattermapbox.Marker(
            size=df_year['Value']*3,  # adjust scaling as needed
            color='blue',
            opacity=0.6
        ),
        hoverinfo='text',
        visible=(yr == unique_years[0])
    )
    aqi_map.add_trace(trace)
    year_trace_indices[yr] = [len(aqi_map.data) - 1]

# Dropdown menu buttons for filtering by year
buttons = []
all_visible = [True] * len(aqi_map.data)

for yr in unique_years:
    vis = [False] * len(aqi_map.data)
    for idx in year_trace_indices[yr]:
        vis[idx] = True
    buttons.append(dict(
        label=str(yr),
        method="update",
        args=[{"visible": vis}]
    ))

aqi_map.update_layout(
    title= f"Air Quality Index {week_start} - {week_end}",
    height = 600, width = 800,
    font_family='Arial',
    updatemenus=[dict(
        active=0,
        buttons=buttons,
        x=0.9,
        xanchor="left",
        y=0.975,
        yanchor="top"
    )],
    mapbox_style="carto-positron",
    mapbox_zoom=10.7,
    mapbox_center={"lat": 40.77, "lon": -73.895},
    margin={"r":0, "t":60, "l":0, "b":0}
)

# plot YTD comparisons

all_site_avg = combined_df[['iso_year', 'iso_week', 'Value']].groupby(['iso_year', 'iso_week']).mean().reset_index()
all_site_avg['SiteName'] = 'All Sites (Average)'

# ytd: iso_week average aqi per site per year.
# date range of data is jan 1 - current iso_week (ytd)
ytd = combined_df[['SiteName', 'iso_year', 'iso_week', 'Value']].groupby(['SiteName', 'iso_year', 'iso_week']).mean().reset_index()
ytd = pd.concat([ytd, all_site_avg], ignore_index=True)
ytd = ytd.loc[ytd.iso_week.isin(range(week_no+1))].reset_index(drop=True)

# Get the sorted list of unique years (for consistent color/ordering)
years = sorted(ytd['iso_year'].unique())

site_options = sorted(ytd.SiteName.unique())
# Build traces: one trace per (site option, iso_year) combination.
# We also keep track of which traces belong to which site option.
traces = []
site_trace_indices = {}

colors = {2022: '#E2E0C8', 2023: '#A7B49E', 2024: '#818C78', 2025: '#5C7285'}

for site in site_options:
    indices = []
    for year in years:
        if site == "All Sites (Average)":
            # For average across sites: filter by year and group by iso_week.
            df_filtered = (
                ytd[ytd['iso_year'] == year]
                .groupby('iso_week', as_index=False)['Value']
                .mean()
            )
        else:
            # For a specific site: filter by site and year.
            df_filtered = ytd[(ytd['SiteName'] == site) & (ytd['iso_year'] == year)]
        
        # Create a bar trace for this year.
        trace = go.Bar(
            x=df_filtered['iso_week'],
            y=df_filtered['Value'],
            name=str(year),
            visible=False,  # We'll control visibility via the dropdown.
            marker=dict(color=colors[year]),
            hovertemplate=f'<b>{site} ({year}):</b> %{{y:.2f}} <extra></extra>'
        )
        traces.append(trace)
        indices.append(len(traces) - 1)
    site_trace_indices[site] = indices

# Create the figure with all traces.
fig = go.Figure(data=traces)

# 3. Create the dropdown buttons.
buttons = []
for site in site_options:
    # Build a list for visibility of each trace.
    vis = [False] * len(traces)
    # Set to True only the traces corresponding to this site option.
    for idx in site_trace_indices[site]:
        vis[idx] = True
    buttons.append(
        dict(
            label=site,
            method="update",
            args=[{"visible": vis},
                  {"title": f"Weekly Averages by Year for {site}"}]
        )
    )

# 4. Update the layout with the dropdown menu and set barmode to group.
fig.update_layout(
    updatemenus=[
        dict(
            type="dropdown",
            direction="down",
            buttons=buttons,
            showactive=True,
            x=0.82,
            xanchor="left",
            y=1.1,
            yanchor="top",
            font=dict(size=12)  # Set your desired font size here
        )
    ],
    barmode="group",  # side-by-side bars by year for each ISO week
    xaxis_title="ISO Week",
    yaxis_title="Value",
    title="Weekly Average Air Quality",
    font_family='Arial',
    height=600, width = 1000, plot_bgcolor='white'
)

# 5. Set the initial visible traces (for the first dropdown option).
initial_site = site_options[0]
initial_vis = [False] * len(traces)
for idx in site_trace_indices[initial_site]:
    initial_vis[idx] = True
for i, trace in enumerate(fig.data):
    trace.visible = initial_vis[i]

#####       STREAMLIT APP
st.title('Air Quality Index')

st.markdown('''
    Another benefit of reducing traffic congestion is reducing vehicle emissions. The New York Department of 
    Environmental Conservation (DEC) has rooftop monitors throughout the city which offer hourly readings of 
    PM2.5, harmful pollutants. Monitor availability varies year by year. The BQE, FDR, Mott Haven, Van Wyck, 
    Hamilton Bridge, and SI Expwy sites were added in 2025 using funds from the tolling program.
''')

st.plotly_chart(last7days)
st.caption('''
    This describes daily average PM2.5 levels across all air quality sites for the most recent ISO week. The 
    dropdown menu allows you to compare the same ISO week in previous years.
''')

st.plotly_chart(aqi_map)
st.caption('''
    Map of all air quality rooftop monitoring sites in the city. Size of each point describes the most recent
    ISO's week average for that site.

    * Analysis is limited due to differing sites per year. The best comparison points will be FDR, Williamsburg
    Bridge, and Manhattan Bridge, though they are geographically near each other.
    * All three of the aforementioned sites see a decrease in PM2.5 between 2024 and 2025.
''')

st.plotly_chart(fig)
st.caption('''
    Comparison of YTD air quality per site, as well as an average across all sites. Availability of site data
    varies per year. Toggle year traces on and off for clearer comparisons.

    * In most ISO weeks, air quality has improved (fine particles have decreased) between 2024 and 2025, though
    air quality was already improving between 2023 and 2024.
    * Further analysis required to determine causal relationship between the introduction of congestion pricing
    and reduction in PM2.5.
''')