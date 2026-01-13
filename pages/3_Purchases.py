import streamlit as st
import pandas as pd
from db import get_connection
from datetime import date

st.title("🧵 Purchases (Pembelian Bahan)")

conn = get_connection()
conn.row_factory = None
c = conn.cursor()

# =========================
# LOAD PROJECT & SUPPLIER
# =========================
projects = c.execute("""
    SELECT id, project_name
    FROM projects
    WHERE status='ongoing'
""").fetchall()

suppliers = c.execute("""
    SELECT id, name
    FROM suppliers
""").fetchall()

if not projects:
    st.warning("Belum ada project ongoing.")
    st.stop()

# =========================
# ADD PURCHASE
# =========================
with st.expander("➕ Tambah Pembelian", expanded=False):
    with st.form("add_purchase_form"):
        project_id = st.selectbox(
            "Project",
            [p[0] for p in projects],
            format_func=lambda x: f"ID {x} - {[p[1] for p in projects if p[0]==x][0]}"
        )

        supplier_id = st.selectbox(
            "Supplier",
            [s[0] for s in suppliers],
            format_func=lambda x: [s[1] for s in suppliers if s[0]==x][0]
        ) if suppliers else None

        item = st.text_input("Item (contoh: Kain Drill)")
        amount = st.number_input("Jumlah", min_value=0.1, step=0.1)
        unit = st.selectbox("Satuan", ["meter", "roll", "pcs"])
        price = st.number_input("Total Harga (Rp)", min_value=0)

        submitted = st.form_submit_button("Simpan Pembelian")

        if submitted:
            if not item:
                st.warning("Item wajib diisi.")
            else:
                # 1. simpan purchase
                c.execute("""
                    INSERT INTO purchases
                    (project_id, supplier_id, item, amount, unit, price, date)
                    VALUES (?, ?, ?, ?, ?, ?, DATE('now'))
                """, (
                    project_id,
                    supplier_id,
                    item,
                    amount,
                    unit,
                    price
                ))

                # ambil purchase id terakhir
                purchase_id = c.lastrowid

                # 2. AUTO inventory IN
                c.execute("""
                    INSERT INTO inventory
                    (fabric_type, amount, direction, reason, project_id)
                    VALUES (?, ?, 'IN', 'purchase', ?)
                """, (
                    item,        # fabric_type
                    amount,      # jumlah
                    project_id
                ))

                conn.commit()
                st.success("Pembelian berhasil ditambahkan.")
                st.rerun()

# =========================
# LIST PURCHASES
# =========================
st.subheader("📋 Daftar Pembelian")

query = """
SELECT 
    pc.id,
    p.project_name AS Project,
    pc.item AS Item,
    pc.amount AS Jumlah,
    pc.unit AS Satuan,
    pc.price AS Harga,
    pc.date AS Tanggal
FROM purchases pc
JOIN projects p ON p.id = pc.project_id
ORDER BY pc.date DESC
"""

df = pd.read_sql_query(query, conn)

if df.empty:
    st.info("Belum ada pembelian.")
else:
    st.dataframe(df, use_container_width=True)

# =========================
# TOTAL COST PER PROJECT
# =========================
st.subheader("💰 Total Biaya per Project")

summary = pd.read_sql_query("""
    SELECT 
        p.project_name AS Project,
        SUM(pc.price) AS Total_Biaya
    FROM projects p
    LEFT JOIN purchases pc ON pc.project_id = p.id
    GROUP BY p.id
""", conn)

st.dataframe(summary, use_container_width=True)
