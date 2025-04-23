import requests
import pandas as pd
import streamlit as st
import altair as alt

# Fetch data from NYC Open Data API
@st.cache_data(ttl=3600) # Cache data for 1 hour
def load_data(BASE_URL, params):
    try:
        response = requests.get(BASE_URL, params=params)
        response.raise_for_status() # Raise an exception for bad status codes
        data = response.json()
        if not data:
            st.error("No data received from the API.")
            return pd.DataFrame()
        crash_df = pd.DataFrame(data)
        return crash_df
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching data from API: {e}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"An error occurred: {e}")
        return pd.DataFrame()

def plot_tlc_metric(df, value_col, title, ylabel):
    month_order = ['January', 'February', 'March']

    # get min & max values for y-scale
    min_val = df[value_col].min()
    max_val = df[value_col].max()

    # Altair line chart
    chart = alt.Chart(df).mark_line(point=True).encode(
        x=alt.X('Month:N', sort=month_order, title='Month'),
        y=alt.Y(f'{value_col}:Q', title=ylabel, scale=alt.Scale(domain=[min_val - 0.1 * min_val, max_val + 0.1 * max_val])),
        color=alt.Color('Year:N', scale=alt.Scale(scheme='tableau10'), title='Year'),
        tooltip=['Month', 'Year', alt.Tooltip(value_col, title=ylabel)]
    ).properties(
        #title=title,
        width=600,
        height=350
    ).interactive()

    return chart

def preprocess_tlc_data(df, metrics, license_types):
    # specifiy data types 
    df['month_year'] = pd.to_datetime(df['month_year'])
    for col in metrics:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
    # filter data to Jan/Feb/March 2024 & 2025
    df_filtered = df[df['month_year'].dt.month.isin([1, 2, 3]) & df['month_year'].dt.year.isin([2024, 2025])].copy()
    df_filtered['Month'] = df_filtered['month_year'].dt.strftime('%B')
    df_filtered['Year'] = df_filtered['month_year'].dt.year



            