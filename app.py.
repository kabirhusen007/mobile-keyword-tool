import streamlit as st
import requests
import pandas as pd

# Mobile-friendly page configuration
st.set_page_config(page_title="Keyword Metrics Tool", page_icon="🔍", layout="wide")

st.title("🔍 Keyword Research Tool")
st.caption("Personal mobile app powered by DataForSEO")

# --- Sidebar Configuration ---
st.sidebar.header("⚙️ API & Settings")

# Automatically pull credentials from Streamlit secrets if set
default_login = st.secrets.get("DATAFORSEO_LOGIN", "") if "DATAFORSEO_LOGIN" in st.secrets else ""
default_password = st.secrets.get("DATAFORSEO_PASSWORD", "") if "DATAFORSEO_PASSWORD" in st.secrets else ""

api_login = st.sidebar.text_input("DataForSEO Login", value=default_login, type="password")
api_password = st.sidebar.text_input("DataForSEO Password", value=default_password, type="password")

LOCATIONS = {
    "United States": 2840,
    "United Kingdom": 2826,
    "Canada": 2124,
    "Australia": 2036,
    "Germany": 2276,
    "India": 2356,
}

selected_country = st.sidebar.selectbox("Target Country", list(LOCATIONS.keys()))
location_code = LOCATIONS[selected_country]

# --- API Functions ---
def fetch_keyword_overview(login, password, keyword, location):
    url = "https://api.dataforseo.com/v3/dataforseo_labs/google/keyword_overview/live"
    payload = [{
        "keywords": [keyword],
        "location_code": location,
        "language_code": "en"
    }]
    response = requests.post(url, auth=(login, password), json=payload)
    return response.json()

def fetch_related_keywords(login, password, keyword, location):
    url = "https://api.dataforseo.com/v3/dataforseo_labs/google/related_keywords/live"
    payload = [{
        "keyword": keyword,
        "location_code": location,
        "language_code": "en",
        "limit": 10
    }]
    response = requests.post(url, auth=(login, password), json=payload)
    return response.json()

# --- Main UI ---
target_keyword = st.text_input("Enter Target Keyword", placeholder="e.g. android app development")

if st.button("Search Metrics", type="primary", use_container_width=True):
    if not api_login or not api_password:
        st.error("Please provide your DataForSEO login and password in the sidebar (or via Streamlit Secrets).")
    elif not target_keyword.strip():
        st.warning("Please enter a keyword to search.")
    else:
        with st.spinner("Fetching data from DataForSEO..."):
            try:
                # 1. Fetch Keyword Overview
                res = fetch_keyword_overview(api_login, api_password, target_keyword.strip(), location_code)
                tasks = res.get("tasks", [])
                
                if tasks and tasks[0].get("result"):
                    items = tasks[0]["result"][0].get("items", [])
                    if items:
                        item = items[0]
                        info = item.get("keyword_info", {}) or {}
                        props = item.get("keyword_properties", {}) or {}
                        intent = item.get("search_intent_info", {}) or {}

                        volume = info.get("search_volume", 0) or 0
                        cpc = info.get("cpc", 0.0) or 0.0
                        kd = props.get("keyword_difficulty", 0) or 0
                        main_intent = (intent.get("main_intent") or "N/A").capitalize()

                        st.subheader(f"Overview: **{target_keyword}**")

                        # Display key metrics in responsive cards
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Search Volume", f"{volume:,} / mo")
                            kd_label = "Easy" if kd < 30 else ("Moderate" if kd < 60 else "Hard")
                            st.metric("Difficulty (KD)", f"{kd} / 100", delta=kd_label)
                        
                        with col2:
                            st.metric("Est. CPC", f"${cpc:.2f}")
                            st.metric("Search Intent", main_intent)
                    else:
                        st.warning("No metrics found for this specific keyword.")
                else:
                    st.error("API error or invalid credentials. Check your DataForSEO login details.")

                st.markdown("---")

                # 2. Fetch Related Keywords
                rel_res = fetch_related_keywords(api_login, api_password, target_keyword.strip(), location_code)
                rel_tasks = rel_res.get("tasks", [])
                
                if rel_tasks and rel_tasks[0].get("result"):
                    rel_items = rel_tasks[0]["result"][0].get("items", [])
                    if rel_items:
                        st.subheader("💡 Related Keywords")
                        table_data = []
                        for r in rel_items:
                            k_data = r.get("keyword_data", {}) or {}
                            k_info = k_data.get("keyword_info", {}) or {}
                            k_props = k_data.get("keyword_properties", {}) or {}
                            
                            table_data.append({
                                "Keyword": k_data.get("keyword"),
                                "Volume": k_info.get("search_volume", 0) or 0,
                                "KD": k_props.get("keyword_difficulty", 0) or 0,
                                "CPC ($)": k_info.get("cpc", 0.0) or 0.0
                            })
                        
                        df = pd.DataFrame(table_data)
                        st.dataframe(df, use_container_width=True)

            except Exception as e:
                st.error(f"Error executing search: {e}")
