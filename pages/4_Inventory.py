import streamlit as st
import pandas as pd
from db import get_connection

st.title("📦 Inventory (Stok Kain)")

conn = get_connection()
conn.row_factory = None
c = conn.cursor()

# =========================
# LOAD PROJECTS
# =========================
projects = c.execute("""
    SELECT id, project_name
    FROM projects
""").fetchall()

project_map = {p[0]: p[1] for p in projects}

# =========================
# ADD INVENTORY
# =========================
with st.expander("➕ Tambah Inventory", expanded=False):
    with st.form("add_inventory_form"):
        fabric_type = st.text_input("Jenis Kain / Item")
        direction = st.selectbox("Arah", ["IN", "OUT"])
        amount = st.number_input("Jumlah", min_value=0.1, step=0.1)

        reason = st.selectbox(
            "Alasan",
            ["initial", "purchase", "production", "leftover"]
        )

        project_id = st.selectbox(
            "Project (opsional)",
            ["-"] + list(project_map.keys()),
            format_func=lambda x: "-" if x == "-" else f"ID {x} - {project_map[x]}"
        )

        submitted = st.form_submit_button("Simpan")

        if submitted:
            if not fabric_type:
                st.warning("Jenis kain wajib diisi.")
            else:
                c.execute("""
                    INSERT INTO inventory
                    (fabric_type, amount, direction, reason, project_id)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    fabric_type,
                    amount,
                    direction,
                    reason,
                    None if project_id == "-" else project_id
                ))
                conn.commit()
                st.success("Inventory berhasil ditambahkan.")
                st.rerun()

# =========================
# CURRENT STOCK
# =========================
st.subheader("📊 Stok Terkini")

stock_query = """
SELECT
    fabric_type,
    SUM(
        CASE WHEN direction='IN' THEN amount
             ELSE -amount
        END
    ) AS stock
FROM inventory
GROUP BY fabric_type
HAVING stock != 0
"""

df_stock = pd.read_sql_query(stock_query, conn)

if df_stock.empty:
    st.info("Belum ada stok.")
else:
    st.dataframe(df_stock, use_container_width=True)

# =========================
# INVENTORY HISTORY
# =========================
st.subheader("🕒 Riwayat Inventory")

history_query = """
SELECT
    id,
    fabric_type AS Item,
    amount AS Jumlah,
    direction AS Arah,
    reason AS Alasan,
    project_id AS Project,
    created_at AS Tanggal
FROM inventory
ORDER BY created_at DESC
"""

df_history = pd.read_sql_query(history_query, conn)

st.dataframe(df_history, use_container_width=True)
