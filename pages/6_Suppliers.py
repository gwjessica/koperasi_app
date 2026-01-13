import streamlit as st
import pandas as pd
from db import get_connection

st.set_page_config(page_title="Suppliers", page_icon="🚚", layout="wide")
st.title("🚚 Partner & Supplier")

conn = get_connection()
conn.row_factory = None
c = conn.cursor()

# =========================
# LOAD DATA
# =========================
df_suppliers = pd.read_sql_query("SELECT id, name, address, contact, notes FROM suppliers ORDER BY name", conn)

# Load Spending per Supplier (Join table)
query_spend = """
SELECT 
    s.name AS "Supplier",
    COUNT(p.id) AS "Total Transaksi",
    COALESCE(SUM(p.price), 0) AS "Total Belanja"
FROM suppliers s
LEFT JOIN purchases p ON p.supplier_id = s.id
GROUP BY s.id
ORDER BY "Total Belanja" DESC
"""
df_spend = pd.read_sql_query(query_spend, conn)

# =========================
# TABS LAYOUT
# =========================
tab1, tab2 = st.tabs(["📊 Analisis Partner", "📇 Data Supplier"])

# --- TAB 1: INSIGHTS ---
with tab1:
    if df_spend.empty:
        st.info("Belum ada data transaksi dengan supplier.")
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🏆 Top Supplier (Berdasarkan Nilai Belanja)")
            st.bar_chart(df_spend.set_index("Supplier")["Total Belanja"], color="#4CAF50", horizontal=True)
            
        with col2:
            st.subheader("📦 Frekuensi Pembelian")
            st.bar_chart(df_spend.set_index("Supplier")["Total Transaksi"], color="#FF9F40")

        st.subheader("Rincian Kinerja Supplier")
        st.dataframe(
            df_spend.style.format({"Total Belanja": "Rp {:,.0f}"}),
            use_container_width=True
        )

# --- TAB 2: CRUD ---
with tab2:
    col_input, col_list = st.columns([1, 2])
    
    with col_input:
        st.subheader("➕ Tambah Partner Baru")
        with st.form("add_supp"):
            name = st.text_input("Nama Toko / Supplier")
            contact = st.text_input("Kontak (HP/Telp)")
            address = st.text_area("Alamat")
            notes = st.text_input("Catatan (Misal: Spesialis Kancing)")
            
            if st.form_submit_button("Simpan"):
                if name:
                    c.execute("INSERT INTO suppliers (name, address, contact, notes) VALUES (?,?,?,?)", 
                              (name, address, contact, notes))
                    conn.commit()
                    st.success("Tersimpan!")
                    st.rerun()
                else:
                    st.warning("Nama wajib diisi.")
                    
    with col_list:
        st.subheader("📇 Database Kontak")
        st.dataframe(df_suppliers, use_container_width=True)
        
        with st.expander("Edit Data Supplier"):
            sel_id = st.selectbox("Pilih Supplier utk Edit", df_suppliers["id"], format_func=lambda x: f"ID {x}")
            if sel_id:
                curr = df_suppliers[df_suppliers["id"] == sel_id].iloc[0]
                with st.form("edit_supp"):
                    n_name = st.text_input("Nama", curr["name"])
                    n_contact = st.text_input("Kontak", curr["contact"])
                    n_addr = st.text_input("Alamat", curr["address"])
                    if st.form_submit_button("Update"):
                        c.execute("UPDATE suppliers SET name=?, contact=?, address=? WHERE id=?", (n_name, n_contact, n_addr, sel_id))
                        conn.commit()
                        st.success("Updated.")
                        st.rerun()