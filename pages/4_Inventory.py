import streamlit as st
import pandas as pd
from db import get_connection

st.set_page_config(page_title="Inventory", page_icon="🧶", layout="wide")
st.title("🧶 Gudang & Inventaris Kain")

conn = get_connection()
conn.row_factory = None
c = conn.cursor()

# =========================
# LOAD DATA STOCK
# =========================
stock_query = """
SELECT
    fabric_type AS "Jenis Kain",
    SUM(CASE WHEN direction='IN' THEN amount ELSE -amount END) AS "Stok Akhir"
FROM inventory
GROUP BY fabric_type
HAVING "Stok Akhir" != 0
ORDER BY "Stok Akhir" DESC
"""
df_stock = pd.read_sql_query(stock_query, conn)

# Load History
history_query = """
SELECT id, fabric_type, amount, direction, reason, created_at 
FROM inventory ORDER BY created_at DESC
"""
df_history = pd.read_sql_query(history_query, conn)

# =========================
# TABS LAYOUT
# =========================
tab1, tab2 = st.tabs(["📊 Monitor Stok", "📝 Keluar/Masuk Barang"])

# ------------------------------------------------------------------
# TAB 1: DASHBOARD
# ------------------------------------------------------------------
with tab1:
    if df_stock.empty:
        st.info("Gudang kosong.")
    else:
        # Metrics
        col1, col2, col3 = st.columns(3)
        total_items = len(df_stock)
        total_meters = df_stock["Stok Akhir"].sum()
        low_stock = len(df_stock[df_stock["Stok Akhir"] < 10]) # Asumsi <10m = sedikit

        col1.metric("Varian Kain", f"{total_items} Jenis")
        col2.metric("Total Aset (Meter)", f"{total_meters:,.1f} m")
        col3.metric("Stok Menipis (<10m)", f"{low_stock} Jenis", delta_color="inverse")
        
        st.divider()
        
        c1, c2 = st.columns([2, 1])
        
        with c1:
            st.subheader("📊 Level Stok per Jenis Kain")
            # Bar chart horizontal
            st.bar_chart(df_stock.set_index("Jenis Kain"), color="#FF9F40", horizontal=True)
            
        with c2:
            st.subheader("⚠️ Perlu Restock")
            low_stock_df = df_stock[df_stock["Stok Akhir"] < 10]
            if not low_stock_df.empty:
                for idx, row in low_stock_df.iterrows():
                    st.warning(f"**{row['Jenis Kain']}**: Sisa {row['Stok Akhir']} m")
            else:
                st.success("Semua stok aman.")

# ------------------------------------------------------------------
# TAB 2: MANAJEMEN INVENTARIS
# ------------------------------------------------------------------
with tab2:
    col_input, col_table = st.columns([1, 2])
    
    with col_input:
        st.subheader("📝 Catat Transaksi")
        with st.form("inv_form"):
            fabric_type = st.text_input("Nama Kain / Item")
            direction = st.selectbox("Arah", ["IN (Masuk)", "OUT (Keluar)"])
            amount = st.number_input("Jumlah (Meter/Pcs)", min_value=0.1, step=0.5)
            reason = st.selectbox("Keterangan", ["purchase", "production", "leftover", "initial"])
            
            # Load project utk referensi
            proj_data = c.execute("SELECT id, project_name FROM projects WHERE status='ongoing'").fetchall()
            proj_opts = {f"ID {p[0]} - {p[1]}": p[0] for p in proj_data}
            proj_select = st.selectbox("Untuk Project (Opsional)", ["-"] + list(proj_opts.keys()))
            
            submitted = st.form_submit_button("Simpan Data")
            
            if submitted:
                real_dir = "IN" if "IN" in direction else "OUT"
                proj_id = proj_opts[proj_select] if proj_select != "-" else None
                
                c.execute("INSERT INTO inventory (fabric_type, amount, direction, reason, project_id) VALUES (?, ?, ?, ?, ?)",
                          (fabric_type, amount, real_dir, reason, proj_id))
                conn.commit()
                st.success("Berhasil disimpan.")
                st.rerun()

    with col_table:
        st.subheader("🕒 Riwayat Transaksi Terakhir")
        st.dataframe(df_history, use_container_width=True, height=400)