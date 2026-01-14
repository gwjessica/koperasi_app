import streamlit as st
import pandas as pd
import altair as alt
import os
from db import get_connection

# Konfigurasi Halaman
st.set_page_config(
    page_title="Manajemen Penjahit", 
    page_icon="🧵",
    layout="wide"
)

# --- CSS CUSTOM UNTUK MEMPERCANTIK ---
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        border-left: 5px solid #4CAF50;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }
    .metric-title {
        color: #616161;
        font-size: 0.9rem;
        font-weight: bold;
    }
    .metric-value {
        color: #212121;
        font-size: 1.8rem;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

st.title("🧵 Pusat Data Penjahit")
st.markdown("Monitor kinerja, sebaran lokasi, dan status operasional mitra penjahit.")

# Load Data dari Database
conn = get_connection()
conn.row_factory = None # Biar bisa dibaca pandas
c = conn.cursor()

# Query Data Lengkap
df = pd.read_sql_query("""
    SELECT 
        id, 
        name, 
        age, 
        distance_km, 
        speed_clothes_per_day AS speed, 
        specialty, 
        status, 
        contact 
    FROM tailors
""", conn)

# --- TAB MENU ---
tab1, tab2, tab3 = st.tabs(["📊 Dashboard Analitik", "🛠️ Manajemen Data", "📋 History Assignment"])

# ==========================================
# TAB 1: DASHBOARD & VISUALISASI
# ==========================================
with tab1:
    if df.empty:
        st.info("Belum ada data untuk ditampilkan.")
    else:
        # --- SECTION 1: KEY METRICS ---
        st.subheader("📌 Ringkasan Kinerja")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">Total Mitra</div>
                <div class="metric-value">{len(df)}</div>
            </div>
            """, unsafe_allow_html=True)
            
        with col2:
            avg_speed = df['speed'].mean()
            st.markdown(f"""
            <div class="metric-card" style="border-left-color: #2196F3;">
                <div class="metric-title">Rata-rata Speed</div>
                <div class="metric-value">{avg_speed:.1f} <span style="font-size:1rem">pcs/hari</span></div>
            </div>
            """, unsafe_allow_html=True)
            
        with col3:
            working = len(df[df['status'] == 'working'])
            st.markdown(f"""
            <div class="metric-card" style="border-left-color: #FF5252;">
                <div class="metric-title">Sedang Sibuk</div>
                <div class="metric-value">{working} <span style="font-size:1rem">Org</span></div>
            </div>
            """, unsafe_allow_html=True)

        with col4:
            idle = len(df[df['status'] == 'idle'])
            st.markdown(f"""
            <div class="metric-card" style="border-left-color: #FFC107;">
                <div class="metric-title">Siap Kerja (Idle)</div>
                <div class="metric-value">{idle} <span style="font-size:1rem">Org</span></div>
            </div>
            """, unsafe_allow_html=True)
        
        st.divider()

        # --- SECTION 2: CHARTS ---
        c1, c2 = st.columns([2, 1])

        with c1:
            st.markdown("##### 🚀 Top 10 Penjahit Tercepat")
            # Bar Chart Horizontal
            chart_speed = alt.Chart(df.nlargest(10, 'speed')).mark_bar().encode(
                x=alt.X('speed', title='Kecepatan (Pcs/Hari)'),
                y=alt.Y('name', sort='-x', title=None),
                color=alt.Color('specialty', legend=alt.Legend(title="Spesialis")),
                tooltip=['name', 'speed', 'specialty']
            ).properties(height=350)
            st.altair_chart(chart_speed, use_container_width=True)

        with c2:
            st.markdown("##### 🎭 Distribusi Spesialisasi")
            # Donut Chart
            pie = alt.Chart(df).mark_arc(innerRadius=50).encode(
                theta=alt.Theta("count()"),
                color=alt.Color("specialty"),
                tooltip=["specialty", "count()"]
            ).properties(height=350)
            st.altair_chart(pie, use_container_width=True)

        st.divider()
        
        # --- SECTION 3: SCATTER PLOT ---
        st.markdown("##### 📍 Analisis: Jarak vs Usia")
        st.caption("Melihat apakah usia mempengaruhi seberapa jauh lokasi tempat tinggal mitra.")
        
        scatter = alt.Chart(df).mark_circle(size=100).encode(
            x=alt.X('age', title='Usia (Tahun)', scale=alt.Scale(domain=[15, 80])),
            y=alt.Y('distance_km', title='Jarak (Km)'),
            color=alt.Color('status', scale=alt.Scale(domain=['idle', 'working'], range=['green', 'red'])),
            tooltip=['name', 'age', 'distance_km', 'status']
        ).properties(height=400).interactive()
        
        st.altair_chart(scatter, use_container_width=True)


# ==========================================
# TAB 2: MANAJEMEN DATA (CRUD)
# ==========================================
with tab2:
    st.subheader("📋 Daftar & Kelola Data")
    
    col_kiri, col_kanan = st.columns([3, 1])
    
    # --- FITUR PENCARIAN ---
    with col_kiri:
        search_query = st.text_input("🔍 Cari Penjahit (Nama)", placeholder="Ketik nama penjahit...")
    
    if search_query:
        df_display = df[df['name'].str.contains(search_query, case=False)]
    else:
        df_display = df

    # --- TABEL DATA ---
    st.dataframe(
        df_display, 
        column_config={
            "status": st.column_config.SelectboxColumn(
                "Status",
                help="Status Ketersediaan",
                width="medium",
                options=["idle", "working"],
            ),
            "speed": st.column_config.ProgressColumn(
                "Speed (Pcs/Hari)",
                format="%.1f",
                min_value=0,
                max_value=30, # Asumsi max speed
            ),
            "distance_km": st.column_config.NumberColumn(
                "Jarak (Km)",
                format="%.1f km"
            )
        },
        use_container_width=True,
        hide_index=True
    )

    st.divider()
    
    # --- FORM CRUD (TAMBAH/EDIT) ---
    c1, c2 = st.columns(2)
    
    with c1:
        st.info("➕ **Tambah Penjahit Baru**")
        with st.form("add_form"):
            new_name = st.text_input("Nama")
            col_a, col_b = st.columns(2)
            with col_a:
                new_age = st.number_input("Usia", 17, 80, 30)
                new_dist = st.number_input("Jarak (Km)", 0.0, 100.0, 5.0)
            with col_b:
                new_speed = st.number_input("Speed (Pcs/Hari)", 1.0, 50.0, 5.0)
                new_spec = st.selectbox("Spesialis", ["uniform", "custom"])
            
            new_contact = st.text_input("Kontak")
            if st.form_submit_button("Simpan Data Baru"):
                c.execute("""
                    INSERT INTO tailors (name, age, distance_km, speed_clothes_per_day, specialty, status, contact)
                    VALUES (?, ?, ?, ?, ?, 'idle', ?)
                """, (new_name, new_age, new_dist, new_speed, new_spec, new_contact))
                conn.commit()
                st.success("Berhasil ditambahkan!")
                st.rerun()

    with c2:
        st.warning("✏️ **Edit / Hapus Data**")
        
        # Dropdown pilih penjahit
        all_tailors = df[['id', 'name']].values.tolist()
        selected_id_edit = st.selectbox("Pilih Nama utk Diedit", options=[x[0] for x in all_tailors], format_func=lambda x: next((y[1] for y in all_tailors if y[0] == x), "Unknown"))
        
        if selected_id_edit:
            # Ambil data current
            curr = df[df['id'] == selected_id_edit].iloc[0]
            
            with st.form("edit_form"):
                e_name = st.text_input("Nama", value=curr['name'])
                
                ec1, ec2 = st.columns(2)
                with ec1:
                    e_speed = st.number_input("Speed", value=float(curr['speed']))
                    e_status = st.selectbox("Status", ["idle", "working"], index=0 if curr['status']=='idle' else 1)
                with ec2:
                    e_spec = st.selectbox("Spesialis", ["uniform", "custom"], index=0 if curr['specialty']=='uniform' else 1)
                    e_dist = st.number_input("Jarak", value=float(curr['distance_km']))
                
                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    if st.form_submit_button("Update Data"):
                        c.execute("""
                            UPDATE tailors SET name=?, speed_clothes_per_day=?, status=?, specialty=?, distance_km=? 
                            WHERE id=?
                        """, (e_name, e_speed, e_status, e_spec, e_dist, selected_id_edit))
                        conn.commit()
                        st.success("Data Updated!")
                        st.rerun()
                with btn_col2:
                    if st.form_submit_button("Hapus Data", type="primary"):
                        c.execute("DELETE FROM tailors WHERE id=?", (selected_id_edit,))
                        conn.commit()
                        st.error("Data Deleted!")
                        st.rerun()

with tab3:
    st.subheader("📜 Riwayat Assignment Penjahit")

    # Pilih penjahit
    tailor_map = dict(zip(df['name'], df['id']))
    selected_tailor = st.selectbox(
        "Pilih Penjahit",
        options=tailor_map.keys()
    )

    tailor_id = tailor_map[selected_tailor]

    # Ambil assignment berdasarkan tailor
    hist_df = pd.read_sql_query("""
        SELECT 
            a.id AS "Assignment ID",
            p.project_name AS "Project Name",
            a.amount_assigned AS "Amount",
            a.status AS "Status",
            a.payment_amount AS "Payment Amount"
        FROM assignments a
        JOIN tailors t on a.tailor_id = t.id
        JOIN projects p on p.id = a.project_id

        WHERE t.id = ?
        ORDER BY a.id DESC
    """, conn, params=(tailor_id,))

    if hist_df.empty:
        st.info("Belum ada assignment untuk penjahit ini.")
    else:
        st.dataframe(
            hist_df,
            column_config={
                "status": st.column_config.SelectboxColumn(
                    "Status",
                    options=["ongoing", "finished", "paid"]
                ),
                "total_price": st.column_config.NumberColumn(
                    "Total",
                    format="Rp %.0f"
                )
            },
            use_container_width=True,
            hide_index=True
        )
