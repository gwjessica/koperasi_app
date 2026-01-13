import streamlit as st
import pandas as pd
from db import get_connection
from datetime import date
import io

st.title("📦 Projects")

conn = get_connection()
conn.row_factory = None  # supaya pandas yang handle
c = conn.cursor()

# =========================
# ADD NEW PROJECT
# =========================
with st.expander("➕ Tambah Project Baru", expanded=False):
    with st.form("add_project_form"):
        project_name = st.text_input("Nama Project")
        customer_name = st.text_input("Nama Customer")

        clothes_type = st.selectbox(
            "Jenis Pakaian",
            ["uniform", "custom"]
        )

        amount = st.number_input(
            "Jumlah Pakaian",
            min_value=1,
            step=1
        )

        deadline = st.date_input(
            "Deadline",
            min_value=date.today()
        )

        base_fee = st.number_input(
            "Biaya dasar (pemotongan pola dll)",
            min_value=0,
            step=1
        )

        tailor_fee = st.number_input(
            "Biaya jahit per item",
            min_value=0,
            step=1
        )

        price = st.number_input(
            "Harga jual per item",
            min_value=0,
            step=1
        )

        notes = st.text_area("Catatan")

        submitted = st.form_submit_button("Simpan Project")

        if submitted:
            if not project_name or not customer_name:
                st.warning("Nama project dan customer wajib diisi.")
            else:
                c.execute("""
                    INSERT INTO projects
                    (project_name, customer_name, clothes_type, amount, deadline, order_date, status, notes, tailor_fee_per_item, base_fee, price_per_item)
                    VALUES (?, ?, ?, ?, ?, DATE('now'), 'ongoing', ?, ?, ?, ?)
                """, (
                    project_name,
                    customer_name,
                    clothes_type,
                    amount,
                    deadline,
                    notes,
                    tailor_fee,
                    base_fee,
                    price
                ))
                conn.commit()
                st.success("Project berhasil ditambahkan.")
                st.rerun()

# =========================
# LIST PROJECTS (TABLE)
# =========================
st.subheader("📋 Daftar Project")

query = """
SELECT 
    p.id AS project_id,
    p.project_name AS "Nama Project",
    p.customer_name AS "Customer",
    p.clothes_type AS "Jenis",
    p.amount AS "Jumlah (pcs)",
    p.deadline AS "Deadline",
    p.status AS "Status",
    p.notes AS "Catatan",

    p.tailor_fee_per_item AS "Biaya Jahit / item",

    -- harga dasar = bahan + base fee
    (COALESCE(SUM(pc.price), 0) + p.base_fee) AS "Harga Dasar",

    -- total biaya produksi
    (COALESCE(SUM(pc.price), 0) 
        + p.base_fee 
        + (p.amount * p.tailor_fee_per_item)
    ) AS "Total Harga",

    -- harga jual per item
    (p.price_per_item) AS "Harga Jual / item",

    -- total pendapatan
    (p.price_per_item * p.amount) AS "Total Pendapatan",

    -- total keuntungan
    (
        (p.price_per_item * p.amount)
        -
        (
            COALESCE(SUM(pc.price), 0)
            + p.base_fee
            + (p.amount * p.tailor_fee_per_item)
        )
    ) AS "Total Keuntungan"

FROM projects p
LEFT JOIN purchases pc ON pc.project_id = p.id
GROUP BY p.id
ORDER BY p.id DESC;

"""

df_projects = pd.read_sql_query(query, conn)

if df_projects.empty:
    st.info("Belum ada project.")
else:
    st.dataframe(df_projects, use_container_width=True)

#     # =========================
#     # EXPORT
#     # =========================
#     col1, col2 = st.columns(2)

#     with col1:
#         st.download_button(
#             "⬇️ Download CSV",
#             data=df_projects.to_csv(index=False),
#             file_name="projects.csv",
#             mime="text/csv"
#         )

#     with col2:
#         buffer = io.BytesIO()
#         with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
#             df_projects.to_excel(writer, index=False, sheet_name="Projects")

#         st.download_button(
#             "⬇️ Download Excel",
#             data=buffer.getvalue(),
#             file_name="projects.xlsx",
#             mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
#         )


# EDIT PROJECT

st.subheader("✏️ Edit Project")

project_ids = df_projects["project_id"].tolist()

selected_project_id = st.selectbox(
    "Pilih Project",
    project_ids,
    format_func=lambda x: f"ID {x} - {df_projects[df_projects['project_id']==x]['Nama Project'].values[0]}",
    key="edit_project_select"
)

c.execute("""
    SELECT 
        project_name,
        customer_name,
        amount,
        deadline,
        price_per_item,
        base_fee,
        tailor_fee_per_item,
        notes
    FROM projects
    WHERE id=?
""", (int(selected_project_id),))

row = c.fetchone()

if not row:
    st.error("Project tidak ditemukan.")
    st.stop()

project = {
    "Nama Project": row[0],
    "Customer": row[1],
    "Jumlah (pcs)": row[2],
    "Deadline": row[3],
    "Harga Jual / item": row[4],
    "Base Fee": row[5],
    "Biaya Jahit / item": row[6],
    "Catatan": row[7],
}


c.execute("SELECT base_fee FROM projects WHERE id=?", (int(selected_project_id),))
base_fee_value = c.fetchone()
base_fee_value = base_fee_value[0] if base_fee_value else 0

with st.expander("Edit Project Form", expanded=False):
    with st.form("edit_project_form"):
        project_name = st.text_input("Nama Project", project["Nama Project"])
        customer_name = st.text_input("Customer", project["Customer"])

        clothes_type = st.selectbox(
                "Jenis Pakaian",
                ["uniform", "custom"]
            )
        
        amount = st.number_input("Jumlah (pcs)", min_value=1, value=int(project["Jumlah (pcs)"]))
        deadline = st.date_input("Deadline", pd.to_datetime(project["Deadline"]))

        base_fee = st.number_input(
            "Base Fee",
            min_value=0.0,
            value=float(base_fee_value or 0)
        )

        tailor_fee = st.number_input(
            "Biaya Jahit / Item",
            min_value=0.0,
            value=float(project["Biaya Jahit / item"] or 0)
        )

        price_per_item = st.number_input(
            "Harga Jual / Item",
            min_value=0.0,
            value=float(project["Harga Jual / item"] or 0)
        )

        notes = st.text_area("Catatan", project["Catatan"] or "")

        submit = st.form_submit_button("💾 Update Project")

        if submit:
            if not project_name or not customer_name:
                st.warning("Nama project dan customer wajib diisi.")
            else:
                c.execute("""
UPDATE projects
SET project_name = ?,
    customer_name = ?,
    clothes_type = ?,
    amount = ?,
    deadline = ?,
    order_date = DATE('now'),
    status = 'ongoing',
    notes = ?,
    tailor_fee_per_item = ?,
    base_fee = ?,
    price_per_item = ?
WHERE id = ?
""", (
        project_name,
        customer_name,
        clothes_type,
        amount,
        deadline,
        notes,
        tailor_fee,
        base_fee,
        price_per_item,
        selected_project_id
    ))
                conn.commit()
                st.success("Project berhasil diedit.")
                st.rerun()




# =========================
# PROJECT ACTIONS
# =========================
st.subheader("⚙️ Aksi Project")

ongoing_projects = df_projects[df_projects["Status"] == "ongoing"]

if ongoing_projects.empty:
    st.info("Tidak ada project ongoing.")
else:
    selected_project = st.selectbox(
        "Pilih project",
        ongoing_projects["project_id"].tolist(),
        format_func=lambda x: f"ID {x} - {df_projects[df_projects['project_id']==x]['Nama Project'].values[0]}"
    )

    if st.button("✔️ Tandai Project Selesai"):
        c.execute("""
            UPDATE projects SET status='done'
            WHERE id=?
        """, (selected_project,))
        conn.commit()
        st.success("Project ditandai selesai.")
        st.rerun()


# DELETE PROJECT

st.subheader("🗑️ Hapus Project")
ongoing_projects = df_projects[df_projects["Status"] == "ongoing"]

if ongoing_projects.empty:
    st.info("Tidak ada project ongoing.")
else:
    selected_project = st.selectbox(
        "Pilih project",
        ongoing_projects["project_id"].tolist(),
        format_func=lambda x: f"ID {x} - {df_projects[df_projects['project_id']==x]['Nama Project'].values[0]}",
        key="select_project_delete"
    )

    if st.button("⚠️ Hapus Project"):
        # cek material
        c.execute(
            "SELECT COUNT(*) FROM purchases WHERE project_id = ?",
            (selected_project_id,)
        )
        material_count = c.fetchone()[0]

        # cek penjahit
        c.execute(
            "SELECT COUNT(*) FROM assignments WHERE project_id = ?",
            (selected_project_id,)
        )
        tailor_count = c.fetchone()[0]

        if material_count > 0 or tailor_count > 0:
            st.error(
                "❌ Project tidak bisa dihapus karena masih terhubung dengan:\n"
                f"- {material_count} data material\n"
                f"- {tailor_count} data penjahit"
            )
        else:
            c.execute("DELETE FROM projects WHERE id = ?", (selected_project_id,))
            conn.commit()
            st.success("Project berhasil dihapus.")
            st.rerun()