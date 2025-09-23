import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

st.title("Update Status Sheet History – Multi ID")

# ==== kredensial dari st.secrets ====
sa_info = dict(st.secrets["connections"]["gsheets"])
scopes = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(sa_info, scopes=scopes)
gc = gspread.authorize(creds)

# ==== target spreadsheet & worksheet ====
SPREADSHEET_ID = st.secrets["connections"]["gsheets"].get(
    "spreadsheet",
    "1FvKNPEtkOfB9nlH8sMqdXkZDYYQ4n-7n8yL9-v2_rx0"  # fallback
)
WS_NAME = st.secrets["connections"]["gsheets"].get("worksheet", "History")

sh = gc.open_by_key(SPREADSHEET_ID)
ws = sh.worksheet(WS_NAME)

# ==== load data ====
df = pd.DataFrame(ws.get_all_records())

penyulang_list = sorted(pd.Series(df.get("PENYULANG", [])).dropna().unique())
penyulang = st.selectbox("Pilih PENYULANG", penyulang_list)

if penyulang:
    filtered = df[df["PENYULANG"].astype(str).str.lower() == str(penyulang).lower()]
    id_list = filtered["ID"].tolist()

    select_all = st.checkbox("Pilih semua ID")
    target_ids = st.multiselect("Pilih satu atau banyak ID", id_list,
                                default=id_list if select_all else None)

    col1, col2 = st.columns(2)
    with col1:
        new_status = st.selectbox("STATUS (F)", ["Selesai", "Proses"])
        new_status_gardu = st.selectbox("STATUS_GARDU (G)", ["Nyala", "Mati"])
        new_jenis = st.text_input("JENIS_PEKERJAAN (H)", "")
        new_pengawas = st.text_input("PENGAWAS (B)", "")
    with col2:
        new_waktu_mulai = st.date_input("WAKTU_MULAI (I)", value=None)
        new_waktu_selesai = st.date_input("WAKTU_SELESAI (J)", value=None)
        new_pelaksana = st.text_input("PELAKSANA (K)", "")

    if st.button("Update Data"):
        if not target_ids:
            st.warning("Silakan pilih minimal satu ID.")
        else:
            values_F_K = [
                new_status,
                new_status_gardu,
                new_jenis,
                new_waktu_mulai.isoformat() if new_waktu_mulai else "",
                new_waktu_selesai.isoformat() if new_waktu_selesai else "",
                new_pelaksana,
            ]
            updated = 0
            # bangun index ID -> row
            idx_map = {row["ID"]: i for i, row in df.iterrows()}
            batch = []
            for tid in target_ids:
                row_idx = idx_map.get(tid)
                if row_idx is None:
                    continue
                row_num = row_idx + 2  # header di baris 1
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                batch.append({"range": f"A{row_num}", "values": [[timestamp]]})
                batch.append({"range": f"B{row_num}", "values": [[new_pengawas]]})
                batch.append({"range": f"F{row_num}:K{row_num}", "values": [values_F_K]})
                updated += 1

            if batch:
                ws.batch_update(batch)
            st.success(f"Berhasil memperbarui {updated} baris.")
