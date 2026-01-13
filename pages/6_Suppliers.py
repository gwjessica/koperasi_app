import streamlit as st
import pandas as pd
from db import get_connection

st.title("🚚 Manajemen Supplier")

conn = get_connection()
conn.row_factory = None
c = conn.cursor()

# =========================
# ADD TAILOR
# =========================
with st.expander("➕ Tambah Supplier", expanded=False):
    with st.form("add_supplier_form"):
        supplier_name = st.text_input("Nama Supplier")
        address = st.text_input("Alamat")
        contact = st.text_input("Kontak")
        notes = st.text_area("Catatan")

        submit_supplier = st.form_submit_button("➕ Simpan Supplier")

        if submit_supplier:
            if not supplier_name:
                st.warning("Nama supplier wajib diisi.")
            else:
                c.execute("""
                    INSERT INTO suppliers
                    (name, address, contact, notes)
                    VALUES (?, ?, ?, ?)
                """, (
                    supplier_name,
                    address,
                    contact,
                    notes
                ))
                conn.commit()
                st.success("Supplier berhasil ditambahkan.")
                st.rerun()

# =========================
# LIST TAILORS
# =========================
st.subheader("📋 Daftar Supplier")

df = pd.read_sql_query("""
    SELECT
        id,
        name AS Nama,
        address AS Alamat,
        contact AS Kontak,
        notes AS Catatan
    FROM suppliers
    ORDER BY id DESC
""", conn)

if df.empty:
    st.info("Belum ada supplier.")
    st.stop()

st.dataframe(df, use_container_width=True)

# =========================
# EDIT / DELETE
# =========================
st.subheader("✏️ Edit Supplier")

selected_id = st.selectbox(
    "Pilih supplier",
    df["id"],
    format_func=lambda x: f"ID {x} - {df[df['id']==x]['Nama'].values[0]}"
)

supplier = df[df["id"] == selected_id].iloc[0]

with st.expander("Edit Supplier Data", expanded=False):
    with st.form("edit_supplier_form"):
        name = st.text_input("Nama", value=supplier["Nama"])
        address = st.text_input("Alamat", value=supplier["Alamat"])
        contact = st.text_input("Kontak", value=supplier["Kontak"])

        notes = st.text_area("Catatan", value=supplier["Catatan"])

        update = st.form_submit_button("💾 Edit")

        if update:
            c.execute("""
                UPDATE suppliers
                SET name=?, address=?, contact=?, notes=?
                WHERE id=?
            """, (
                name,
                address,
                contact,
                selected_id
            ))
            conn.commit()
            st.success("Data penjahit diperbarui.")
            st.rerun()


# HISTORY

st.subheader("📋 History Supplier")

df_history = pd.read_sql_query("""
SELECT
    s.name AS "Supplier",
    p.item AS "Material",
    p.amount AS "Jumlah",
    p.unit AS "Satuan",
    p.price AS "Harga",
    p.date AS "Tanggal",
    pr.project_name AS "Project"
FROM purchases p
JOIN suppliers s ON p.supplier_id = s.id
LEFT JOIN projects pr ON p.project_id = pr.id
ORDER BY p.date DESC;
""", conn)

if df_history.empty:
    st.info("Belum ada pembelian.")

st.dataframe(df_history, use_container_width=True)

selected_supplier = st.selectbox(
    "See by Supplier",
    df["Nama"]
)

filtered = df_history[df_history["Supplier"] == selected_supplier]
st.dataframe(filtered)
