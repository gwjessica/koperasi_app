import streamlit as st
import pandas as pd
import time
import base64
from db import get_connection

# =========================================
# 1. KONFIGURASI HALAMAN (WAJIB PALING ATAS)
# =========================================
st.set_page_config(page_title="Dashboard Utama", page_icon="📊", layout="wide")

# --- FUNGSI BANTUAN UNTUK GAMBAR LOKAL ---
def get_base64_image(image_path):
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except FileNotFoundError:
        return ""

# Ubah gambar lokal jadi format Base64
# Pastikan file PCU.png dan SUTD.png ada di folder yang sama dengan Dashboard.py
petra_b64 = get_base64_image("PCU.png")
sutd_b64 = get_base64_image("SUTD.png")

# Masukkan ke variabel URL
LOGO_PETRA = f"data:image/png;base64,{petra_b64}"
LOGO_KOPERASI = f"data:image/png;base64,{sutd_b64}"

# =========================================
# 2. FITUR LOADER / SPLASH SCREEN (DARK MODE FRIENDLY)
# =========================================
if "is_loaded" not in st.session_state:
    loader_container = st.empty()
    
    with loader_container.container():
        # --- CSS STYLE ---
        st.markdown(f"""
        <style>
            /* Container utama: Transparan */
            .loader-wrapper {{
                display: flex;
                flex-direction: column;
                justify_content: center;
                align-items: center;
                margin-top: 10vh;
                padding: 40px;
            }}

            /* Container Logo */
            .logo-container {{
                display: flex;
                gap: 40px;
                margin-bottom: 30px;
                align-items: center;
                justify-content: center;
            }}
            .custom-logo {{
                height: 100px;
                width: auto;
                transition: transform 0.3s ease;
            }}
            .custom-logo:hover {{
                transform: scale(1.1);
            }}

            /* Spinner Loading */
            .loader-spinner {{
                border: 6px solid #444; 
                border-top: 6px solid #4CAF50; 
                border-radius: 50%;
                width: 60px;
                height: 60px;
                animation: spin 1s linear infinite;
                margin-top: 30px;
                margin-bottom: 20px;
            }}

            @keyframes spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}
            
            /* Teks Putih untuk Dark Mode */
            .loader-title {{
                font-size: 2.5em;
                font-weight: 700;
                color: #ffffff;
                margin-bottom: 10px;
                text-align: center;
            }}
            .loader-caption {{
                font-size: 1.2em;
                color: #cccccc;
                font-style: italic;
                text-align: center;
                margin-bottom: 20px;
            }}
             .status-text {{
                font-size: 1em;
                font-weight: 500;
                color: #4CAF50;
                margin-top: 10px;
                text-align: center;
            }}
        </style>
        """, unsafe_allow_html=True)

        # --- HTML LOADER ---
        st.markdown(f"""
            <div class="loader-wrapper">
                <div class="logo-container">
                    <img src="{LOGO_PETRA}" class="custom-logo" alt="Logo Petra">
                    <img src="{LOGO_KOPERASI}" class="custom-logo" alt="Logo SUTD">
                </div>
                <div class="loader-title">Sistem Koperasi Mahasiswa</div>
                <div class="loader-caption">Universitas Kristen Petra</div>
                <div class="loader-spinner"></div>
            </div>
        """, unsafe_allow_html=True)

        status_text_placeholder = st.empty()

        # --- ANIMASI LOADING ---
        for i in range(100):
            time.sleep(0.02) 
            
            if i == 10:
                status_text_placeholder.markdown("<p class='status-text'>🔄 Menghubungkan ke Database...</p>", unsafe_allow_html=True)
            elif i == 40:
                status_text_placeholder.markdown("<p class='status-text'>📂 Memuat Data Project & Inventaris...</p>", unsafe_allow_html=True)
            elif i == 70:
                status_text_placeholder.markdown("<p class='status-text'>🧵 Sinkronisasi Data Penjahit...</p>", unsafe_allow_html=True)
            elif i == 95:
                status_text_placeholder.markdown("<p class='status-text'>✅ Siap!</p>", unsafe_allow_html=True)

        time.sleep(0.5)
        
    loader_container.empty()
    st.session_state["is_loaded"] = True

# =========================================
# 3. KODE DASHBOARD UTAMA
# =========================================

st.title("🚀 Dashboard Manajerial")
st.markdown("Ringkasan performa bisnis, status produksi, dan peringatan dini.")

conn = get_connection()
conn.row_factory = None
c = conn.cursor()

# --- A. KEY METRICS ---
total_omzet = c.execute("SELECT SUM(price_per_item * amount) FROM projects").fetchone()[0] or 0
total_spend = c.execute("SELECT SUM(price) FROM purchases").fetchone()[0] or 0
net_profit = total_omzet - total_spend

active_projects = c.execute("SELECT COUNT(*) FROM projects WHERE status='ongoing'").fetchone()[0]
idle_tailors = c.execute("SELECT COUNT(*) FROM tailors WHERE status='idle'").fetchone()[0]
low_stock_items = c.execute("SELECT COUNT(DISTINCT fabric_type) FROM inventory GROUP BY fabric_type HAVING SUM(CASE WHEN direction='IN' THEN amount ELSE -amount END) < 10").fetchone()
low_stock_count = low_stock_items[0] if low_stock_items else 0

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("💰 Net Profit", f"Rp {net_profit:,.0f}")
col2.metric("📉 Total Pengeluaran", f"Rp {total_spend:,.0f}")
col3.metric("🔨 Project Aktif", f"{active_projects} Project")
col4.metric("🧵 Penjahit Ready", f"{idle_tailors} Org")
col5.metric("⚠️ Stok Menipis", f"{low_stock_count} Item", delta_color="inverse")

st.divider()

# --- B. CHARTS ---
col_chart1, col_chart2 = st.columns([2, 1])

with col_chart1:
    st.subheader("📈 Tren Keuangan (Project)")
    query_finance = """
    SELECT 
        project_name, 
        (price_per_item * amount) as revenue,
        base_fee + (amount * tailor_fee_per_item) as cost
    FROM projects 
    ORDER BY id DESC LIMIT 10
    """
    df_finance = pd.read_sql_query(query_finance, conn)
    
    if not df_finance.empty:
        st.bar_chart(
            df_finance.set_index("project_name"),
            color=["#36A2EB", "#FF6384"],
            stack=False
        )
    else:
        st.info("Belum ada data keuangan.")

with col_chart2:
    st.subheader("📊 Status Produksi")
    df_status = pd.read_sql_query("SELECT status, COUNT(*) as count FROM projects GROUP BY status", conn)
    
    if not df_status.empty:
        st.dataframe(df_status.style.background_gradient(cmap="Blues"), use_container_width=True, hide_index=True)
        st.bar_chart(df_status.set_index("status"), color="#4BC0C0")
    else:
        st.info("Belum ada data project.")

# --- C. RECENT ACTIVITY ---
st.subheader("🕒 Aktivitas Terkini")
tab_a, tab_b = st.tabs(["Project Baru", "Transaksi Material"])

with tab_a:
    df_recent_proj = pd.read_sql_query("SELECT project_name, customer_name, status, deadline FROM projects ORDER BY id DESC LIMIT 5", conn)
    st.dataframe(df_recent_proj, use_container_width=True, hide_index=True)

with tab_b:
    df_recent_buy = pd.read_sql_query("SELECT item, amount, unit, price, date FROM purchases ORDER BY date DESC LIMIT 5", conn)
    st.dataframe(df_recent_buy, use_container_width=True, hide_index=True)