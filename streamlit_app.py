# streamlit_app.py — safe router for pages di /sidebar
import streamlit as st

# --- Panggil sekali di entrypoint ---
st.set_page_config(page_title="PKL Dashboard", layout="wide", initial_sidebar_state="expanded")

# Cegah sub-halaman memanggil set_page_config lagi
_st_set_page_config_original = st.set_page_config
st.set_page_config = lambda *a, **k: None

# --- Std libs
from pathlib import Path
from datetime import datetime

# --- Timezone helper (ZoneInfo + fallback) ---
try:
    from zoneinfo import ZoneInfo  # Py>=3.9
except Exception:
    ZoneInfo = None
    try:
        import pytz  # type: ignore
    except Exception:
        pytz = None  # type: ignore

def now_local(tz_name: str = "Asia/Jakarta"):
    if ZoneInfo is not None:
        try:
            return datetime.now(ZoneInfo(tz_name))
        except Exception:
            pass
    if 'pytz' in globals() and pytz is not None:
        try:
            return datetime.now(pytz.timezone(tz_name))  # type: ignore[attr-defined]
        except Exception:
            pass
    return datetime.now()

# --- Paths ---
BASE_DIR: Path = Path(__file__).resolve().parent
PAGES_DIR: Path = BASE_DIR / "sidebar"
ASSETS_DIR: Path = BASE_DIR / "assets"

# --- Optional CSS ---
css_path = ASSETS_DIR / "styles.css"
if css_path.exists():
    try:
        st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)
    except Exception:
        pass

# --- Sidebar ---
st.sidebar.title("PKL")
st.sidebar.caption(f"Local time: {now_local().strftime('%Y-%m-%d %H:%M:%S')}")

# Katalog halaman
pages = []
if PAGES_DIR.exists():
    for p in sorted(PAGES_DIR.glob("*.py")):
        if not p.name.startswith("_"):
            pages.append(p)
else:
    st.sidebar.error("Folder 'sidebar/' tidak ditemukan.")

def _label_from_path(path: Path) -> str:
    base = path.stem.replace("_", " ").strip()
    return " ".join(w.capitalize() for w in base.split())

page_labels = [_label_from_path(p) for p in pages]
if not page_labels:
    st.error("Tidak ada halaman di folder 'sidebar/'. Tambahkan Home.py atau Input.py.")

selected = st.sidebar.radio("Halaman", options=page_labels or ["(tidak ada)"], index=0 if page_labels else 0)

# --- Import dinamis yang aman ---
import importlib.util
import types

def import_module_from_path(module_name: str, path: Path) -> types.ModuleType | None:
    try:
        if not path.exists():
            st.error(f"File tidak ditemukan: {path}")
            return None
        spec = importlib.util.spec_from_file_location(module_name, str(path))
        if spec is None or spec.loader is None:
            st.error(f"Gagal membuat import spec untuk: {path.name}")
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # type: ignore[union-attr]
        return module
    except Exception as e:
        st.exception(e)
        return None

def render_page(path: Path) -> None:
    module_name = f"sidebar.{path.stem}"
    module = import_module_from_path(module_name, path)
    if module is None:
        return
    if hasattr(module, "app") and callable(getattr(module, "app")):
        try:
            module.app()
        except Exception as e:
            st.exception(e)

if page_labels:
    target_idx = page_labels.index(selected)
    render_page(pages[target_idx])

st.markdown("---")
st.caption("Tips: Definisikan fungsi `app()` pada setiap file di folder `sidebar/` dan jangan panggil `st.set_page_config()` di sana.")
