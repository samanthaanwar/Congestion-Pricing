import streamlit as st

st.set_page_config(
    page_title="NYC Congestion Pricing",
    page_icon="🚗",
)

st.write("# Preliminary Effects of Congestion Pricing in New York City 🚗🏙️")
st.write('#### Project by Sam Anwar, Ishraq Khan, and Devraj Singhania')
st.write('#### Data Science & Public Policy | Columbia University')

st.markdown(
    """
    New York City introduced congestion pricing on January 5, 2025, charging most motorists $9 to travel 
    through its Congestion Relief Zone (CRZ) during peak hours. The hope is that this additional cost 
    will encourage people to choose mass transit and subsequently, decrease traffic, lower carbon emissions, 
    and improve safety for pedestrians. Moreover, the revenue generated from the congestion pricing will 
    fund MTA projects to improve transit in the city.

    This site aims to evaluate the impact of congestion pricing in New York City by analyzing transportation 
    patterns before and after policy implementation. Data is from Open Data NYC. Findings will provide 
    evidence-based insights to inform urban transportation policies and sustainability efforts in 
    metropolitan areas worldwide.

    """
)

st.link_button("Learn More", "https://congestionreliefzone.mta.info/tolling")