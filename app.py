import csv
import io
import re
import string
import time
import urllib.parse
from collections import defaultdict
import pandas as pd
import requests
import streamlit as st

# --- STREAMLIT PAGE CONFIG ---
st.set_page_config(
    page_title="Free Keyword Research Tool & Trends",
    page_icon="🔍",
    layout="wide",
)

# Initialize Session Search History
if "search_history" not in st.session_state:
    st.session_state["search_history"] = []

# --- ADVANCED DESIGNER CSS INJECTION ---
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
    
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #0F172A;
        color: #F1F5F9;
        font-family: 'Inter', sans-serif !important;
    }
    
    div[data-testid="stTextInput"], 
    button, 
    div.stDataFrame,
    .trend-card,
    .success-card {
        border-radius: 12px !important;
        overflow: hidden;
    }

    .header-container { text-align: center; margin-bottom: 30px; }
    .main-header { 
        font-size: 2.5rem; 
        font-weight: 800; 
        background: -webkit-linear-gradient(#3B82F6, #10B981); 
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .sub-header { font-size: 1.1rem; color: #94A3B8; font-weight: 400; }

    div[data-testid="stTextInput"] input {
        background-color: rgba(30, 41, 59, 0.7);
        color: #F1F5F9;
        border: 1px solid #334155;
        height: 3em;
    }

    div[data-testid="stHorizontalBlock"] .stButton>button { 
        background: linear-gradient(135deg, #2563EB, #1D4ED8); 
        color: white; 
        border: none;
        height: 3em; 
        font-weight: 700; 
        text-transform: uppercase;
        box-shadow: 0 4px 10px rgba(37, 99, 235, 0.3);
    }

    .trend-card {
        background-color: rgba(30, 41, 59, 0.7);
        padding: 25px;
        border: 1px solid #334155;
        margin-bottom: 25px;
        backdrop-filter: blur(10px);
    }
    .trend-link {
        display: inline-block;
        background: linear-gradient(135deg, #3B82F6, #10B981);
        color: white !important;
        padding: 12px 24px;
        border-radius: 8px;
        text-decoration: none;
        font-weight: 700;
        margin-top: 15px;
    }
    
    .success-card {
        background-color: rgba(16, 185, 129, 0.15);
        color: #10B981;
        border: 1px solid #10B981;
        padding: 15px 20px;
        margin-bottom: 20px;
        font-weight: 600;
    }
    </style>
""",
    unsafe_allow_html=True,
)


# --- HELPER FUNCTIONS ---
def get_google_suggest(query):
    encoded_query = urllib.parse.quote(query)
    url = f"http://suggestqueries.google.com/complete/search?client=chrome&q={encoded_query}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            return response.json()[1]
    except Exception:
        pass
    return []


def detect_search_intent(keyword):
    """Heuristic logic to classify search intent."""
    kw = keyword.lower()

    transactional = [
        "price",
        "buy",
        "cost",
        "cheap",
        "shop",
        "sale",
        "discount",
        "bd",
        "store",
        "online",
        "order",
    ]
    informational = [
        "how",
        "what",
        "why",
        "where",
        "guide",
        "tips",
        "tutorial",
        "meaning",
        "review",
        "difference",
        "wiring",
        "setup",
    ]
    commercial = ["best", "top", "vs", "compare", "rating", "review", "brand"]

    if any(word in kw for word in transactional):
        return "💳 Transactional"
    elif any(word in kw for word in commercial):
        return "🔍 Commercial"
    elif any(word in kw for word in informational):
        return "ℹ️ Informational"
    else:
        return "🌐 General / Navigational"


def cluster_keywords(keywords, seed):
    """Clusters keywords into groups based on common repeating root words."""
    clusters = defaultdict(list)
    stop_words = set(seed.lower().split()).union(
        {"in", "of", "for", "and", "to", "the", "a", "is", "with", "bd"}
    )

    for kw in keywords:
        words = re.findall(r"\w+", kw.lower())
        meaningful_words = [w for w in words if w not in stop_words]

        if meaningful_words:
            primary_topic = meaningful_words[0].capitalize()
            clusters[f"Topic: {primary_topic}"].append(kw)
        else:
            clusters["General Variations"].append(kw)

    return clusters


def estimate_keyword_difficulty(keyword):
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
    results = set()
    results.update(get_google_suggest(seed))

    progress_bar = st.progress(0)
    status_text = st.empty()

    letters = list(string.ascii_lowercase)
    total_steps = len(letters) + (7 if include_questions else 0)
    current_step = 0

    for letter in letters:
        current_step += 1
        status_text.text(f"✨ Scanning alphabet... ({letter.upper()})")
        progress_bar.progress(current_step / total_steps)
        results.update(get_google_suggest(f"{seed} {letter}"))
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
            results.update(get_google_suggest(f"{q_word} {seed}"))
            time.sleep(0.02)

    progress_bar.empty()
    status_text.empty()

    return sorted(list(results))


# --- SIDEBAR (SEARCH HISTORY) ---
with st.sidebar:
    st.title("📜 Search History")
    if st.session_state["search_history"]:
        for past_search in reversed(st.session_state["search_history"]):
            st.code(past_search, language="text")
        if st.button("Clear History"):
            st.session_state["search_history"] = []
            st.rerun()
    else:
        st.caption("No previous searches in this session.")


# --- UI LAYOUT ---
st.markdown(
    """
    <div class="header-container">
        <h1 class="main-header">Free Keyword Research Tool & Trends</h1>
        <p class="sub-header">Autocomplete Extractor, Search Intent AI, Keyword Clustering & Trends</p>
    </div>
    """,
    unsafe_allow_html=True,
)

col_input, col_action = st.columns([4, 1.2])

with col_input:
    seed_keyword = st.text_input(
        "Enter Seed Keyword:",
        placeholder="e.g., best mobile under 20k, solar panel bd, inverter ac",
    )

with col_action:
    st.write("##")
    include_questions = st.checkbox("Include Questions", value=True)
    st.write("##")
    search_button = st.button("Search Keywords ✨")

if search_button and seed_keyword.strip():
    clean_seed = seed_keyword.strip()

    # Save to Session History
    if clean_seed not in st.session_state["search_history"]:
        st.session_state["search_history"].append(clean_seed)

    with st.spinner("Extracting keywords, intent, and clusters..."):
        keywords = generate_keywords(
            clean_seed, include_questions=include_questions
        )

    if keywords:
        st.markdown(
            f"""
            <div class="success-card">
                🎉 Discovered {len(keywords)} long-tail keywords for '{clean_seed}'!
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Google Trends Card
        trends_url = f"https://trends.google.com/trends/explore?q={urllib.parse.quote(clean_seed)}"
        st.markdown(
            f"""
            <div class="trend-card">
                <h3 style="margin-top:0; color:#F8FAFC;">📈 Search Interest Trend: '{clean_seed}'</h3>
                <p style="color:#CBD5E1; font-size: 0.95rem;">
                    Analyze regional interest, 12-month popularity trajectory, and breakout topics directly on Google Trends.
                </p>
                <a href="{trends_url}" target="_blank" class="trend-link">
                    🚀 View Live Graph on Google Trends ↗
                </a>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Build Main Data Table
        table_data = []
        for kw in keywords:
            difficulty_label, kd_score = estimate_keyword_difficulty(kw)
            intent = detect_search_intent(kw)
            table_data.append(
                {
                    "Keyword": kw,
                    "Search Intent": intent,
                    "Estimated KD": difficulty_label,
                    "KD Score": kd_score,
                    "Words": len(kw.split()),
                }
            )

        # --- TABULAR & CLUSTER VIEWS ---
        tab1, tab2 = st.tabs(
            ["📋 All Keywords & Intent", "🧩 Keyword Topic Clusters"]
        )

        with tab1:
            # Download CSV
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(
                [
                    "Keyword",
                    "Search Intent",
                    "Estimated KD",
                    "KD Score",
                    "Word Count",
                ]
            )
            for row in table_data:
                writer.writerow(
                    [
                        row["Keyword"],
                        row["Search Intent"],
                        row["Estimated KD"],
                        row["KD Score"],
                        row["Words"],
                    ]
                )

            st.download_button(
                label="📥 Download CSV",
                data=output.getvalue(),
                file_name=f"{clean_seed.replace(' ', '_')}_keywords.csv",
                mime="text/csv",
            )
            st.dataframe(table_data, use_container_width=True, height=500)

        with tab2:
            st.markdown(
                "### Automatically Grouped Topic Clusters for Content Planning"
            )
            clusters = cluster_keywords(keywords, clean_seed)

            for topic, cluster_kws in clusters.items():
                if len(cluster_kws) > 1:
                    with st.expander(
                        f"📁 **{topic}** ({len(cluster_kws)} keywords)"
                    ):
                        st.write(cluster_kws)

    else:
        st.error("No keywords found. Try a different seed keyword.")
