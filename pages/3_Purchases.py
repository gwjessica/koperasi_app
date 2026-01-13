import streamlit as st
import pandas as pd
from db import get_connection

st.set_page_config(page_title="Purchases", page_icon="🛒", layout="wide")
st.title("🛒 Manajemen Pembelian & Pengeluaran")

conn = get_connection()
conn.row_factory = None
c = conn.cursor()

# =========================
# LOAD DATA
# =========================
# Query Lengkap untuk Tabel
query_list = """
SELECT 
    pc.id,
    p.project_name AS "Untuk Project",
    s.name AS "Supplier",
    pc.item AS "Nama Barang",
    pc.amount AS "Jml",
    pc.unit AS "Satuan",
    pc.price AS "Total Harga",
    pc.date AS "Tanggal"
FROM purchases pc
LEFT JOIN projects p ON p.id = pc.project_id
LEFT JOIN suppliers s ON s.id = pc.supplier_id
ORDER BY pc.date DESC
"""
df_purchases = pd.read_sql_query(query_list, conn)
df_purchases["Tanggal"] = pd.to_datetime(df_purchases["Tanggal"])

# =========================
# TABS LAYOUT
# =========================
tab1, tab2 = st.tabs(["📊 Analisis Pengeluaran", "📝 Input Pembelian"])

# --- TAB 1: ANALYTICS ---
with tab1:
    if df_purchases.empty:
        st.info("Belum ada data pembelian.")
    else:
        # Metrics
        col1, col2, col3 = st.columns(3)
        total_expense = df_purchases["Total Harga"].sum()
        avg_expense = df_purchases["Total Harga"].mean()
        top_item = df_purchases["Nama Barang"].mode()[0] if not df_purchases.empty else "-"

        col1.metric("Total Pengeluaran", f"Rp {total_expense:,.0f}")
        col2.metric("Rata-rata Transaksi", f"Rp {avg_expense:,.0f}")
        col3.metric("Item Paling Sering", f"{top_item}")

        st.divider()

        c1, c2 = st.columns(2)
        
        with c1:
            st.subheader("📅 Tren Pengeluaran Harian")
            # Group by Date
            daily_spend = df_purchases.groupby("Tanggal")["Total Harga"].sum()
            st.line_chart(daily_spend, color="#FF6384")
            
        with c2:
            st.subheader("🏗️ Biaya per Project")
            # Group by Project
            proj_spend = df_purchases.groupby("Untuk Project")["Total Harga"].sum().sort_values(ascending=False).head(10)
            st.bar_chart(proj_spend, color="#36A2EB", horizontal=True)

# --- TAB 2: MANAGEMENT ---
with tab2:
    col_form, col_data = st.columns([1, 2])
    
    with col_form:
        st.subheader("➕ Catat Pembelian Baru")
        with st.form("add_purchase_form"):
            # Load Data Pendukung
            projects = c.execute("SELECT id, project_name FROM projects WHERE status='ongoing'").fetchall()
            suppliers = c.execute("SELECT id, name FROM suppliers").fetchall()
            
            proj_map = {f"ID {p[0]} - {p[1]}": p[0] for p in projects}
            supp_map = {f"{s[1]}": s[0] for s in suppliers}
            
            sel_proj = st.selectbox("Project", list(proj_map.keys())) if projects else None
            sel_supp = st.selectbox("Supplier", list(supp_map.keys())) if suppliers else None
            
            item = st.text_input("Nama Barang / Kain")
            col_qty, col_unit = st.columns(2)
            with col_qty: amount = st.number_input("Jumlah", 0.1, step=0.5)
            with col_unit: unit = st.selectbox("Satuan", ["meter", "roll", "pcs", "kg", "pack"])
            
            price = st.number_input("Total Harga (Rp)", min_value=0, step=5000)
            
            if st.form_submit_button("Simpan Data"):
                if not item:
                    st.error("Nama barang harus diisi.")
                else:
                    pid = proj_map[sel_proj] if sel_proj else None
                    sid = supp_map[sel_supp] if sel_supp else None
                    
                    # 1. Insert Purchase
                    c.execute("""
                        INSERT INTO purchases (project_id, supplier_id, item, amount, unit, price, date)
                        VALUES (?, ?, ?, ?, ?, ?, DATE('now'))
                    """, (pid, sid, item, amount, unit, price))
                    
                    # 2. Auto Inventory IN
                    c.execute("""
                        INSERT INTO inventory (fabric_type, amount, direction, reason, project_id)
                        VALUES (?, ?, 'IN', 'purchase', ?)
                    """, (item, amount, pid))
                    
                    conn.commit()
                    st.success("Pembelian tercatat & Stok bertambah!")
                    st.rerun()

    with col_data:
        st.subheader("📋 Riwayat Pembelian")
        st.dataframe(
            df_purchases.style.format({"Total Harga": "Rp {:,.0f}", "Tanggal": "{:%d-%m-%Y}"}),
            use_container_width=True,
            height=500
        )