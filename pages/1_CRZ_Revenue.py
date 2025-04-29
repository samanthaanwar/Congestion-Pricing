import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
import numpy as np

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'data'

# Load multiple files
budget = pd.read_excel(DATA_DIR / 'arb_budget.xlsx')
entries = pd.read_csv(DATA_DIR / 'vehicle_entries_grouped.csv')

# Sankey Diagram

# Step 1: Get all labels (already done)
labels = pd.unique(budget[["Category 1", "Category 2", "Category 3"]].values.ravel()).tolist()
label_map = {label: i for i, label in enumerate(labels)}

# Step 2: Compute total flow per node (both incoming and outgoing)
n_nodes = len(labels)
incoming_values = np.zeros(n_nodes)
outgoing_values = np.zeros(n_nodes)
# Link: Category 1 → Category 2
df_l1_l2 = budget.groupby(["Category 1", "Category 2"])["Budget"].sum().reset_index()
df_l1_l2["source"] = df_l1_l2["Category 1"].map(label_map)
df_l1_l2["target"] = df_l1_l2["Category 2"].map(label_map)

# Only keep descriptions for valid Category 2 → Category 3 flows
df_valid = budget.dropna(subset=["Category 3"]).copy()
df_valid["source"] = df_valid["Category 2"].map(label_map)
df_valid["target"] = df_valid["Category 3"].map(label_map)

def insert_line_breaks(text, max_len=30):
    words = text.split()
    lines, current = [], ""
    for word in words:
        if len(current) + len(word) + 1 > max_len:
            lines.append(current)
            current = word
        else:
            current += (" " if current else "") + word
    lines.append(current)
    return "<br>".join(lines)

df_valid["Description"] = df_valid["Description"].apply(insert_line_breaks)

# Use empty strings for the Category 1 → 2 links (no descriptions)
df_l1_l2["Description"] = ""

# Combine sources, targets, values, and descriptions
source_nodes = pd.concat([df_l1_l2["source"], df_valid["source"]])
target_nodes = pd.concat([df_l1_l2["target"], df_valid["target"]])
values = pd.concat([df_l1_l2["Budget"], df_valid["Budget"]])
hover_text = pd.concat([df_l1_l2["Description"], df_valid["Description"]])

for t, v in zip(target_nodes, values):
    incoming_values[t] += v
for s, v in zip(source_nodes, values):
    outgoing_values[s] += v

# Final node budget: if no incoming, use outgoing
node_budget_values = [
    incoming_values[i] if incoming_values[i] > 0 else outgoing_values[i]
    for i in range(n_nodes)
]

def format_value(val):
    if val >= 1e9:
        return f"${val / 1e9:.2f}B"
    elif val >= 1e6:
        return f"${val / 1e6:.0f}M"
    else:
        return f"${val:,.0f}"
    
node_hover_text = [
    f"<b>{label}</b><br>Total Budget: {format_value(node_budget_values[i])}"
    for i, label in enumerate(labels)
]

# Sankey plot
sankey = go.Figure(data=[go.Sankey(
    arrangement='snap',
    node=dict(
        pad=10,
        thickness=20,
        line=dict(color="black", width=0.5),
        label=labels,
        customdata=node_hover_text,
        hovertemplate="%{customdata}<extra></extra>",
    ),
    link=dict(
        source=source_nodes,
        target=target_nodes,
        value=values,
        customdata=hover_text,
        hovertemplate='%{customdata}<extra></extra>'
    )
)])

sankey.update_layout(font_family = 'Arial', height=600, font_size=14)

st.title('CRZ Revenue')
mta_info = 'https://www.mta.info/fares-tolls/tolls/congestion-relief-zone/better-transit'
st.markdown('''
    Tolls collected in the Congestion Relief Zone will be used to fund a wide portfolio of transit 
    projects. 80\% of revenue connected is obligated to capital improvements in the subway and bus 
    system, plus an additional \$1.5 billion each to the Long Island Rail Road and Metro-North.
''')

st.markdown('''
    The budget numbers in the sankey diagram are merely representative to demonstrate a goal of 
    improved transparency from the MTA. For more information, please see [this link](%s).
''' % mta_info)

st.plotly_chart(sankey)

toll_data = [
    ['Passenger Cars & Vans', '$9.00', '$2.25', ''], 
    ['Single-Unit Trucks', '$14.40', '$3.60', ''],
    ['Multi-Unit Trucks', '$21.60', '$5.40', ''],
    ['Sightseeing Buses', '$21.60', '$5.40', ''],
    ['Other Buses', '$14.40', '$3.60', ''],
    ['Motorcycles', '$4.50', '$1.05'],
    ['TLC Taxi', '', '', '$0.75'],
    ['App-based FHV', '', '', '$1.50']
]

toll_rates = pd.DataFrame(toll_data, columns=['Vehicle Class', 'Peak', 'Overnight', 'Per Trip']).set_index('Vehicle Class')

st.markdown('''
    Revenue estimates from the cordon pricing program are below. Actual revenue numbers have not yet been
    released, so we use a set of assumptions on top of the table of rates below. 
''')

st.table(toll_rates)

st.markdown('''
    **Assumptions**
 
    - Sightseeing buses make up 5\% of total buses. Bus revenue estimates are calculated with a weighted
    average between the two rates of \$14.76 / \$3.69.
    - 25/75 split between Taxis and App-based FHV for a weighted average of \$1.31 per car entering the zone.
    We also assume an average of 10 rides per vehicle per for an estimated revenue rate of \$13.10.
    - Vehicles receive credits for entering and leaving the CRZ via a tunnel, and some vehicles are part of
    a low-income program which offers 50\% off rates after the vehicle's 11th ride per month. We reduce 
    revenue estimates by 15% to reflect these conditions.
    - We multiply revenue by 80% to reflect mandate from Article 44-C that 80\% of revenue be attributed
    to MTA projects.
''')

revenue_sum = entries['Estimated Revenue'].sum()
st.subheader(f'Estimated Revenue (as of 4/12/25): ${revenue_sum:,.0f}')

view_choice = st.selectbox('Select view', ['By Vehicle Class', 'By Period'])

entries['Toll Date'] = pd.to_datetime(entries['Toll Date'])

if view_choice == 'By Vehicle Class':
    rev_group = (entries
                    .groupby(['Toll Date', 'Day of Week', 'Toll Week', 'Vehicle Class'])['Estimated Revenue']
                    .sum()
                    .reset_index())
    line_plot = px.bar(rev_group, x = 'Toll Date', y = 'Estimated Revenue', 
                       color = 'Vehicle Class',
                       custom_data = ['Vehicle Class'],
                       category_orders={'Vehicle Class': ['Passenger Cars & Vans', 'TLC Taxi/FHV',
                                                          'Single-Unit Trucks', 'Buses', 'Multi-Unit Trucks',
                                                          'Motorcycles']})
    line_plot.update_layout(xaxis_title='', font_family='Arial', height = 500)
    line_plot.update_traces(hovertemplate = '''
                            <b>%{x}</b><br><br><b>%{customdata[0]}</b>
                            <br>$%{y:,.2f}<extra></extra>''')

else:
    rev_group = (entries
                    .groupby(['Toll Date', 'Day of Week', 'Toll Week', 'Time Period'])['Estimated Revenue']
                    .sum()
                    .reset_index())
    line_plot = px.bar(rev_group, x = 'Toll Date', y = 'Estimated Revenue', 
                       color = 'Time Period', custom_data = ['Time Period'],
                       category_orders = {'Time Period': ['Peak', 'Overnight']})
    line_plot.update_layout(xaxis_title='', font_family='Arial', height = 500)
    line_plot.update_traces(hovertemplate = '''
                            <b>%{x}</b><br><br><b>%{customdata[0]}</b>
                            <br>$%{y:,.2f}<extra></extra>''')

st.plotly_chart(line_plot)