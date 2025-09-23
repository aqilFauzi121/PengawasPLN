import streamlit as st
import pandas as pd
import gspread
from datetime import date, datetime
from google.oauth2.service_account import Credentials

st.title("Update Status Sheet History – Multi ID")

# Ambil creds dari secrets → jadikan Credentials
raw_info = dict(st.secrets["connections"]["gsheets"])
creds = Credentials.from_service_account_info(raw_info).with_scopes([
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
])

gc = gspread.authorize(creds)

# Baca target sheet dari secrets
SPREADSHEET_ID = st.secrets["SPREADSHEET_ID"]
WORKSHEET_GID = int(st.secrets["WORKSHEET_GID"])

sh = gc.open_by_key(SPREADSHEET_ID)

# Cari worksheet berdasarkan GID
ws = None
for _ws in sh.worksheets():
    if _ws.id == WORKSHEET_GID:
        ws = _ws
        break
if ws is None:
    st.error(f"Worksheet dengan GID {WORKSHEET_GID} tidak ditemukan.")
    return

df = pd.DataFrame(ws.get_all_records())

penyulang_list = sorted(df["PENYULANG"].dropna().unique())
penyulang = st.selectbox("Pilih PENYULANG", penyulang_list)

if penyulang:
    filtered = df[df["PENYULANG"].str.lower() == penyulang.lower()]
    id_list = filtered["ID"].tolist()

    # === ✅ Checkbox untuk pilih semua ID ===
    select_all = st.checkbox("Pilih semua ID")
    if select_all:
        target_ids = st.multiselect(
            "Pilih satu atau banyak ID",
            id_list,
            default=id_list      # semua ID otomatis terpilih
        )
    else:
        target_ids = st.multiselect(
            "Pilih satu atau banyak ID",
            id_list
        )

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
            for tid in target_ids:
                row_idx = df.index[df["ID"] == tid][0]
                row_num = row_idx + 2   # header + offset

                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ws.update(f"A{row_num}", timestamp)        # kolom A: last update
                ws.update(f"B{row_num}", new_pengawas)     # kolom B: Pengawas
                ws.update(f"F{row_num}:K{row_num}", [values_F_K])  # kolom F–K

                updated += 1

            st.success(f"Berhasil memperbarui {updated} baris.")
