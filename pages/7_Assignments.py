import streamlit as st
import pandas as pd
from db import get_connection

st.title("🧩 Assignment Penjahit")

conn = get_connection()
conn.row_factory = None
c = conn.cursor()

# =========================
# LOAD DATA
# =========================
projects = c.execute("""
    SELECT id, project_name
    FROM projects
    WHERE status='ongoing'
""").fetchall()

tailors = c.execute("""
    SELECT id, name, status
    FROM tailors
""").fetchall()

project_map = {p[0]: p[1] for p in projects}
tailor_map = {t[0]: t[1] for t in tailors}

idle_tailors = [t for t in tailors if t[2] == 'idle']

# =========================
# ADD ASSIGNMENT
# =========================
with st.expander("➕ Assign Penjahit ke Project", expanded=False):
    if not projects or not idle_tailors:
        st.warning("Butuh project ongoing dan penjahit idle.")
    else:
        with st.form("add_assignment_form"):
            project_id = st.selectbox(
                "Project",
                [p[0] for p in projects],
                format_func=lambda x: f"ID {x} - {project_map[x]}"
            )

            tailor_id = st.selectbox(
                "Penjahit (Idle)",
                [t[0] for t in idle_tailors],
                format_func=lambda x: f"ID {x} - {tailor_map[x]}"
            )

            amount_assigned = st.number_input(
                "Jumlah Pakaian",
                min_value=1,
                step=1
            )

            submitted = st.form_submit_button("Assign")

            if submitted:
                # ambil jumlah project
                c.execute("""
                    SELECT amount FROM projects WHERE id=?
                """, (project_id,))
                project_amount = c.fetchone()[0]

                # total assigned saat ini
                c.execute("""
                    SELECT COALESCE(SUM(amount_assigned), 0)
                    FROM assignments
                    WHERE project_id=?
                """, (project_id,))
                current_assigned = c.fetchone()[0]

                is_valid = True
                if current_assigned + amount_assigned > project_amount:
                    st.error(
                        f"Jumlah assignment melebihi order project "
                        f"({current_assigned} + {amount_assigned} > {project_amount})"
                    )
                    is_valid = False
            
                if is_valid == True:
                    c.execute("""
                        INSERT INTO assignments
                        (project_id, tailor_id, amount_assigned, status)
                        VALUES (?, ?, ?, 'assigned')
                    """, (
                        project_id,
                        tailor_id,
                        amount_assigned
                    ))

                    # ubah status penjahit
                    c.execute("""
                        UPDATE tailors SET status='working'
                        WHERE id=?
                    """, (tailor_id,))

                    conn.commit()
                    st.success("Penjahit berhasil di-assign.")
                    st.rerun()

# =========================
# LIST ASSIGNMENTS
# =========================
st.subheader("📋 Daftar Assignment")

df = pd.read_sql_query("""
    SELECT
        a.id,
        a.project_id,
        t.id AS tailor_id,
        p.project_name AS Project,
        t.name AS Penjahit,
        a.amount_assigned AS Jumlah,
        a.status AS Status,
        a.payment_amount AS Upah
    FROM assignments a
    JOIN projects p ON p.id = a.project_id
    JOIN tailors t ON t.id = a.tailor_id
    ORDER BY a.id DESC
""", conn)

if df.empty:
    st.info("Belum ada assignment.")
    st.stop()

st.dataframe(df, use_container_width=True)


# UPDATE ASSIGNMENTS

st.subheader("✏️ Edit Assignment")

selected_id = st.selectbox(
    "Pilih Assignment",
    df["id"],
    format_func=lambda x: f"ID {x} - {df[df['id']==x]['Penjahit'].values[0]}"
)

assignment = df[df["id"] == selected_id].iloc[0]

with st.form("edit_assignment_form"):
    new_amount = st.number_input(
        "Jumlah Pakaian",
        min_value=1,
        value=int(assignment["Jumlah"])
    )

    status = st.selectbox(
        "Status",
        ["assigned", "submitted", "paid"],
        index=["assigned", "submitted", "paid"].index(assignment["Status"])
    )

    payment = st.number_input(
        "Upah",
        min_value=0,
        value=0 if pd.isna(assignment["Upah"]) else int(assignment["Upah"])
    )

    submitted = st.form_submit_button("Update Assignment")

    if submitted:
        is_valid = True

        # VALIDASI TOTAL
        c.execute("""
            SELECT COALESCE(SUM(amount_assigned), 0)
            FROM assignments
            WHERE project_id=? AND id!=?
        """, (assignment["project_id"], selected_id))
        other_assigned = c.fetchone()[0]

        # st.write("DEBUG project_id:", assignment["project_id"])
        c.execute("""
            SELECT amount FROM projects WHERE id=?
        """, (int(assignment["project_id"]),))
        project_amount = c.fetchone()[0]

        if other_assigned + new_amount > project_amount:
            st.error("Jumlah assignment melebihi total project.")
            is_valid = False

        if is_valid:
            c.execute("""
                UPDATE assignments
                SET amount_assigned=?, status=?, payment_amount=?
                WHERE id=?
            """, (
                new_amount,
                status,
                payment,
                selected_id
            ))

            # status tailor logic (optional)
            if status == "paid":
                c.execute("""
                    UPDATE tailors SET status='idle'
                    WHERE id=?
                """, (int(assignment["tailor_id"],)))

            conn.commit()
            st.success("Assignment berhasil diperbarui.")
            st.rerun()
