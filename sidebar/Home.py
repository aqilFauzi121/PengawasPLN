import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import pytz
import plotly.express as px

st.set_page_config(layout="wide")
st.title("Selamat Datang di Dashboard PLN AREA MALANG")

# ----------------------
# CONFIG
# ----------------------
LOG_WORKSHEET = "History"
DATA_WORKSHEET = "Sheet1"
SPREADSHEET_ID = "1ucW_0t_nK47WKn4kFZrbSnkWgEYf-TtCk7ioQJHpD5w"

# Koneksi ke Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# ----------------------
# FUNGSI BANTUAN
# ----------------------
def safe_read(worksheet_name):
    try:
        df = conn.read(worksheet=worksheet_name)
        if isinstance(df, pd.DataFrame):
            return df.copy()
        else:
            return pd.DataFrame(df)
    except Exception:
        return pd.DataFrame()

def convert_old_log_to_snapshot(df_old):
    target_cols = ["TIMESTAMP","PENGAWAS","PENYULANG","ID","SECTION",
                   "STATUS","JENIS_PEKERJAAN","WAKTU_MULAI","WAKTU_SELESAI","PELAKSANA"]
    if df_old.empty:
        return pd.DataFrame(columns=target_cols)

    if "FIELD_CHANGED" in df_old.columns and "NEW_VALUE" in df_old.columns:
        try:
            pivot = (
                df_old
                .pivot_table(
                    index=["TIMESTAMP", "PENGAWAS", "PENYULANG", "ID", "SECTION"],
                    columns="FIELD_CHANGED",
                    values="NEW_VALUE",
                    aggfunc="first"
                )
                .reset_index()
            )
            if isinstance(pivot.columns, pd.MultiIndex):
                pivot.columns = [col if not isinstance(col, tuple) else col[-1] for col in pivot.columns]
            for c in target_cols:
                if c not in pivot.columns:
                    pivot[c] = ""
            return pivot[target_cols].copy()
        except Exception:
            return pd.DataFrame(columns=target_cols)
    else:
        df = df_old.copy()
        for c in target_cols:
            if c not in df.columns:
                df[c] = ""
        return df[target_cols].copy()

# ----------------------
# BACA DATA GARDU
# ----------------------
df_gardu = safe_read(DATA_WORKSHEET)

# Layout utama: kiri (grafik + log) dan kanan (KPI)
left_col, right_col = st.columns([2,1])

with right_col:
    if not df_gardu.empty:
        total_gardu = df_gardu["ID"].nunique()
        total_gardu_induk = df_gardu["GARDU INDUK"].nunique()
        total_pelanggan = df_gardu["JML PELANGGAN"].astype(float).sum()

        st.metric("Jumlah Gardu Total", f"{total_gardu:g}")
        st.metric("Jumlah Gardu Induk", f"{total_gardu_induk:g}")
        st.metric("Jumlah Pelanggan", f"{int(total_pelanggan):,}")

# ----------------------
# BACA & FILTER LOG
# ----------------------
log_raw = safe_read(LOG_WORKSHEET)
log_snapshot = convert_old_log_to_snapshot(log_raw)

# Ambil tanggal hari ini (zona WIB)
wib = pytz.timezone("Asia/Jakarta")
today = datetime.now(wib).date()

if not log_snapshot.empty and "TIMESTAMP" in log_snapshot.columns:
    log_snapshot["TIMESTAMP"] = pd.to_datetime(log_snapshot["TIMESTAMP"], errors="coerce")
    log_today = log_snapshot[log_snapshot["TIMESTAMP"].dt.date == today]
else:
    log_today = pd.DataFrame()

# ----------------------
# KONTEN KIRI: Grafik + Log
# ----------------------
with left_col:
    if not df_gardu.empty and "PENYULANG" in df_gardu.columns:
        # pastikan numeric
        df_gardu["JML PELANGGAN"] = pd.to_numeric(df_gardu["JML PELANGGAN"], errors="coerce").fillna(0).astype(int)
        df_gardu["DAYA"] = pd.to_numeric(df_gardu["DAYA"], errors="coerce").fillna(0)

        # agregasi data
        tabel_pelanggan = (
            df_gardu.groupby("PENYULANG", dropna=False)["JML PELANGGAN"]
            .sum()
            .reset_index()
            .sort_values("JML PELANGGAN", ascending=False)
        )

        st.subheader("Sebaran Jumlah Pelanggan per Penyulang")
        fig_pelanggan = px.bar(
            tabel_pelanggan,
            x="PENYULANG",
            y="JML PELANGGAN",
            text="JML PELANGGAN",
            color="PENYULANG",
        )
        fig_pelanggan.update_layout(showlegend=False, yaxis_title="Jumlah Pelanggan", xaxis_tickangle=-45)
        fig_pelanggan.update_traces(textposition="outside")
        st.plotly_chart(fig_pelanggan, use_container_width=True)

    st.markdown("----")
    st.subheader("Log Pekerjaan Hari Ini")

    if log_today.empty:
        st.info("Belum ada log untuk hari ini.")
    else:
        # KPI tambahan untuk status pekerjaan
        total_ongoing = (log_today["STATUS"].str.lower() == "Proses").sum()
        total_selesai = (log_today["STATUS"].str.lower() == "Selesai").sum()

        col1, col2, col3 = st.columns(3)
        col1.metric("🟡 Proses", total_ongoing)
        col2.metric("🟢 Selesai", total_selesai)

        # Mapping status ke emoji
        status_map = {
            "selesai": "🟢 Selesai",
            "on-going": "🟡 Proses",
        }
        df_display = log_today.copy()
        df_display["STATUS"] = df_display["STATUS"].str.lower().map(status_map).fillna(df_display["STATUS"])
        display_cols = ["STATUS","TIMESTAMP","PENYULANG","SECTION","ID","PENGAWAS",
                        "JENIS_PEKERJAAN","WAKTU_MULAI","WAKTU_SELESAI","PELAKSANA"]
        display_cols = [c for c in display_cols if c in df_display.columns]

        st.dataframe(df_display[display_cols].reset_index(drop=True), use_container_width=True)
