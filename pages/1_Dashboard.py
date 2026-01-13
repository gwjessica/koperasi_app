import streamlit as st
from db import get_connection

st.title("📊 Dashboard")

conn = get_connection()
c = conn.cursor()

# ===== METRICS =====
total_projects = c.execute(
    "SELECT COUNT(*) FROM projects"
).fetchone()[0]

ongoing_projects = c.execute(
    "SELECT COUNT(*) FROM projects WHERE status='ongoing'"
).fetchone()[0]

done_projects = c.execute(
    "SELECT COUNT(*) FROM projects WHERE status='done'"
).fetchone()[0]

total_inventory = c.execute(
    """
    SELECT COALESCE(SUM(
        CASE WHEN direction='IN' THEN amount ELSE -amount END
    ), 0)
    FROM inventory
    """
).fetchone()[0]

col1, col2, col3, col4 = st.columns(4)

col1.metric("Total Projects", total_projects)
col2.metric("Ongoing", ongoing_projects)
col3.metric("Done", done_projects)
col4.metric("Total Fabric Stock", f"{total_inventory:.2f}")

st.divider()

# ===== RECENT PROJECTS =====
st.subheader("📌 Project Terbaru")

projects = c.execute("""
    SELECT project_name, customer_name, amount, status, deadline
    FROM projects
    ORDER BY id DESC
    LIMIT 5
""").fetchall()

if projects:
    for p in projects:
        st.write(
            f"**{p['project_name']}** | {p['customer_name']} "
            f"| {p['amount']} pcs | {p['status']} | Deadline: {p['deadline']}"
        )
else:
    st.info("Belum ada project.")
