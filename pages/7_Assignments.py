import streamlit as st
import pandas as pd
from db import get_connection

st.set_page_config(page_title="Assignments", page_icon="📋", layout="wide")
st.title("📋 Distribusi Tugas & Monitoring")
st.markdown("Pantau beban kerja penjahit dan kelola pembagian tugas produksi.")

conn = get_connection()
conn.row_factory = None
c = conn.cursor()

# =========================
# LOAD DATA (COMMON)
# =========================
# Data Project Ongoing (untuk dropdown & validasi)
projects = c.execute("SELECT id, project_name, amount FROM projects WHERE status='ongoing'").fetchall()
proj_map = {p[0]: f"{p[1]} (Target: {p[2]} pcs)" for p in projects}
proj_amount_map = {p[0]: p[2] for p in projects}

# Data Tailor (untuk dropdown)
tailors = c.execute("SELECT id, name, status FROM tailors").fetchall()
idle_tailors = [t for t in tailors if t[2] == 'idle']

# Data Assignment Lengkap (untuk Tabel Utama)
query_main = """
SELECT 
    a.id,
    p.project_name AS "Project",
    t.name AS "Penjahit",
    a.amount_assigned AS "Jml Pcs",
    a.status AS "Status",
    (p.tailor_fee_per_item * a.amount_assigned) AS "Upah",
    p.id as project_id,
    t.id as tailor_id
FROM assignments a
JOIN projects p ON p.id = a.project_id
JOIN tailors t ON t.id = a.tailor_id
ORDER BY a.id DESC
"""
df_assign = pd.read_sql_query(query_main, conn)

# =========================
# TABS LAYOUT
# =========================
tab1, tab2 = st.tabs(["📊 Monitor Beban Kerja", "📝 Kelola Penugasan"])

# ------------------------------------------------------------------
# TAB 1: DASHBOARD ANALITIK
# ------------------------------------------------------------------
with tab1:
    # --- Metrics Row ---
    col1, col2, col3 = st.columns(3)
    
    # Hitung Statistik
    active_items = df_assign[df_assign["Status"] == "assigned"]["Jml Pcs"].sum()
    active_workers = len(df_assign[df_assign["Status"] == "assigned"]["Penjahit"].unique())
    ongoing_count = len(projects)
    
    col1.metric("👔 Sedang Dijahit", f"{active_items} Pcs")
    col2.metric("🧵 Penjahit Aktif", f"{active_workers} Orang")
    col3.metric("📦 Project Berjalan", f"{ongoing_count} Project")
    
    st.divider()
    
    # --- Charts Row ---
    c1, c2 = st.columns([2, 1])
    
    with c1:
        st.subheader("🏆 Top Penjahit Tersibuk (Sedang Bekerja)")
        # Filter hanya yang status assigned
        df_active = df_assign[df_assign["Status"] == "assigned"]
        if not df_active.empty:
            # Group by Penjahit dan Sum Jumlah Pcs
            busy_tailors = df_active.groupby("Penjahit")["Jml Pcs"].sum().sort_values(ascending=False).head(10)
            st.bar_chart(busy_tailors, color="#FF6384", horizontal=True)
        else:
            st.info("Saat ini tidak ada penjahit yang sedang memegang pekerjaan (active).")
            
    with c2:
        st.subheader("📊 Progress Project")
        # Visualisasi: Berapa persen project yang sudah dibagikan ke penjahit?
        if projects:
            proj_progress = []
            for pid, pname, ptotal in projects:
                # Hitung total assigned untuk project ini
                assigned = df_assign[df_assign["project_id"] == pid]["Jml Pcs"].sum()
                # Hitung sisa
                remaining = max(0, ptotal - assigned)
                proj_progress.append({"Project": pname, "Sudah Dibagi": assigned, "Belum Dibagi": remaining})
            
            df_prog = pd.DataFrame(proj_progress).set_index("Project")
            # Stacked Bar Chart (Hijau = Assigned, Abu = Sisa)
            st.bar_chart(df_prog, color=["#4CAF50", "#E0E0E0"], stack=True)
        else:
            st.info("Tidak ada project ongoing.")

# ------------------------------------------------------------------
# TAB 2: MANAJEMEN PENUGASAN
# ------------------------------------------------------------------
with tab2:
    col_form, col_list = st.columns([1, 2])
    
    # --- 1. FORM ASSIGNMENT ---
    with col_form:
        st.subheader("➕ Beri Tugas Baru")
        
        # Cek Project DULU sebelum membuat form
        if not projects:
            st.warning("⚠️ Tidak ada project ongoing.")
            st.info("Silakan buat project baru dulu di menu 'Projects'.")
        else:
            # Jika project ada, baru buat form
            with st.form("assign_form"):
                sel_proj_id = st.selectbox("Pilih Project", list(proj_map.keys()), format_func=lambda x: proj_map[x])
                
                # Filter penjahit idle
                idle_opts = {t[0]: t[1] for t in idle_tailors}
                
                if idle_opts:
                    sel_tailor_id = st.selectbox("Pilih Penjahit (Idle)", list(idle_opts.keys()), format_func=lambda x: idle_opts[x])
                else:
                    st.warning("Semua penjahit sedang sibuk!")
                    sel_tailor_id = None
                
                amount = st.number_input("Jumlah Pcs", min_value=1, step=1)
                
                # Tombol submit aman ada di sini
                submitted = st.form_submit_button("Assign Tugas")
                
                if submitted:
                    if not sel_tailor_id:
                        st.error("Pilih penjahit terlebih dahulu (atau semua sedang sibuk).")
                    else:
                        # Validasi Kuota Project
                        curr_assigned = c.execute("SELECT COALESCE(SUM(amount_assigned), 0) FROM assignments WHERE project_id=?", (sel_proj_id,)).fetchone()[0]
                        proj_total = proj_amount_map[sel_proj_id]
                        
                        if curr_assigned + amount > proj_total:
                            st.error(f"❌ Over capacity! Sisa kuota project ini hanya: {proj_total - curr_assigned} pcs.")
                        else:
                            # 1. Insert Assignment
                            c.execute("INSERT INTO assignments (project_id, tailor_id, amount_assigned, status) VALUES (?, ?, ?, 'assigned')", (sel_proj_id, sel_tailor_id, amount))
                            
                            # 2. Update Status Penjahit -> Working
                            c.execute("UPDATE tailors SET status='working' WHERE id=?", (sel_tailor_id,))

                            # c.execute("""
                            # UPDATE assignments SET a.payment_amount = (p.tailor_fee_per_item * ?)
                            # FROM assignments a
                            # JOIN projects p ON a.project_id = p.id
                            # WHERE a.id = MAX(SELECT id FROM assignments)
                            # """)
                            
                            conn.commit()
                            st.success(f"Tugas berhasil diberikan kepada penjahit ID {sel_tailor_id}!")
                            st.rerun()

    # --- 2. LIST & EDIT ---
    with col_list:
        st.subheader("📋 Daftar Riwayat Penugasan")
        
        # Tampilkan tabel tanpa kolom ID teknis agar bersih
        display_df = df_assign.drop(columns=["project_id", "tailor_id"])
        
        # [PERBAIKAN UTAMA] Isi nilai None dengan 0 agar tidak error saat format currency
        display_df["Upah"] = display_df["Upah"].fillna(0)
        
        st.dataframe(
            display_df.style.format({"Upah": "Rp {:,.0f}"}), 
            use_container_width=True,
            height=400
        )
        
    st.divider()
    st.subheader("✏️ Update Status / Edit")
    
    col_edit, col_delete = st.columns([1, 2])

    with col_edit:
        if not df_assign.empty:
            with st.expander("Klik untuk update status penugasan", expanded=False):
                assign_ids = df_assign["id"].tolist()
                sel_assign_id = st.selectbox("Pilih ID Assignment", assign_ids)
                
                # Load data saat ini
                curr_row = df_assign[df_assign["id"] == sel_assign_id].iloc[0]
                st.info(f"Mengedit: **{curr_row['Project']}** - {curr_row['Penjahit']} ({curr_row['Jml Pcs']} pcs)")
                
                with st.form("edit_assign"):
                    col_s, col_p = st.columns(2)
                    with col_s:
                        status_opts = ["assigned", "submitted", "paid"]
                        curr_idx = status_opts.index(curr_row["Status"]) if curr_row["Status"] in status_opts else 0
                        new_status = st.selectbox("Status", status_opts, index=curr_idx)
                        
                    with col_p:
                        # Handle jika Upah None/NaN di form juga
                        new_amount = st.number_input("Jumlah", value=curr_row["Jml Pcs"], step=1)
                        val_upah = 0.0 if pd.isna(curr_row["Upah"]) else float(curr_row["Upah"])
                        # new_pay = st.number_input("Upah Cair (Rp)", value=val_upah, step=5000.0)
                        
                        # tailor_fee = c.execute("SELECT tailor_fee_per_item FROM projects WHERE id=?", (sel_proj_id,))
                    
                    if st.form_submit_button("Simpan Perubahan"):
                        # Update Assignment
                        c.execute("UPDATE assignments SET amount_assigned=?, status=? WHERE id=?", (new_amount, new_status, sel_assign_id))
                        
                        # LOGIC PENTING: Jika status berubah jadi 'paid', bebaskan penjahit (idle)
                        if new_status == 'paid' and curr_row["Status"] != 'paid':
                            c.execute("UPDATE tailors SET status='idle' WHERE id=?", (int(curr_row["tailor_id"]),))
                            st.toast("Penjahit kini statusnya IDLE (Siap kerja lagi).")
                            
                        conn.commit()
                        st.success("Data berhasil diupdate!")
                        st.rerun()
        
    with col_delete:
        if not df_assign.empty:
            st.warning("Hapus assignment bersifat permanen")
        
        if st.button("Hapus Assignment"):
            c.execute("DELETE FROM assignments WHERE id=?", (sel_assign_id,))
            conn.commit()
            st.error("Project dihapus.")
            st.rerun()