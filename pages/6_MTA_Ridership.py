# MTA Congestion Pricing Impact Analysis
# Python code to reproduce ITS, DiD, and Counterfactual projections, including saving PNGs

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import statsmodels.api as sm
import streamlit as st

st.title('MTA Ridership')

# Step 1: Load and Preprocess Data
file_path = "data/MTA_Daily_Ridership_and_Traffic__Beginning_2020_20250416.csv"
df = pd.read_csv(file_path)
df['Date'] = pd.to_datetime(df['Date'])
pivot_df = df.pivot(index='Date', columns='Mode', values='Count')
filtered_df = pivot_df[pivot_df.index >= '2024-01-01']

# Define dates
intervention_date = pd.to_datetime("2025-01-05")
highlight_start = pd.to_datetime("2025-01-05")
highlight_end = pd.to_datetime("2025-04-30")
highlight_2024_start = pd.to_datetime("2024-01-01")
highlight_2024_end = pd.to_datetime("2024-04-30")

# Step 2: ITS Analysis Preparation
its_df = filtered_df[['LIRR', 'MNR']].copy()
its_df['LIRR_7d'] = its_df['LIRR'].rolling(window=7).mean()
its_df['MNR_7d'] = its_df['MNR'].rolling(window=7).mean()

# Step 3: ITS Calculation
avg_lirr_2024 = its_df.loc[highlight_2024_start:highlight_2024_end, 'LIRR_7d'].mean()
avg_lirr_2025 = its_df.loc[highlight_start:highlight_end, 'LIRR_7d'].mean()
lirr_pct_change = ((avg_lirr_2025 - avg_lirr_2024) / avg_lirr_2024) * 100

avg_mnr_2024 = its_df.loc[highlight_2024_start:highlight_2024_end, 'MNR_7d'].mean()
avg_mnr_2025 = its_df.loc[highlight_start:highlight_end, 'MNR_7d'].mean()
mnr_pct_change = ((avg_mnr_2025 - avg_mnr_2024) / avg_mnr_2024) * 100

# Step 4: DiD Calculation
comparison_modes = ['LIRR', 'MNR', 'SIR']
jan_apr_2024_all = filtered_df.loc[highlight_2024_start:highlight_2024_end, comparison_modes]
jan_apr_2025_all = filtered_df.loc[highlight_start:highlight_end, comparison_modes]
avg_2024_all = jan_apr_2024_all.mean()
avg_2025_all = jan_apr_2025_all.mean()

# DiD Changes
change_2024_2025 = avg_2025_all - avg_2024_all
did_lirr = change_2024_2025['LIRR'] - change_2024_2025['SIR']
did_mnr = change_2024_2025['MNR'] - change_2024_2025['SIR']
combined_treatment_effect = (did_lirr + did_mnr) / 2

# Step 5: Seasonally Adjusted Counterfactual
jan_apr_2024_lirr = filtered_df.loc["2024-01-01":"2024-04-30", 'LIRR'].reset_index(drop=True)
jan_apr_2024_mnr = filtered_df.loc["2024-01-01":"2024-04-30", 'MNR'].reset_index(drop=True)

dec_2024_lirr_base = filtered_df.loc["2024-12-24":"2024-12-31", 'LIRR'].mean()
dec_2024_mnr_base = filtered_df.loc["2024-12-24":"2024-12-31", 'MNR'].mean()

jan_2024_lirr_base = jan_apr_2024_lirr.mean()
jan_2024_mnr_base = jan_apr_2024_mnr.mean()

lirr_scale = dec_2024_lirr_base / jan_2024_lirr_base
mnr_scale = dec_2024_mnr_base / jan_2024_mnr_base

lirr_counterfactual_2025 = jan_apr_2024_lirr * lirr_scale
mnr_counterfactual_2025 = jan_apr_2024_mnr * mnr_scale

actual_2025_lirr = filtered_df.loc["2025-01-01":"2025-04-30", 'LIRR'].reset_index(drop=True)
actual_2025_mnr = filtered_df.loc["2025-01-01":"2025-04-30", 'MNR'].reset_index(drop=True)
date_range = filtered_df.loc["2025-01-01":"2025-04-30"].index

# Ensure same length
min_length = min(len(date_range), len(lirr_counterfactual_2025))
date_range = date_range[:min_length]
actual_2025_lirr = actual_2025_lirr[:min_length]
actual_2025_mnr = actual_2025_mnr[:min_length]
lirr_counterfactual_2025 = lirr_counterfactual_2025[:min_length]
mnr_counterfactual_2025 = mnr_counterfactual_2025[:min_length]

# Step 6: Plotting and Saving Figures
# ITS Visualization
fig, ax = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
ax[0].plot(its_df.index, its_df['LIRR_7d'], label='LIRR (7-day Avg)', color='blue')
ax[0].axvline(intervention_date, color='red', linestyle='--', label='Policy Start')
ax[0].axvspan(highlight_2024_start, highlight_2024_end, color='blue', alpha=0.1)
ax[0].axvspan(highlight_start, highlight_end, color='orange', alpha=0.2)
ax[0].set_title('LIRR Ridership (7-day Avg) with Jan–Apr Highlights')
ax[0].legend()
ax[0].grid(True)

ax[1].plot(its_df.index, its_df['MNR_7d'], label='MNR (7-day Avg)', color='green')
ax[1].axvline(intervention_date, color='red', linestyle='--', label='Policy Start')
ax[1].axvspan(highlight_2024_start, highlight_2024_end, color='blue', alpha=0.1)
ax[1].axvspan(highlight_start, highlight_end, color='orange', alpha=0.2)
ax[1].set_title('MNR Ridership (7-day Avg) with Jan–Apr Highlights')
ax[1].legend()
ax[1].grid(True)

plt.xlabel('Date')
plt.tight_layout()
# plt.savefig("ITS_LIRR_MNR.png")
plt.show()

# DiD Bar Chart
fig, ax = plt.subplots(figsize=(8, 6))
x = np.arange(len(comparison_modes))
bar_width = 0.35
ax.bar(x - bar_width/2, avg_2024_all, bar_width, label='2024')
ax.bar(x + bar_width/2, avg_2025_all, bar_width, label='2025')
ax.set_xticks(x)
ax.set_xticklabels(comparison_modes)
ax.set_ylabel('Average Daily Riders (Jan–Apr)')
ax.set_title('Difference-in-Differences: LIRR & MNR vs SIR')
ax.legend()
plt.grid(axis='y', linestyle='--', alpha=0.6)
plt.tight_layout()
plt.savefig("DiD_LIRR_MNR_SIR.png")
plt.show()

# Counterfactual Projection Plot
fig, ax = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
ax[0].plot(date_range, actual_2025_lirr, label='LIRR Actual', color='blue')
ax[0].plot(date_range, lirr_counterfactual_2025, label='Seasonal Counterfactual', linestyle='--', color='gray')
ax[0].set_title('LIRR: Actual vs Seasonal Counterfactual')
ax[0].legend()
ax[0].grid(True)

ax[1].plot(date_range, actual_2025_mnr, label='MNR Actual', color='green')
ax[1].plot(date_range, mnr_counterfactual_2025, label='Seasonal Counterfactual', linestyle='--', color='gray')
ax[1].set_title('MNR: Actual vs Seasonal Counterfactual')
ax[1].legend()
ax[1].grid(True)

plt.xlabel('Date')
plt.tight_layout()
# plt.savefig("Counterfactual_LIRR_MNR.png")
plt.show()
