import re
from collections import Counter
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

st.set_page_config(page_title="GATEWAYS-2025 Fest Dashboard", layout="wide")

# --- Paths (relative to this file) ---
BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "fest_dataset.csv"

# India states GeoJSON (from GitHub gist)
GEOJSON_URL = (
    "https://gist.githubusercontent.com/jbrobst/"
    "56c13bbbf9d97d187fea01ca62ea5112/raw/"
    "e388c4cae20aa53cb5090210a42ebb9b765c0a36/india_states.geojson"
)

# --- Stopwords for feedback cleaning ---
STOPWORDS = {
    "the", "and", "to", "of", "in", "on", "for", "a", "an", "is", "was",
    "with", "very", "good", "great", "useful", "experience", "event",
    "session", "slight", "needs", "creative", "informative", "engaging",
}


# --- Load dataset (cached) ---
@st.cache_data
def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]
    df["Rating"] = pd.to_numeric(df["Rating"], errors="coerce")
    df["Amount Paid"] = pd.to_numeric(df["Amount Paid"], errors="coerce")
    df["State"] = df["State"].str.strip().str.title()
    return df


# --- Load India states GeoJSON (cached) ---
@st.cache_data
def load_geojson(url: str) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(url)
    # standardize state names
    gdf["ST_NM"] = gdf["ST_NM"].str.strip().str.title()
    return gdf


# --- Text tokenizer ---
def clean_tokens(text: str) -> list:
    words = re.findall(r"[a-zA-Z]{3,}", text.lower())
    return [w for w in words if w not in STOPWORDS]


# --- Sentiment score ---
def sentiment_hint(text: str) -> str:
    pos = {"excellent", "fun", "engaging", "interactive", "creative", "good"}
    neg = {"needs", "improvement", "bad", "poor"}
    score = sum(1 for w in clean_tokens(text) if w in pos) - \
            sum(1 for w in clean_tokens(text) if w in neg)
    return "Positive" if score > 0 else ("Negative" if score < 0 else "Neutral")


# --- India choropleth map ---
def plot_india_map(filtered_df: pd.DataFrame) -> None:
    # count participants per state
    state_counts = filtered_df["State"].value_counts().reset_index()
    state_counts.columns = ["State", "Participants"]

    india_gdf = load_geojson(GEOJSON_URL)

    # merge shapefile with participation data
    merged = india_gdf.merge(state_counts, left_on="ST_NM", right_on="State", how="left")
    merged["Participants"] = merged["Participants"].fillna(0)

    fig, ax = plt.subplots(figsize=(10, 10))
    merged.plot(
        column="Participants",
        cmap="YlOrRd",
        linewidth=0.5,
        edgecolor="grey",
        legend=True,
        ax=ax,
        missing_kwds={"color": "#e5e7eb", "label": "No data"},
    )
    ax.set_title("Statewise Participants – India", fontsize=14, fontweight="bold")
    ax.axis("off")
    plt.tight_layout()
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)


# ============================================================
# MAIN APP
# ============================================================
def main() -> None:
    st.title("GATEWAYS-2025 National Fest Dashboard")
    st.caption("Interactive analysis of participation trends, feedback, and insights.")

    df = load_data(DATA_PATH)

    # ---- Sidebar Filters ----
    # filter key names for session state reset
    filter_keys = [
        "f_events", "f_types", "f_states", "f_colleges",
        "f_min_rating", "f_fee", "f_top_n", "f_keyword",
    ]

    with st.sidebar:
        st.header("🔍 Filters")

        # ADDITION 3: Reset Filters button
        if st.button("Reset Filters"):
            for k in filter_keys:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()

        events = sorted(df["Event Name"].unique())
        types = sorted(df["Event Type"].unique())
        states = sorted(df["State"].unique())
        colleges = sorted(df["College"].unique())

        sel_events = st.multiselect("Event", events, default=events, key="f_events")
        sel_types = st.multiselect("Event Type", types, default=types, key="f_types")
        sel_states = st.multiselect("State", states, default=states, key="f_states")
        sel_colleges = st.multiselect("College", colleges, default=colleges, key="f_colleges")
        min_rating = st.slider("Minimum Rating", 1, int(df["Rating"].max()), 1, key="f_min_rating")
        fee_min, fee_max = int(df["Amount Paid"].min()), int(df["Amount Paid"].max())
        sel_fee = st.slider("Amount Paid (₹)", fee_min, fee_max, (fee_min, fee_max), key="f_fee")
        top_n = st.slider("Top N Colleges", 5, 15, 10, key="f_top_n")
        kw_search = st.text_input("Feedback keyword search", "", key="f_keyword").strip().lower()

    # ---- Apply Filters ----
    filtered = df[
        df["Event Name"].isin(sel_events) &
        df["Event Type"].isin(sel_types) &
        df["State"].isin(sel_states) &
        df["College"].isin(sel_colleges) &
        (df["Rating"] >= min_rating) &
        (df["Amount Paid"].between(sel_fee[0], sel_fee[1]))
    ].copy()

    if kw_search:
        filtered = filtered[
            filtered["Feedback on Fest"].str.lower().str.contains(kw_search, na=False)
        ].copy()

    if filtered.empty:
        st.warning("No data for the current filters. Please widen the selection.")
        st.stop()

    # ---- Summary Metrics ----
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Participants", len(filtered))
    c2.metric("Unique Colleges", filtered["College"].nunique())
    c3.metric("Avg Rating", f"{filtered['Rating'].mean():.2f} / 5")
    c4.metric("Total Fees Collected", f"₹{int(filtered['Amount Paid'].sum()):,}")

    # ADDITION 1: Data Quality Strip
    st.subheader("Data Quality Check")
    dq1, dq2, dq3 = st.columns(3)
    dq1.metric("Records in current view", len(filtered))
    dq2.metric("Missing Ratings", int(filtered["Rating"].isna().sum()))
    dq3.metric("Missing Feedback", int(filtered["Feedback on Fest"].isna().sum()))

    # ---- Insight Lines ----
    top_event = filtered["Event Name"].value_counts().idxmax()
    top_event_n = int(filtered["Event Name"].value_counts().max())
    top_state = filtered["State"].value_counts().idxmax()
    top_state_n = int(filtered["State"].value_counts().max())
    grp_pct = filtered["Event Type"].eq("Group").mean() * 100

    st.info(f"🏆 Highest participation event: **{top_event}** ({top_event_n} participants)")
    st.info(f"📍 Top state: **{top_state}** ({top_state_n} participants)")
    st.info(f"📊 Group events make up **{grp_pct:.1f}%** of registrations in this view.")

    st.caption(
        f"Viewing {filtered['State'].nunique()} states · "
        f"{filtered['Event Name'].nunique()} events · "
        f"{len(filtered)} records"
    )

    st.divider()

    # ============================================================
    # TABS
    # ============================================================
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Participation Trends", "🗺️ State Map", "💬 Feedback & Ratings", "🔍 Comparisons"
    ])

    # ========== TAB 1 – Participation Trends ==========
    with tab1:
        col_l, col_r = st.columns(2)

        # Event-wise bar chart
        event_cnt = filtered["Event Name"].value_counts().reset_index()
        event_cnt.columns = ["Event", "Participants"]
        with col_l:
            st.subheader("Event-wise Participation")
            fig, ax = plt.subplots(figsize=(7, 4))
            ax.barh(event_cnt["Event"], event_cnt["Participants"], color="#4f86c6")
            ax.set_xlabel("Number of Participants")
            ax.set_ylabel("Event")
            ax.set_title("Participants per Event")
            for i, v in enumerate(event_cnt["Participants"]):
                ax.text(v + 0.3, i, str(v), va="center", fontsize=9)
            plt.tight_layout()
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)
            # ADDITION 5: chart insight caption
            top_ev = event_cnt.iloc[0]
            st.caption(f"{top_ev['Event']} has the highest participation with {top_ev['Participants']} registrations.")

        # College-wise bar chart
        college_cnt = filtered["College"].value_counts().head(top_n).reset_index()
        college_cnt.columns = ["College", "Participants"]
        with col_r:
            st.subheader(f"Top {top_n} Colleges by Participation")
            fig, ax = plt.subplots(figsize=(7, 4))
            ax.barh(college_cnt["College"], college_cnt["Participants"], color="#57a773")
            ax.set_xlabel("Number of Participants")
            ax.set_ylabel("College")
            ax.set_title(f"Top {top_n} Colleges")
            for i, v in enumerate(college_cnt["Participants"]):
                ax.text(v + 0.3, i, str(v), va="center", fontsize=9)
            plt.tight_layout()
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)

        # Event Type pie chart
        st.subheader("Event Type Distribution")
        type_cnt = filtered["Event Type"].value_counts()
        fig, ax = plt.subplots(figsize=(5, 4))
        ax.pie(type_cnt, labels=type_cnt.index, autopct="%1.1f%%",
               startangle=90, colors=["#4f86c6", "#f4a261"])
        ax.set_title("Individual vs Group Events")
        st.pyplot(fig, use_container_width=True)
        plt.close(fig)

        # ADDITION 2: Event Summary Table
        st.subheader("Event Summary Table")
        summary = filtered.groupby("Event Name").agg(
            Participants=("Event Name", "count"),
            Avg_Rating=("Rating", "mean"),
            Total_Fees=("Amount Paid", "sum"),
        ).reset_index()
        summary["Avg_Rating"] = summary["Avg_Rating"].round(2)
        summary = summary.sort_values("Participants", ascending=False)
        summary.columns = ["Event Name", "Participants", "Avg Rating", "Total Fees"]
        st.dataframe(summary, use_container_width=True)

    # ========== TAB 2 – State Map ==========
    with tab2:
        st.subheader("Statewise Participants – India Choropleth Map")

        # ADDITION 4: Map Coverage Check
        india_gdf = load_geojson(GEOJSON_URL)
        dataset_states = set(filtered["State"].unique())
        geojson_states = set(india_gdf["ST_NM"].unique())
        matched = len(dataset_states.intersection(geojson_states))
        st.success(f"Mapped states: {matched}/{len(dataset_states)}")

        plot_india_map(filtered)

        # Top states bar chart
        state_cnt = filtered["State"].value_counts().reset_index()
        state_cnt.columns = ["State", "Participants"]
        st.subheader("Top States by Participants")
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.bar(state_cnt["State"], state_cnt["Participants"], color="#e76f51")
        ax.set_xlabel("State")
        ax.set_ylabel("Number of Participants")
        ax.set_title("State-wise Participant Count")
        for i, v in enumerate(state_cnt["Participants"]):
            ax.text(i, v + 0.2, str(v), ha="center", fontsize=9)
        plt.xticks(rotation=30, ha="right")
        plt.tight_layout()
        st.pyplot(fig, use_container_width=True)
        plt.close(fig)
        # ADDITION 5: chart insight caption
        top_st = state_cnt.iloc[0]
        st.caption(f"{top_st['State']} leads participation with {top_st['Participants']} registrations.")

    # ========== TAB 3 – Feedback & Ratings ==========
    with tab3:
        col_l, col_r = st.columns(2)

        # Feedback keyword frequency
        with col_l:
            st.subheader("Feedback Keywords (Top 15)")
            all_tokens = [
                tok for text in filtered["Feedback on Fest"]
                for tok in clean_tokens(str(text))
            ]
            freq = Counter(all_tokens).most_common(15)
            if freq:
                words_df = pd.DataFrame(freq, columns=["Word", "Count"])
                fig, ax = plt.subplots(figsize=(7, 4))
                ax.barh(words_df["Word"][::-1], words_df["Count"][::-1], color="#2a9d8f")
                ax.set_xlabel("Frequency")
                ax.set_ylabel("Keyword")
                ax.set_title("Most Common Feedback Words")
                plt.tight_layout()
                st.pyplot(fig, use_container_width=True)
                plt.close(fig)
            else:
                st.info("No keywords to display.")

        # Rating distribution
        with col_r:
            st.subheader("Rating Distribution")
            rating_dist = filtered["Rating"].value_counts().sort_index()
            fig, ax = plt.subplots(figsize=(7, 4))
            ax.bar(rating_dist.index.astype(str), rating_dist.values, color="#e9c46a")
            ax.set_xlabel("Rating")
            ax.set_ylabel("Number of Participants")
            ax.set_title("Distribution of Ratings")
            for i, v in enumerate(rating_dist.values):
                ax.text(i, v + 0.2, str(v), ha="center", fontsize=9)
            plt.tight_layout()
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)

        # Average rating per event
        st.subheader("Average Rating by Event")
        avg_rating = filtered.groupby("Event Name")["Rating"].mean().sort_values(ascending=False)
        fig, ax = plt.subplots(figsize=(9, 4))
        ax.bar(avg_rating.index, avg_rating.values, color="#264653")
        ax.set_xlabel("Event")
        ax.set_ylabel("Average Rating")
        ax.set_title("Average Rating per Event")
        ax.set_ylim(0, 5.5)
        for i, v in enumerate(avg_rating.values):
            ax.text(i, v + 0.05, f"{v:.2f}", ha="center", fontsize=9, color="white" if v < 0 else "black")
        plt.xticks(rotation=20, ha="right")
        plt.tight_layout()
        st.pyplot(fig, use_container_width=True)
        plt.close(fig)
        # ADDITION 5: chart insight caption
        best_event = avg_rating.idxmax()
        worst_event = avg_rating.idxmin()
        st.caption(f"{best_event} has the highest average rating; {worst_event} has the lowest.")

        # Sentiment table
        st.subheader("Feedback Sentiment Preview")
        filtered["Sentiment"] = filtered["Feedback on Fest"].apply(
            lambda x: sentiment_hint(str(x))
        )
        senti_view = filtered[["Student Name", "State", "Event Name",
                                "Feedback on Fest", "Rating", "Sentiment"]]
        st.dataframe(senti_view.head(20), use_container_width=True)

        # ADDITION 6: Sentiment Distribution Cards + Top Negative Keyword
        st.subheader("Sentiment Distribution")
        senti_counts = filtered["Sentiment"].value_counts()
        sc1, sc2, sc3 = st.columns(3)
        sc1.metric("Positive", int(senti_counts.get("Positive", 0)))
        sc2.metric("Neutral", int(senti_counts.get("Neutral", 0)))
        sc3.metric("Negative", int(senti_counts.get("Negative", 0)))

        # top negative keyword
        neg_rows = filtered[filtered["Sentiment"] == "Negative"]
        if not neg_rows.empty:
            neg_tokens = [
                tok for text in neg_rows["Feedback on Fest"]
                for tok in clean_tokens(str(text))
            ]
            if neg_tokens:
                top_neg_word = Counter(neg_tokens).most_common(1)[0][0]
                st.caption(f"Most flagged keyword in negative feedback: '{top_neg_word}'")

    # ========== TAB 4 – Comparisons ==========
    with tab4:
        col_l, col_r = st.columns(2)

        # State vs Event heatmap
        with col_l:
            st.subheader("State × Event Heatmap")
            heat = pd.crosstab(filtered["State"], filtered["Event Name"])
            fig, ax = plt.subplots(figsize=(9, 5))
            im = ax.imshow(heat.values, cmap="YlGnBu", aspect="auto")
            ax.set_xticks(range(len(heat.columns)))
            ax.set_xticklabels(heat.columns, rotation=40, ha="right", fontsize=8)
            ax.set_yticks(range(len(heat.index)))
            ax.set_yticklabels(heat.index, fontsize=8)
            ax.set_xlabel("Event")
            ax.set_ylabel("State")
            ax.set_title("Participation Heatmap (State × Event)")
            fig.colorbar(im, ax=ax, label="Participants")
            plt.tight_layout()
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)

        # Amount Paid vs Rating scatter
        with col_r:
            st.subheader("Amount Paid vs Rating")
            fig, ax = plt.subplots(figsize=(7, 5))
            colors = {"Individual": "#e76f51", "Group": "#2a9d8f"}
            for etype, grp in filtered.groupby("Event Type"):
                ax.scatter(
                    grp["Amount Paid"], grp["Rating"],
                    alpha=0.6, label=etype, color=colors.get(etype, "#999")
                )
            ax.set_xlabel("Amount Paid (₹)")
            ax.set_ylabel("Rating (out of 5)")
            ax.set_title("Amount Paid vs Participant Rating")
            ax.legend(title="Event Type")
            plt.tight_layout()
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)

    # Actionable recommendation box for organizers
    improve_timing = filtered["Feedback on Fest"].str.lower().str.contains("timing|improvement", regex=True, na=False).mean() * 100
    st.info(
        f"Actionable recommendation: Focus promotion on {top_event} in {top_state}; "
        f"also improve scheduling because {improve_timing:.1f}% feedback mentions timing/improvement themes."
    )

    # ---- Download filtered data ----
    st.divider()
    st.download_button(
        label="⬇️ Download Filtered Data (CSV)",
        data=filtered.drop(columns=["Sentiment"], errors="ignore").to_csv(index=False),
        file_name="gateways_filtered.csv",
        mime="text/csv",
    )


if __name__ == "__main__":
    main()
