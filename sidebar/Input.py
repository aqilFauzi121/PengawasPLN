# sidebar/Input.py
import re
import streamlit as st
import pandas as pd
import gspread
from gspread.utils import rowcol_to_a1
from google.oauth2.service_account import Credentials
from datetime import datetime
from typing import List, Tuple, Optional

def app():
    st.header("Update Status Sheet History – Multi ID")

    # --------------------------- AUTH via st.secrets ---------------------------
    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    REQUIRED_KEYS = {
        "type",
        "project_id",
        "private_key_id",
        "private_key",
        "client_email",
        "client_id",
        "token_uri",
    }
    OPTIONAL_KEYS = {
        "auth_uri",
        "auth_provider_x509_cert_url",
        "client_x509_cert_url",
        "universe_domain",
    }

    @st.cache_resource(show_spinner=False)
    def get_gspread_client() -> gspread.Client:
        try:
            raw = dict(st.secrets["connections"]["gsheets"])
        except Exception as e:
            st.error(
                "Secrets belum lengkap. Tambahkan blok [connections.gsheets] di Settings → Secrets.\n"
                "Minimal memuat kredensial service account (type, project_id, private_key_id, private_key, "
                "client_email, client_id, token_uri)."
            )
            raise e

        # Filter field kredensial
        sa_info = {k: v for k, v in raw.items() if k in REQUIRED_KEYS or k in OPTIONAL_KEYS}
        missing = [k for k in REQUIRED_KEYS if k not in sa_info]
        if missing:
            st.error(f"Secrets tidak lengkap. Field wajib hilang: {', '.join(missing)}")
            st.stop()

        # Private key: pastikan newline benar
        if "\\n" in sa_info.get("private_key", ""):
            sa_info["private_key"] = sa_info["private_key"].replace("\\n", "\n")

        creds = Credentials.from_service_account_info(sa_info, scopes=SCOPES)
        return gspread.authorize(creds)

    gc = get_gspread_client()

    # --------------------------- Default dari secrets -------------------------
    def extract_spreadsheet_id(s: str) -> Optional[str]:
        if not s:
            return None
        m = re.search(r"/d/([a-zA-Z0-9-_]+)", s)
        if m:
            return m.group(1)
        if re.fullmatch(r"[a-zA-Z0-9-_]{20,}", s):
            return s
        return None

    raw_conn = dict(st.secrets.get("connections", {})).get("gsheets", {})
    default_spreadsheet = str(raw_conn.get("spreadsheet", ""))
    default_ws = str(raw_conn.get("worksheet", ""))  # boleh nama tab atau GID (angka)
    default_id = extract_spreadsheet_id(default_spreadsheet) or ""

    # --------------------------- UI target sheet ------------------------------
    mode = st.radio(
        "Pilih cara referensi Spreadsheet:",
        ["Spreadsheet ID", "Nama Spreadsheet"],
        horizontal=True,
        index=0 if default_id else 1,
    )

    c1, c2 = st.columns(2)
    with c1:
        if mode == "Spreadsheet ID":
            spreadsheet_id = st.text_input("Spreadsheet ID", value=default_id, placeholder="1AbC...XYZ")
            spreadsheet_name = ""
        else:
            spreadsheet_name = st.text_input("Nama Spreadsheet", value="", placeholder="data gardu")
            spreadsheet_id = ""

    with c2:
        ws_hint = "nama tab (mis. History) atau angka GID (mis. 1476556612)"
        worksheet_input = st.text_input("Worksheet", value=str(default_ws or ""), placeholder=ws_hint, help=ws_hint).strip()

    # Open spreadsheet & worksheet
    try:
        sh = gc.open_by_key(spreadsheet_id) if mode == "Spreadsheet ID" else gc.open(spreadsheet_name)
    except Exception as e:
        st.error(f"Gagal membuka Spreadsheet: {e}")
        st.stop()

    try:
        if worksheet_input.isdigit():
            ws = sh.get_worksheet_by_id(int(worksheet_input))
        elif worksheet_input:
            ws = sh.worksheet(worksheet_input)
        else:
            ws = sh.sheet1
    except Exception as e:
        st.error(f"Gagal membuka Worksheet: {e}")
        st.stop()

    # --------------------------- Header & pemetaan kolom ----------------------
    try:
        header = ws.row_values(1)
        if not header:
            st.warning("Header baris pertama kosong.")
            st.stop()
    except Exception as e:
        st.error(f"Gagal membaca header: {e}")
        st.stop()

    def col_index(col_name: str, header_row: List[str]) -> int:
        try:
            return header_row.index(col_name) + 1  # 1-based
        except ValueError:
            raise ValueError(f"Kolom '{col_name}' tidak ditemukan di header.")

    # Saran kolom
    suggest_id = "ID" if "ID" in header else header[0]
    candidates_status = [c for c in header if c.upper() in ("STATUS", "STATUS_GARDU")] or header
    suggest_status = candidates_status[0]
    candidates_ts = [c for c in header if c.lower() in ("timestamp", "sent at", "sent_at", "updated_at")]
    suggest_ts = candidates_ts[0] if candidates_ts else None

    st.subheader("Pengaturan Kolom")
    k1, k2, k3 = st.columns(3)
    with k1:
        col_id_name = st.selectbox("Kolom ID", options=header, index=header.index(suggest_id))
    with k2:
        col_status_name = st.selectbox("Kolom Status", options=header, index=header.index(suggest_status))
    with k3:
        col_ts_name = st.selectbox(
            "Kolom Timestamp (opsional)",
            options=["(None)"] + header,
            index=(header.index(suggest_ts) + 1) if (suggest_ts and suggest_ts in header) else 0,
        )

    # --------------------------- Input perubahan ------------------------------
    st.subheader("Input Perubahan")
    ids_raw = st.text_area(
        "Daftar ID (pisahkan dengan koma atau baris baru)",
        placeholder="51311172646881, 51311172646882\n51311172646883",
        height=110,
    )
    new_status = st.text_input("Nilai status baru", value="Selesai")
    apply_btn = st.button("Update Status")

    def parse_ids(text: str) -> List[str]:
        parts = [p.strip() for p in text.replace("\n", ",").split(",")]
        return [p for p in parts if p]

    # --------------------------- Helper & update ------------------------------
    def find_rows_by_ids(all_values: List[List[str]], id_col_idx: int, id_targets: List[str]) -> Tuple[dict, List[str]]:
        target_set = {str(x) for x in id_targets}
        mapping = {}
        not_found = set(target_set)
        for r_idx in range(2, len(all_values) + 1):  # mulai baris 2
            val = str(all_values[r_idx - 1][id_col_idx - 1]).strip()
            if val in target_set:
                mapping[val] = r_idx
                not_found.discard(val)
        return mapping, sorted(list(not_found))

    def batch_update_cells(ws: gspread.Worksheet, rows_map: dict, status_col_idx: int,
                           ts_col_idx: Optional[int], status_value: str):
        updates = []
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for _id, row in rows_map.items():
            updates.append({"range": rowcol_to_a1(row, status_col_idx), "values": [[status_value]]})
            if ts_col_idx is not None:
                updates.append({"range": rowcol_to_a1(row, ts_col_idx), "values": [[now_str]]})
        if not updates:
            return
        try:
            ws.batch_update(updates)
        except Exception:
            for u in updates:
                ws.update(u["range"], u["values"])

    # --------------------------- Eksekusi -------------------------------------
    if apply_btn:
        id_list = parse_ids(ids_raw)
        if not id_list:
            st.warning("Masukkan minimal satu ID.")
            st.stop()

        try:
            all_vals = ws.get_all_values()
        except Exception as e:
            st.error(f"Gagal membaca data worksheet: {e}")
            st.stop()

        try:
            id_col_idx = col_index(col_id_name, header)
            status_col_idx = col_index(col_status_name, header)
            ts_col_idx = col_index(col_ts_name, header) if col_ts_name != "(None)" else None
        except ValueError as e:
            st.error(str(e))
            st.stop()

        rows_map, not_found = find_rows_by_ids(all_vals, id_col_idx, id_list)

        if not rows_map:
            st.warning("Tidak ada ID yang cocok ditemukan.")
        else:
            try:
                batch_update_cells(ws, rows_map, status_col_idx, ts_col_idx, new_status)
                st.success(f"Berhasil mengupdate {len(rows_map)} baris.")
            except Exception as e:
                st.error(f"Gagal mengupdate: {e}")

        if not_found:
            st.info("ID tidak ditemukan: " + ", ".join(not_found))

    # --------------------------- Pratinjau ------------------------------------
    with st.expander("Lihat sampel data (maks 100 baris)"):
        try:
            df = pd.DataFrame(ws.get_all_records())
            st.dataframe(df.head(100), use_container_width=True)
        except Exception as e:
            st.error(f"Gagal menampilkan data: {e}")

# auto-run saat file dijalankan langsung
if __name__ == "__main__":
    app()
