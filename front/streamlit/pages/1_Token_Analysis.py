import streamlit as st
import pandas as pd
import plotly.express as px

# Import shared utilities
from utils.streamlit_config import configure_page

configure_page(page_title="Token Analysis", page_icon="📊", layout="centered")

st.title("Token Analysis")
