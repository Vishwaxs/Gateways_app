# GATEWAYS-2025 National Fest Dashboard

An interactive Streamlit web application for analyzing participation in the GATEWAYS-2025 national-level fest.

## Features

- **Participation Trends** – Event-wise, college-wise analysis with interactive filters
- **India Choropleth Map** – GeoPandas-based statewise participant map
- **Feedback & Ratings** – Keyword analysis, rating distribution, sentiment preview
- **Comparison Tab** – State × Event heatmap and amount vs rating scatter plot

## How to Run Locally

```bash
pip install -r requirements.txt
streamlit run fest_app.py
```

## Deploy on Streamlit Cloud

1. Push this folder to a GitHub repository (root of repo or a subfolder).
2. Go to [share.streamlit.io](https://share.streamlit.io).
3. Connect your GitHub repo.
4. Set **Main file path** to `fest_app.py`.
5. Click **Deploy**.

## Folder Structure

```
gateways_app/
├── fest_app.py              # Main Streamlit app
├── requirements.txt         # Python dependencies
├── README.md
├── .streamlit/
│   └── config.toml          # Theme and server config
└── data/
    ├── fest_dataset.csv     # Participant dataset
    └── india_states.geojson # India state boundaries (GeoJSON)
```

## Libraries Used

- `streamlit` – Web app framework
- `pandas` – Data analysis
- `matplotlib` – Charts and visualizations
- `geopandas` – India map choropleth
