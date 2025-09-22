# sidebar/Home.py
import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_gsheets import GSheetsConnection

def app():
    st.header("Home")

    # --- Koneksi ke Google Sheets via secrets ---
    try:
        conn: GSheetsConnection = st.connection("gsheets", type=GSheetsConnection)
    except Exception as e:
        st.error(
            "Koneksi 'gsheets' belum diset. Buka Settings → Secrets dan pastikan blok "
            "[connections.gsheets] berisi kredensial service account."
        )
        st.stop()

    # Default dari secrets (opsional): spreadsheet URL/ID & worksheet
    gs_secrets = dict(st.secrets.get("connections", {})).get("gsheets", {})
    default_spreadsheet = str(gs_secrets.get("spreadsheet", ""))
    default_worksheet = str(gs_secrets.get("worksheet", "")) or "History"

    c1, c2 = st.columns(2)
    with c1:
        spreadsheet = st.text_input(
            "Spreadsheet (URL atau ID)",
            value=default_spreadsheet,
            placeholder="https://docs.google.com/spreadsheets/d/<ID>/edit#gid=..."
        )
    with c2:
        worksheet = st.text_input("Worksheet (nama tab)", value=default_worksheet)

    @st.cache_data(ttl=120, show_spinner=True)
    def load_data(spreadsheet: str, worksheet: str) -> pd.DataFrame:
        # library akan mengambil kredensial dari [connections.gsheets]
        df = conn.read(spreadsheet=spreadsheet, worksheet=worksheet)
        # normalisasi kolom kosong → None
        if not isinstance(df, pd.DataFrame):
            return pd.DataFrame()
        return df

    try:
        df = load_data(spreadsheet, worksheet)
    except Exception as e:
        st.error(f"Gagal membaca Google Sheets: {e}")
        st.stop()

    if df.empty:
        st.warning("Tidak ada data yang terbaca.")
        return

    st.subheader("Data (sampel)")
    st.dataframe(df.head(100), use_container_width=True)

    # --- Visual ringkas (adaptif) ---
    status_col = None
    for c in ["STATUS_GARDU", "STATUS", "Status"]:
        if c in df.columns:
            status_col = c
            break

    if status_col:
        st.subheader(f"Distribusi {status_col}")
        vc = df[status_col].fillna("Kosong").astype(str).value_counts().reset_index()
        vc.columns = [status_col, "Jumlah"]
        fig = px.pie(vc, names=status_col, values="Jumlah", hole=0.35)
        st.plotly_chart(fig, use_container_width=True)

    # Info ukuran data
    st.caption(f"{len(df):,} baris · {len(df.columns)} kolom")

# panggil otomatis jika file dieksekusi langsung
if __name__ == "__main__":
    app()
