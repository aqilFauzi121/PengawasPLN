# streamlit_app.py — safe router for pages in /sidebar
import streamlit as st

# --- Call once, at the very top ---
st.set_page_config(page_title="PKL Dashboard", layout="wide", initial_sidebar_state="expanded")

# Prevent double calls from subpages
_st_set_page_config_original = st.set_page_config
st.set_page_config = lambda *a, **k: None

# --- Standard libs
import os
from pathlib import Path
from datetime import datetime

# --- Timezone helper (ZoneInfo with safe fallback to pytz) ---
try:
    from zoneinfo import ZoneInfo  # Py>=3.9
except Exception:  # pragma: no cover
    ZoneInfo = None
    try:
        import pytz  # type: ignore
    except Exception:
        pytz = None  # type: ignore

def now_local(tz_name: str = "Asia/Jakarta"):
    """Return aware datetime in the provided timezone (works with zoneinfo or pytz)."""
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
    # last resort: naive
    return datetime.now()

# --- Paths ---
BASE_DIR: Path = Path(__file__).resolve().parent
PAGES_DIR: Path = BASE_DIR / "sidebar"
ASSETS_DIR: Path = BASE_DIR / "assets"
STREAMLIT_DIR: Path = BASE_DIR / ".streamlit"

# --- Optional CSS injection ---
css_path = ASSETS_DIR / "styles.css"
if css_path.exists():
    try:
        st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)
    except Exception:
        pass

# --- Sidebar ---
st.sidebar.title("PKL")
st.sidebar.caption(f"Local time: {now_local().strftime('%Y-%m-%d %H:%M:%S')}")

# Discover available page files under /sidebar (only top-level .py)
pages = []
if PAGES_DIR.exists():
    for p in sorted(PAGES_DIR.glob("*.py")):
        if p.name.startswith("_"):
            continue
        pages.append(p)
else:
    st.sidebar.error("Folder 'sidebar/' tidak ditemukan.")

# Build label -> path mapping with human-friendly names
def _label_from_path(path: Path) -> str:
    base = path.stem.replace("_", " ").strip()
    # Capitalize first letter of each word
    return " ".join(w.capitalize() for w in base.split())

page_labels = [_label_from_path(p) for p in pages]
if not page_labels:
    st.error("Tidak ada halaman ditemukan di folder 'sidebar/'. Tambahkan file .py seperti Home.py atau Input.py")

selected = st.sidebar.radio("Halaman", options=page_labels or ["(tidak ada)"], index=0 if page_labels else 0)

# --- Safe dynamic import ---
import importlib.util
import types

def import_module_from_path(module_name: str, path: Path) -> types.ModuleType | None:
    """Safely import a module from file path; return None on failure."""
    try:
        if not path.exists():
            st.error(f"File tidak ditemukan: {path}")
            return None
        spec = importlib.util.spec_from_file_location(module_name, str(path))
        if spec is None or spec.loader is None:
            st.error(f"Gagal membuat import spec untuk: {path.name}")
            return None
        module = importlib.util.module_from_spec(spec)
        # loader sudah dicek di atas
        spec.loader.exec_module(module)  # type: ignore[union-attr]
        return module
    except Exception as e:
        st.exception(e)
        return None

# --- Render selected page ---
def render_page(path: Path) -> None:
    module_name = f"sidebar.{path.stem}"
    module = import_module_from_path(module_name, path)
    if module is None:
        return
    # Kalau file halaman mendefinisikan app(), panggil. Kalau tidak, biarkan (UI mungkin sudah dibuat top-level).
    if hasattr(module, "app") and callable(getattr(module, "app")):
        try:
            module.app()
        except Exception as e:
            st.exception(e)

# --- Main: render the chosen page ---
if page_labels:
    target_idx = page_labels.index(selected)
    render_page(pages[target_idx])

# --- Footer note for developers ---
st.markdown("---")
st.caption("Tips: Definisikan fungsi `app()` pada setiap file di folder `sidebar/` dan jangan panggil `st.set_page_config()` di sana.")