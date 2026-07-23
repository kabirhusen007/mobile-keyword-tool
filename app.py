import csv
import io
import string
import time
import urllib.parse
import pandas as pd
import requests
import streamlit as st

# --- STREAMLIT PAGE CONFIG ---
st.set_page_config(
    page_title="Free Keyword Research Tool & Trends",
    page_icon="🔍",
    layout="wide",
)

# --- ADVANCED DESIGNER CSS INJECTION ---
st.markdown(
    """
    <style>
    /* 1. Global Page Styling (Theme & Fonts) */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
    
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #0F172A; /* Premium Dark Sky */
        color: #F1F5F9;
        font-family: 'Inter', sans-serif !important;
    }
    
    /* 2. Global Border Radius & Modern Accents */
    div[data-testid="stTextInput"], 
    div[data-testid="stCheckbox"], 
    button, 
    div.stDataFrame,
    [data-testid="stMetricValue"],
    .trend-card,
    .success-card,
    .dl-btn-container {
        border-radius: 12px !important;
        overflow: hidden;
    }

    /* 3. Header Section (Center-aligned, modern font) */
    .header-container {
        text-align: center;
        margin-bottom: 30px;
    }
    .main-header { 
        font-family: 'Inter', sans-serif;
        font-size: 2.5rem; 
        color: #F8FAFC; 
        font-weight: 800; 
        margin-bottom: 0px;
        background: -webkit-linear-gradient(#3B82F6, #10B981); /* Gradient Accent */
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .sub-header { 
        font-family: 'Inter', sans-serif;
        font-size: 1.1rem; 
        color: #94A3B8; 
        font-weight: 400;
        margin-top: -10px;
        margin-bottom: 10px;
    }

    /* 4. The Inputs & Checkbox */
    div[data-testid="stTextInput"] > div[data-testid="stMarkdownContainer"] p {
        font-weight: 600;
        color: #CBD5E1;
        margin-bottom: 5px;
    }
    div[data-testid="stTextInput"] input {
        background-color: rgba(30, 41, 59, 0.7); /* Translucent input */
        color: #F1F5F9;
        border: 1px solid #334155;
        height: 3em;
        font-size: 1rem;
    }
    div[data-testid="stTextInput"] input:focus {
        border-color: #3B82F6;
        box-shadow: 0 0 10px rgba(59, 130, 246, 0.4);
    }
    label[data-testid="stWidgetLabel"] p {
        font-weight: 600;
        color: #CBD5E1;
    }
    div[data-testid="stCheckbox"] > label > div[data-testid="stMarkdownContainer"] p {
        color: #E2E8F0;
        font-weight: 400;
    }

    /* 5. Main Action Button (Primary Blue Gradient) */
    div[data-testid="stHorizontalBlock"] .stButton>button { 
        background: linear-gradient(135deg, #2563EB, #1D4ED8); /* Action Gradient */
        color: white; 
        border: none;
        border-radius: 8px !important;
        height: 3em; 
        font-weight: 700; 
        width: 100%; 
        font-size: 1rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        box-shadow: 0 4px 10px rgba(37, 99, 235, 0.3);
        transition: all 0.2s ease-in-out;
    }
    div[data-testid="stHorizontalBlock"] .stButton>button:hover { 
        background: linear-gradient(135deg, #3B82F6, #2563EB); /* Hover State */
        box-shadow: 0 6px 15px rgba(37, 99, 235, 0.5);
        transform: translateY(-1px);
    }

    /* 6. Cards & Containers (Glassmorphism & Accents) */
    .trend-card {
        background-color: rgba(30, 41, 59, 0.7); /* Translucent & Blurry */
        padding: 25px;
        border-radius: 12px;
        border: 1px solid #334155;
        margin-top: 15px;
        margin-bottom: 25px;
        box-shadow: 0 10px 30px rgba(15, 23, 42, 0.3);
        backdrop-filter: blur(10px);
    }
    .trend-link {
        display: inline-block;
        background: linear-gradient(135deg, #3B82F6, #10B981); /* Unique Card Gradient */
        color: white !important;
        padding: 12px 24px;
        border-radius: 8px;
        text-decoration: none;
        font-weight: 700;
        margin-top: 15px;
        transition: all 0.2s ease-in-out;
    }
    .trend-link:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 15px rgba(59, 130, 246, 0.4);
    }
    
    .success-card {
        background-color: rgba(16, 185, 129, 0.15); /* Translucent Green */
        color: #10B981;
        border: 1px solid #10B981;
        padding: 15px 20px;
        border-radius: 12px;
        margin-bottom: 20px;
        font-weight: 600;
    }

    /* 7. Download Button & CSV Icon */
    .dl-btn-container .stDownloadButton {
        border-radius: 12px !important;
    }
    .dl-btn-container .stDownloadButton>button {
        background-color: rgba(30, 41, 59, 0.7);
        color: #CBD5E1;
        border: 1px solid #334155;
        height: 2.8em;
        font-weight: 600;
    }
    .dl-btn-container .stDownloadButton>button:hover {
        background-color: rgba(51, 65, 85, 0.9);
        border-color: #CBD5E1;
        color: #F8FAFC;
    }

    /* 8. Modern DataFrame Styling */
    div.stDataFrame {
        border: 1px solid #334155 !important;
        border-radius: 12px;
        overflow: hidden;
    }
    div.stDataFrame [data-testid="stHeaderCell"] p {
        color: # CBD5E1 !important;
        font-weight: 700 !important;
    }

    /* 9. Progress Bar Modern Styling */
    div.stProgress > div > div > div > div {
        background-image: linear-gradient(135deg, #3B82F6, #10B981) !important;
    }

    </style>
""",
    unsafe_allow_html=True,
)


def get_google_suggest(query):
    """Scrapes live autocomplete queries directly from Google's endpoint."""
    encoded_query = urllib.parse.quote(query)
    url = f"http://suggestqueries.google.com/complete/search?client=chrome&q={encoded_query}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data[1]
    except Exception:
        pass
    return []


def estimate_keyword_difficulty(keyword):
    """Calculates estimated Keyword Difficulty based on word count intent."""
    words = keyword.split()
    word_count = len(words)

    if word_count >= 5:
        return "🟢 Very Easy", "15%"
    elif word_count == 4:
        return "🟢 Easy", "28%"
    elif word_count == 3:
        return "🟡 Moderate", "52%"
    elif word_count == 2:
        return "🟠 Hard", "75%"
    else:
        return "🔴 Very Hard", "90%"


def generate_keywords(seed, include_questions=True):
    """Loops through A-Z + Question modifiers to extract 100s of long-tail queries."""
    results = set()

    base_suggestions = get_google_suggest(seed)
    results.update(base_suggestions)

    progress_bar = st.progress(0)
    status_text = st.empty()

    letters = list(string.ascii_lowercase)
    total_steps = len(letters) + (7 if include_questions else 0)
    current_step = 0

    for letter in letters:
        current_step += 1
        status_text.text(f"✨ Scanning alphabet... ({letter.upper()})")
        progress_bar.progress(current_step / total_steps)

        query = f"{seed} {letter}"
        suggestions = get_google_suggest(query)
        results.update(suggestions)
        time.sleep(0.02)

    if include_questions:
        question_words = [
            "how",
            "what",
            "why",
            "where",
            "best",
            "vs",
            "for beginners",
        ]
        for q_word in question_words:
            current_step += 1
            status_text.text(f"💡 Extracting questions... ({q_word})")
            progress_bar.progress(current_step / total_steps)

            query = f"{q_word} {seed}"
            suggestions = get_google_suggest(query)
            results.update(suggestions)
            time.sleep(0.02)

    progress_bar.empty()
    status_text.empty()

    return sorted(list(results))


# --- UI LAYOUT ---
st.markdown(
    """
    <div class="header-container">
        <h1 class="main-header">Free Keyword Research Tool & Trends</h1>
        <p class="sub-header">Live Google Autocomplete Extractor, KD Estimator & Interactive Trend Analysis</p>
    </div>
    """,
    unsafe_allow_html=True,
)

col_input, col_action = st.columns([4, 1.2])

with col_input:
    seed_keyword = st.text_input(
        "Enter Seed Keyword:",
        placeholder="e.g., best mobile under 20k, solar panel, inverter ac",
    )

with col_action:
    st.write("##") # Spacer
    include_questions = st.checkbox("Include Questions", value=True)
    st.write("##") # Spacer
    search_button = st.button("Search Keywords ✨")

st.markdown("<br>", unsafe_allow_html=True)

if search_button and seed_keyword.strip():
    clean_seed = seed_keyword.strip()

    with st.spinner("Scraping live search queries from Google..."):
        keywords = generate_keywords(
            clean_seed, include_questions=include_questions
        )

    if keywords:
        # Success Notification Card
        st.markdown(
            f"""
            <div class="success-card">
                🎉 Found {len(keywords)} long-tail keywords for '{clean_seed}'!
            </div>
            """,
            unsafe_allow_html=True,
        )

        # 1. Google Trends Quick Access Card (Glassmorphism + Accent Gradient Button)
        trends_url = f"https://trends.google.com/trends/explore?q={urllib.parse.quote(clean_seed)}"
        st.markdown(
            f"""
            <div class="trend-card">
                <h3 style="margin-top:0; color:#F8FAFC; font-weight:700;">📈 Search Interest Trend: '{clean_seed}'</h3>
                <p style="color:#CBD5E1; font-size: 0.95rem; margin-top:-5px;">
                    Analyze regional interest, 12-month popularity trajectory, and breakout topics directly on Google Trends.
                </p>
                <a href="{trends_url}" target="_blank" class="trend-link">
                    🚀 View Live Graph on Google Trends ↗
                </a>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<br>", unsafe_allow_html=True)

        # 2. Build Keyword Results Table
        table_data = []
        for kw in keywords:
            difficulty_label, kd_score = estimate_keyword_difficulty(kw)
            table_data.append(
                {
                    "Keyword": kw,
                    "Estimated KD": difficulty_label,
                    "KD Score": kd_score,
                    "Words": len(kw.split()),
                }
            )

        # 3. CSV Download Setup
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Keyword", "Estimated KD", "KD Score", "Word Count"])
        for row in table_data:
            writer.writerow(
                [
                    row["Keyword"],
                    row["Estimated KD"],
                    row["KD Score"],
                    row["Words"],
                ]
            )
        csv_data = output.getvalue()

        col_dl1, col_list_label = st.columns([1, 4])
        with col_dl1:
            st.markdown('<div class="dl-btn-container">', unsafe_allow_html=True)
            st.download_button(
                label="📥 Download CSV",
                data=csv_data,
                file_name=f"{clean_seed.replace(' ', '_')}_keywords.csv",
                mime="text/csv",
            )
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("### Extracted Keyword List")
        st.dataframe(table_data, use_container_width=True, height=520)

    else:
        st.error("No keywords found. Try a different seed keyword.")