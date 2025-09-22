# streamlit_app.py
import os
from pathlib import Path
from datetime import datetime
import importlib.util
import runpy

import streamlit as st
from PIL import Image

# === 1) set_page_config (HARUS paling awal & sekali saja) ===
BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
SIDEBAR_DIR = BASE_DIR / "sidebar"
FAVICON_PATH = ASSETS_DIR / "logo_pln.png"  # favicon/tab icon

page_icon = None
try:
    if FAVICON_PATH.exists():
        page_icon = Image.open(FAVICON_PATH)
except Exception:
    page_icon = None  # biarkan default jika gagal dibaca

st.set_page_config(
    page_title="PLN Area Malang - Dashboard Pengawas",
    page_icon=page_icon,
    layout="wide",
    initial_sidebar_state="expanded",
)

# (Opsional) cegah set_page_config dipanggil ulang di file lain
_st_set_page_config_original = st.set_page_config
st.set_page_config = lambda *a, **k: None


# === 2) Util zona waktu (ZoneInfo prefer, pytz fallback) ===
try:
    from zoneinfo import ZoneInfo  # Python 3.9+
    _HAS_ZONEINFO = True
except Exception:
    ZoneInfo = None
    _HAS_ZONEINFO = False
    try:
        import pytz  # type: ignore
    except Exception:
        pytz = None  # type: ignore

def now_jakarta() -> datetime:
    """Datetime aware Asia/Jakarta jika memungkinkan."""
    if _HAS_ZONEINFO and ZoneInfo is not None:
        try:
            return datetime.now(tz=ZoneInfo("Asia/Jakarta"))
        except Exception:
            pass
    if "pytz" in globals() and globals().get("pytz") is not None:
        try:
            return datetime.now(tz=pytz.timezone("Asia/Jakarta"))  # type: ignore
        except Exception:
            pass
    return datetime.now()


# === 3) Halaman / pages dictionary ===
pages = {
    "Home": "Home.py",
    "Input Data": "Input.py",
}


# === 4) Sidebar (logo + header + info) ===
with st.sidebar:
    cols = st.columns([1, 3])

    logo_sidebar_path = ASSETS_DIR / "logo_pln.png"
    if logo_sidebar_path.exists():
        try:
            cols[0].image(Image.open(logo_sidebar_path), width=110)
        except Exception:
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

    choice = st.selectbox("Pilih Menu", list(pages.keys()))

    st.markdown("---")
    st.subheader("🕒 Waktu Akses")
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


# === 5) Load & jalankan modul halaman ===
page_filename = pages.get(choice)
if not page_filename:
    st.error("Nama halaman tidak ditemukan untuk pilihan sidebar.")
    st.stop()

page_path = SIDEBAR_DIR / page_filename
if not page_path.exists():
    st.error(f"File halaman tidak ditemukan: {page_path}")
    st.stop()

try:
    # Muat sebagai modul supaya bisa panggil app() bila ada
    module_name = f"sidebar_{page_path.stem}"
    spec = importlib.util.spec_from_file_location(module_name, str(page_path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Gagal membuat ModuleSpec untuk: {page_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if hasattr(module, "app") and callable(module.app):
        module.app()
    else:
        # Jika tidak ada fungsi app(), eksekusi file apa adanya
        runpy.run_path(str(page_path), run_name="__main__")

except SystemExit:
    raise
except Exception as e:
    st.exception(e)
