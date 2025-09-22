# streamlit_app.py

import streamlit as st
from PIL import Image

# --- Page Config (harus paling awal) ---
pln_logo = Image.open("assets/logo-pln.png")
st.set_page_config(
    page_title="PLN Area Malang - Dashboard Pengawas",
    page_icon=pln_logo,
    layout="wide",
    initial_sidebar_state="expanded"
)

# === 2) imports lain ===
import runpy
import importlib.util
import os
from pathlib import Path
from datetime import datetime
import time

# timezone handling (ZoneInfo preferred, pytz fallback)
_HAS_ZONEINFO = False
ZoneInfo = None  # default supaya selalu terdefinisi
try:
    from zoneinfo import ZoneInfo as _ZoneInfo
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


# === 3) Sidebar ===
SIDEBAR_DIR = Path(__file__).parent / "sidebar"
PAGES = {p.stem: p.name for p in SIDEBAR_DIR.glob("*.py")}

with st.sidebar:
    st.image("assets/logo-pln.png", width=120)
    st.title("PKL")
    st.markdown(f"Local time: {now_jakarta().strftime('%Y-%m-%d %H:%M:%S')}")
    choice = st.radio("Halaman", list(PAGES.keys()))

# === 4) Load halaman sidebar ===
page_filename = PAGES.get(choice)
if not page_filename:
    st.error("Halaman tidak ditemukan")
    st.stop()

page_path = SIDEBAR_DIR / page_filename

try:
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
