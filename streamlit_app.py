# streamlit_app.py (REWRITTEN)
import streamlit as st

# === 1) set_page_config harus dipanggil PERTAMA kali (dan hanya sekali) ===
st.set_page_config(
    page_title="PLN Area Malang - Dashboard Pengawas", 
    page_icon="./assets/logo_pln.png",  # path ke logo PLN sebagai favicon
    layout="wide", 
    initial_sidebar_state="expanded"
)

# Setelah dipanggil sekali, kita "amankan" panggilan selanjutnya supaya tidak melempar error
# (idealnya hapus/komentari semua st.set_page_config di file-file page)
_st_set_page_config_original = st.set_page_config  # simpan (opsional)
st.set_page_config = lambda *a, **k: None  # jadi no-op kalau dipanggil lagi

# === 2) imports lain ===
import runpy
import importlib.util
import os
from pathlib import Path
from PIL import Image
from datetime import datetime
import time

# timezone handling (ZoneInfo preferred, pytz fallback)
_HAS_ZONEINFO = False
ZoneInfo = None
try:
    from zoneinfo import ZoneInfo as _ZoneInfo  # Python 3.9+
    ZoneInfo = _ZoneInfo
    _HAS_ZONEINFO = True
except Exception:
    try:
        import pytz
        _HAS_ZONEINFO = False
    except Exception:
        pytz = None
        _HAS_ZONEINFO = False

def now_jakarta():
    """Return timezone-aware datetime in Asia/Jakarta if possible."""
    if _HAS_ZONEINFO and ZoneInfo is not None:
        try:
            return datetime.now(tz=ZoneInfo("Asia/Jakarta"))
        except Exception:
            pass
    if 'pytz' in globals() and pytz is not None:
        try:
            return datetime.now(tz=pytz.timezone("Asia/Jakarta"))
        except Exception:
            pass
    return datetime.now()

# === 3) base paths (menggunakan Path untuk robust) ===
BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
SIDEBAR_DIR = BASE_DIR / "sidebar"

# === 4) halaman / pages dictionary ===
pages = {
    "Home": "Home.py",
    "Input Data": "Input.py",
}

# === 5) Sidebar content (logo + header) ===
LOGO_PATH = ASSETS_DIR / "logo_pln.png"  # ganti jika beda nama

with st.sidebar:
    cols = st.columns([1, 3])
    if LOGO_PATH.exists():
        try:
            img = Image.open(LOGO_PATH)
            cols[0].image(img, width=110)
        except Exception as e:
            cols[0].write("Logo error")
    else:
        cols[0].warning("Logo tidak ditemukan\n(assets/logo_pln.png)")

    cols[1].markdown("<h3 style='margin:0'>PLN AREA MALANG</h3>", unsafe_allow_html=True)
    cols[1].caption("Dashboard Pengawas Pekerjaan PLN")
    st.markdown(
        "<a href='https://maps.app.goo.gl/T6beHxT9WBxhFBDXA' target='_blank' style='text-decoration:none;'>"
        "📍 Jl. Jenderal Basuki Rahmat No.100, Klojen, Kota Malang</a>",
        unsafe_allow_html=True
    )
    st.markdown("---")

    # page selector
    choice = st.selectbox("Pilih Menu", list(pages.keys()))

    st.markdown("---")
    st.subheader("🕐 Waktu Akses")
    t = now_jakarta()
    st.write(f"📅 {t.strftime('%d-%m-%Y')}")
    st.write(f"⏰ {t.strftime('%H:%M:%S')}")
    st.markdown("---")

    # footer developers (opsional)
    dev_logo = ASSETS_DIR / "Logo_Universitas_Brawijaya.svg.png"
    if dev_logo.exists():
        try:    
            c1, c2 = st.columns([1, 2])
            c1.image(dev_logo, width=100)
            c2.markdown("<b>Developed by<br>Brawijaya University </b>", unsafe_allow_html=True)
            c2.caption("Faculty of Computer Science") 
        except Exception:
            st.write("Developed by: Brawijaya University")
    else:
        st.write("Developed by: Brawijaya University")

    st.markdown(
        "<a href='https://www.linkedin.com/in/naufal-arsya-dinata/' target='_blank'>@Naufal Arsya Dinata</a><br>"
        "<a href='https://www.linkedin.com/in/rizky-akba//' target='_blank'>@Rizky Akbar</a><br>"
        "<a href='https://www.linkedin.com/in/yudaneru-vebrianto/' target='_blank'>@Yudaneru Vebrianto</a><br>"
        "<a href='https://www.linkedin.com/in/andreas-wirawan-dananjaya-788a1828a/' target='_blank'>@Andreas Wirawan</a><br>"
        "<a href='https://www.linkedin.com/in/danishgyanpramana/' target='_blank'>@Danish Gyan Pramana</a><br>"
        "<a href='https://www.linkedin.com/in/muhammad-aqil-fauzi' target='_blank'>@Muhammad Aqil Fauzi</a>",
        unsafe_allow_html=True
    )

# === 6) Load & run page module safely ===
# Path to selected page file
page_filename = pages.get(choice)
if not page_filename:
    st.error("Nama halaman tidak ditemukan untuk pilihan sidebar.")
    st.stop()

page_path = SIDEBAR_DIR / page_filename

if not page_path.exists():
    st.error(f"File halaman tidak ditemukan: {page_path}")
else:
    try:
        # create a unique module name to avoid collisions
        module_name = f"sidebar_{page_path.stem}"

        spec = importlib.util.spec_from_file_location(module_name, str(page_path))
        if spec is None or spec.loader is None:
            raise ImportError(f"Gagal membuat ModuleSpec untuk: {page_path}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        if hasattr(module, "app") and callable(module.app):
            module.app()

    except Exception as e:
        st.exception(e)
