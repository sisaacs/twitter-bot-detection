import os
import sys

import numpy as np
import pandas as pd

import streamlit as st

# pages
# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import graph_explorer

# TODO: Add more pages later
PAGES = [
    'GRAPH EXPLORER',
]

def run_ui():

    st.set_page_config(
        page_title="Twitter Bot Analysis",
        page_icon="🏠",
        initial_sidebar_state="expanded",
    )

    st.sidebar.title("Twitter Bot Analysis")
    if st.session_state.page:
        page=st.sidebar.radio('Navigation', PAGES, index=st.session_state.page)
    else:
        page=st.sidebar.radio('Navigation', PAGES, index=0)

    st.experimental_set_query_params(page=page)

    if page == 'GRAPH EXPLORER':
        st.sidebar.write("""
            ## Overview
            Use this page to explore the network of Twitter accounts as per the uploaded dataset. 
        """)

        graph_explorer.run_ui()

if __name__ == "__main__":
    
    url_params = st.experimental_get_query_params()
    if 'loaded' not in st.session_state:
        if len(url_params.keys()) == 0:
            st.experimental_set_query_params(page='GRAPH EXPLORER')
            url_params = st.experimental_get_query_params()

        st.session_state.page = PAGES.index(url_params['page'][0])
    
    run_ui()