import streamlit as st
import requests
import pandas as pd

# --- Data Fetching ---
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
