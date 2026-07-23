import csv
import io
import re
import string
import time
import urllib.parse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import requests
import streamlit as st
from pytrends.request import TrendReq

# --- STREAMLIT PAGE CONFIG ---
st.set_page_config(
    page_title="Free Keyword Research Tool & Trends",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Initialize Session Search History
if "search_history" not in st.session_state:
    st.session_state["search_history"] = []
if "theme" not in st.session_state:
    st.session_state["theme"] = "dark"

# --- THEME PALETTES ---
THEMES = {
    "dark": {
        "bg": "#0B1220",
        "card_bg": "rgba(30, 41, 59, 0.6)",
        "border": "#293548",
        "text": "#F1F5F9",
        "muted_text": "#94A3B8",
        "input_bg": "rgba(30, 41, 59, 0.7)",
    },
    "light": {
        "bg": "#F8FAFC",
        "card_bg": "#FFFFFF",
        "border": "#E2E8F0",
        "text": "#0F172A",
        "muted_text": "#64748B",
        "input_bg": "#FFFFFF",
    },
}
theme = THEMES[st.session_state["theme"]]

# Small theme toggle in the top-right corner
_, toggle_col = st.columns([6, 1])
with toggle_col:
    theme_choice = st.selectbox(
        "Theme",
        options=["dark", "light"],
        index=0 if st.session_state["theme"] == "dark" else 1,
        label_visibility="collapsed",
    )
    if theme_choice != st.session_state["theme"]:
        st.session_state["theme"] = theme_choice
        st.rerun()

# --- ADVANCED DESIGNER CSS INJECTION (theme-aware + mobile responsive) ---
st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

    html, body, [data-testid="stAppViewContainer"] {{
        background-color: {theme["bg"]};
        color: {theme["text"]};
        font-family: 'Inter', sans-serif !important;
    }}

    /* Keep content readable on all screen sizes instead of edge-to-edge */
    .block-container {{
        padding-left: 1.2rem;
        padding-right: 1.2rem;
        max-width: 1100px;
    }}

    div[data-testid="stTextInput"],
    button,
    div.stDataFrame,
    .trend-card,
    .success-card {{
        border-radius: 12px !important;
        overflow: hidden;
    }}

    .header-container {{ text-align: center; margin-bottom: 30px; }}
    .main-header {{
        font-size: 2.5rem;
        font-weight: 800;
        background: -webkit-linear-gradient(#3B82F6, #10B981);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }}
    .sub-header {{ font-size: 1.1rem; color: {theme["muted_text"]}; font-weight: 400; }}

    div[data-testid="stTextInput"] input {{
        background-color: {theme["input_bg"]};
        color: {theme["text"]};
        border: 1px solid {theme["border"]};
        height: 3em;
    }}

    div[data-testid="stHorizontalBlock"] .stButton>button {{
        background: linear-gradient(135deg, #2563EB, #1D4ED8);
        color: white;
        border: none;
        height: 3em;
        font-weight: 700;
        text-transform: uppercase;
        box-shadow: 0 4px 10px rgba(37, 99, 235, 0.3);
        width: 100%;
    }}

    .trend-card {{
        background-color: {theme["card_bg"]};
        padding: 25px;
        border: 1px solid {theme["border"]};
        margin-bottom: 25px;
        backdrop-filter: blur(10px);
    }}
    .trend-card h3, .trend-card p {{ color: {theme["text"]} !important; }}
    .trend-link {{
        display: inline-block;
        background: linear-gradient(135deg, #3B82F6, #10B981);
        color: white !important;
        padding: 12px 24px;
        border-radius: 8px;
        text-decoration: none;
        font-weight: 700;
        margin-top: 15px;
    }}

    .success-card {{
        background-color: rgba(16, 185, 129, 0.15);
        color: #10B981;
        border: 1px solid #10B981;
        padding: 15px 20px;
        margin-bottom: 20px;
        font-weight: 600;
    }}

    /* --- MOBILE RESPONSIVE ADJUSTMENTS --- */
    @media (max-width: 640px) {{
        .block-container {{ padding-left: 0.6rem; padding-right: 0.6rem; }}
        .main-header {{ font-size: 1.6rem; }}
        .sub-header {{ font-size: 0.85rem; }}
        .trend-card {{ padding: 16px; }}
        .trend-link {{ display: block; text-align: center; padding: 14px; }}
        div[data-testid="stTextInput"] input {{ height: 2.6em; font-size: 0.95rem; }}
        div[data-testid="stHorizontalBlock"] .stButton>button {{ height: 2.8em; font-size: 0.85rem; }}
    }}
    </style>
""",
    unsafe_allow_html=True,
)


# --- HELPER FUNCTIONS ---
def get_google_suggest(query):
    """Fetch Google Autocomplete suggestions for a single query.

    Returns (suggestions, ok) where ok=False signals a failed/blocked
    request so the caller can warn the user instead of silently
    treating it as "no results found".
    """
    encoded_query = urllib.parse.quote(query)
    url = f"http://suggestqueries.google.com/complete/search?client=chrome&q={encoded_query}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            return response.json()[1], True
        return [], False
    except Exception:
        return [], False


def get_bing_suggest(query):
    """Fetch Bing Autocomplete suggestions for a single query.

    Same (suggestions, ok) contract as get_google_suggest. Bing's
    osjson endpoint returns [query, [suggestions]] just like Google's,
    so the parsing logic mirrors it.
    """
    encoded_query = urllib.parse.quote(query)
    url = f"https://www.bing.com/osjson.aspx?query={encoded_query}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 1:
                return data[1], True
        return [], False
    except Exception:
        return [], False


# Registry of suggestion sources: name -> fetch function.
# Adding a new source later just means adding one entry here.
SUGGEST_SOURCES = {
    "google": get_google_suggest,
    "bing": get_bing_suggest,
}


def fetch_suggestions(source, query):
    """Dispatch to the right source's fetch function."""
    return SUGGEST_SOURCES[source](query)


def get_trends_popularity_batch(keyword_batch, timeframe="today 12-m"):
    """Fetch relative Google Trends interest (0-100) for up to 5 keywords.

    IMPORTANT: this is NOT a search volume count. Google Trends only
    exposes relative popularity — 100 marks the batch's peak interest,
    everything else is scaled against it. Returns {} on any failure
    (rate-limited, no data, network error) so callers can degrade
    gracefully instead of crashing the whole search.
    """
    try:
        pytrends = TrendReq(hl="en-US", tz=360, timeout=(5, 10), retries=1, backoff_factor=0.3)
        pytrends.build_payload(keyword_batch, timeframe=timeframe)
        df = pytrends.interest_over_time()
        if df is None or df.empty:
            return {}
        scores = {}
        for kw in keyword_batch:
            if kw in df.columns:
                scores[kw] = round(float(df[kw].mean()), 1)
        return scores
    except Exception:
        return {}


def get_trends_for_top_keywords(keywords, seed, top_n=10):
    """Picks the most representative subset of keywords (shorter/head
    terms first, since those are what people usually want popularity
    context for) and fetches Trends data in batches of 5 — the max
    Google allows per request. Runs sequentially with a short pause
    between batches, since bursting requests is what gets an IP
    rate-limited by Google Trends in the first place."""
    # Always include the seed itself, then fill in with the shortest
    # (most head-term-like) remaining keywords.
    ranked = sorted(
        (kw for kw in keywords if kw != seed),
        key=lambda k: (len(k.split()), len(k)),
    )
    subset = [seed] + ranked
    subset = list(dict.fromkeys(subset))[:top_n]  # dedupe, preserve order

    scores = {}
    failed_batches = 0
    batches = [subset[i : i + 5] for i in range(0, len(subset), 5)]

    for i, batch in enumerate(batches):
        result = get_trends_popularity_batch(batch)
        if result:
            scores.update(result)
        else:
            failed_batches += 1
        if i < len(batches) - 1:
            time.sleep(1)  # small gap between requests to stay polite to Google

    if failed_batches and failed_batches == len(batches):
        st.warning(
            "⚠️ Google Trends didn't return data (likely rate-limited on this "
            "server). Popularity scores are unavailable for this search — "
            "try again in a few minutes."
        )
    elif failed_batches:
        st.info(
            f"ℹ️ Google Trends returned partial data ({failed_batches} of "
            f"{len(batches)} batches failed) — some keywords may be missing "
            "a popularity score."
        )

    return scores


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


def estimate_long_tail_signal(keyword):
    """Rough proxy based on word count only.

    NOTE: This is NOT a real keyword-difficulty metric (no SERP,
    backlink, or competition data goes into it) — it's a heuristic
    that longer, more specific phrases *tend* to be easier to rank
    for. Treat it as a starting signal, not a guarantee.
    """
    words = keyword.split()
    word_count = len(words)
    if word_count >= 5:
        return "🟢 Very Long-tail", "Likely low competition"
    elif word_count == 4:
        return "🟢 Long-tail", "Likely lower competition"
    elif word_count == 3:
        return "🟡 Medium length", "Moderate competition likely"
    elif word_count == 2:
        return "🟠 Short phrase", "Higher competition likely"
    else:
        return "🔴 Single word", "Very high competition likely"


def generate_keywords(seed, include_questions=True, sources=("google", "bing"), max_workers=15):
    """Returns (keywords, keyword_sources) where keyword_sources maps
    each keyword to the set of source names it was found in."""
    keyword_sources = defaultdict(set)
    failed_by_source = defaultdict(int)
    total_by_source = defaultdict(int)

    # Build the full list of queries up front so they can run in parallel
    base_queries = [seed] + [f"{seed} {letter}" for letter in string.ascii_lowercase]
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
        base_queries += [f"{q_word} {seed}" for q_word in question_words]

    # Cross product of queries x sources — each source gets the same seed variations
    jobs = [(source, q) for source in sources for q in base_queries]

    progress_bar = st.progress(0)
    status_text = st.empty()
    total = len(jobs)
    completed = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_job = {
            executor.submit(fetch_suggestions, source, q): (source, q)
            for source, q in jobs
        }
        for future in as_completed(future_to_job):
            source, query = future_to_job[future]
            suggestions, ok = future.result()
            total_by_source[source] += 1
            if ok:
                for kw in suggestions:
                    keyword_sources[kw].add(source)
            else:
                failed_by_source[source] += 1

            completed += 1
            status_text.text(f"✨ Fetching suggestions... ({completed}/{total})")
            progress_bar.progress(completed / total)

    progress_bar.empty()
    status_text.empty()

    # Surface partial failures per source instead of silently under-reporting
    for source in sources:
        source_total = total_by_source.get(source, 0)
        source_failed = failed_by_source.get(source, 0)
        if source_total and (source_failed / source_total) > 0.3:
            st.warning(
                f"⚠️ {source.title()}: {source_failed} of {source_total} "
                "sub-queries failed or were rate-limited. Results from this "
                "source may be incomplete."
            )

    return sorted(keyword_sources.keys()), keyword_sources


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
    source_cols = st.columns(2)
    with source_cols[0]:
        use_google = st.checkbox("Google", value=True)
    with source_cols[1]:
        use_bing = st.checkbox("Bing", value=True)
    fetch_trends = st.checkbox(
        "📈 Add Trends Popularity",
        value=False,
        help=(
            "Fetches a relative popularity score (0-100) from Google Trends "
            "for a subset of your top keywords. This is NOT a search volume "
            "count — it's relative interest, and it's slower / can occasionally "
            "get rate-limited by Google."
        ),
    )
    trends_top_n = 10
    if fetch_trends:
        trends_top_n = st.slider(
            "Keywords to check", min_value=5, max_value=20, value=10, step=5
        )
    search_button = st.button("Search Keywords ✨")

if search_button and seed_keyword.strip():
    clean_seed = seed_keyword.strip()
    selected_sources = [
        s for s, enabled in (("google", use_google), ("bing", use_bing)) if enabled
    ]

    if not selected_sources:
        st.error("Select at least one source (Google or Bing) to search.")
        st.stop()

    # Save to Session History
    if clean_seed not in st.session_state["search_history"]:
        st.session_state["search_history"].append(clean_seed)

    with st.spinner("Extracting keywords, intent, and clusters..."):
        keywords, keyword_sources = generate_keywords(
            clean_seed,
            include_questions=include_questions,
            sources=selected_sources,
        )

    trend_scores = {}
    if keywords and fetch_trends:
        with st.spinner("Fetching Google Trends popularity (this can take a few seconds)..."):
            trend_scores = get_trends_for_top_keywords(
                keywords, clean_seed, top_n=trends_top_n
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
            signal_label, signal_note = estimate_long_tail_signal(kw)
            intent = detect_search_intent(kw)
            found_in = "+".join(sorted(keyword_sources.get(kw, [])))
            popularity = trend_scores.get(kw)
            popularity_display = f"{popularity}" if popularity is not None else "—"
            table_data.append(
                {
                    "Keyword": kw,
                    "Source": found_in,
                    "Search Intent": intent,
                    "Long-tail Signal": signal_label,
                    "Note (not real KD data)": signal_note,
                    "Trends Popularity (relative, not volume)": popularity_display,
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
                    "Source",
                    "Search Intent",
                    "Long-tail Signal",
                    "Note (not real KD data)",
                    "Trends Popularity (relative, not volume)",
                    "Word Count",
                ]
            )
            for row in table_data:
                writer.writerow(
                    [
                        row["Keyword"],
                        row["Source"],
                        row["Search Intent"],
                        row["Long-tail Signal"],
                        row["Note (not real KD data)"],
                        row["Trends Popularity (relative, not volume)"],
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
