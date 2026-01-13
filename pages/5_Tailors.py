import streamlit as st
import pandas as pd
from db import get_connection

st.title("🧑‍🧵 Manajemen Penjahit")

conn = get_connection()
conn.row_factory = None
c = conn.cursor()

# =========================
# ADD TAILOR
# =========================
with st.expander("➕ Tambah Penjahit", expanded=False):
    with st.form("add_tailor_form"):
        name = st.text_input("Nama Penjahit")
        age = st.number_input("Umur", min_value=15, max_value=80)
        distance_km = st.number_input("Jarak ke Workshop (km)", min_value=0.0, step=0.1)
        speed = st.number_input("Kecepatan (pcs / hari)", min_value=0.1, step=0.1)

        specialty = st.selectbox(
            "Spesialisasi",
            ["uniform", "custom"]
        )

        contact = st.text_input("Kontak (HP / WA)")

        submitted = st.form_submit_button("Simpan")

        if submitted:
            if not name:
                st.warning("Nama penjahit wajib diisi.")
            else:
                c.execute("""
                    INSERT INTO tailors
                    (name, age, distance_km, speed_clothes_per_day, specialty, status, contact)
                    VALUES (?, ?, ?, ?, ?, 'idle', ?)
                """, (
                    name,
                    age,
                    distance_km,
                    speed,
                    specialty,
                    contact
                ))
                conn.commit()
                st.success("Penjahit berhasil ditambahkan.")
                st.rerun()

# =========================
# LIST TAILORS
# =========================
st.subheader("📋 Daftar Penjahit")

df = pd.read_sql_query("""
    SELECT
        id,
        name AS Nama,
        age AS Umur,
        distance_km AS "Jarak (km)",
        speed_clothes_per_day AS "Kecepatan (pcs/hari)",
        specialty AS Spesialisasi,
        status AS Status,
        contact AS Kontak
    FROM tailors
    ORDER BY id DESC
""", conn)

if df.empty:
    st.info("Belum ada penjahit.")
    st.stop()

st.dataframe(df, use_container_width=True)

# =========================
# EDIT / DELETE
# =========================
st.subheader("✏️ Edit / Hapus Penjahit")

selected_id = st.selectbox(
    "Pilih Penjahit",
    df["id"],
    format_func=lambda x: f"ID {x} - {df[df['id']==x]['Nama'].values[0]}"
)

tailor = df[df["id"] == selected_id].iloc[0]

with st.form("edit_tailor_form"):
    name = st.text_input("Nama", value=tailor["Nama"])
    age = st.number_input("Umur", value=int(tailor["Umur"]))
    distance_km = st.number_input("Jarak (km)", value=float(tailor["Jarak (km)"]))
    speed = st.number_input(
        "Kecepatan (pcs / hari)",
        value=float(tailor["Kecepatan (pcs/hari)"])
    )

    specialty = st.selectbox(
        "Spesialisasi",
        ["uniform", "custom"],
        index=0 if tailor["Spesialisasi"] == "uniform" else 1
    )

    status = st.selectbox(
        "Status",
        ["idle", "working"],
        index=0 if tailor["Status"] == "idle" else 1
    )

    contact = st.text_input("Kontak", value=tailor["Kontak"])

    col1, col2 = st.columns(2)

    with col1:
        update = st.form_submit_button("💾 Update")

    with col2:
        delete = st.form_submit_button("🗑️ Hapus")

    if update:
        c.execute("""
            UPDATE tailors
            SET name=?, age=?, distance_km=?, speed_clothes_per_day=?,
                specialty=?, status=?, contact=?
            WHERE id=?
        """, (
            name,
            age,
            distance_km,
            speed,
            specialty,
            status,
            contact,
            selected_id
        ))
        conn.commit()
        st.success("Data penjahit diperbarui.")
        st.rerun()

    if delete:
        c.execute("DELETE FROM tailors WHERE id=?", (selected_id,))
        conn.commit()
        st.success("Penjahit dihapus.")
        st.rerun()
