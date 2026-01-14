import streamlit as st
import pandas as pd
from db import get_connection
from datetime import date
import plotly.express as px
import altair as alt

st.set_page_config(page_title="Projects", page_icon="📦", layout="wide")

st.title("📦 Pusat Data Project")
st.markdown("Monitor status produksi, target deadline, dan estimasi keuntungan.")

conn = get_connection()
conn.row_factory = None  # Reset agar pandas bisa membaca dengan benar
c = conn.cursor()

# =========================================
# 1. LOAD DATA UTAMA
# =========================================
query_main = """
SELECT 
    p.id AS project_id,
    p.project_name AS "Nama Project",
    p.customer_name AS "Customer",
    p.clothes_type AS "Jenis",
    p.amount AS "Jumlah (pcs)",
    p.order_date AS "Order Date",
    p.deadline AS "Deadline",
    p.status AS "Status",
    p.notes AS "Catatan",
    p.tailor_fee_per_item AS "Biaya Jahit / Item",
    p.base_fee AS "Harga Dasar",
    p.price_per_item AS "Harga Jual / Item",
    -- Estimasi Biaya & Profit
    (COALESCE(SUM(pc.price), 0) + p.base_fee + (p.amount * p.tailor_fee_per_item)) AS "Total Biaya",
    (p.price_per_item * p.amount) AS "Total Pendapatan",
    ((p.price_per_item * p.amount) - (COALESCE(SUM(pc.price), 0) + p.base_fee + (p.amount * p.tailor_fee_per_item))) AS "Total Keuntungan"
FROM projects p
LEFT JOIN purchases pc ON pc.project_id = p.id
GROUP BY p.id
ORDER BY p.id DESC;
"""
df_projects = pd.read_sql_query(query_main, conn)
df_projects["Biaya Jahit / Item"] = df_projects["Biaya Jahit / Item"].fillna(0.0)
df_projects["Harga Dasar"] = df_projects["Harga Dasar"].fillna(0.0)
df_projects["Total Biaya"] = df_projects["Total Biaya"].fillna(df_projects["Harga Dasar"] + (df_projects["Biaya Jahit / Item"] * df_projects["Jumlah (pcs)"]))

df_projects["Harga Jual / Item"] = df_projects["Harga Jual / Item"].fillna(0.0)
df_projects["Total Pendapatan"] = df_projects["Total Pendapatan"].fillna(df_projects["Harga Jual / Item"] * df_projects["Jumlah (pcs)"])
df_projects["Total Keuntungan"] = df_projects["Total Keuntungan"].fillna(df_projects["Total Pendapatan"] - df_projects["Total Biaya"])

# Konversi Deadline ke datetime agar bisa di-sort
# df_projects["Deadline"] = pd.to_datetime(df_projects["Deadline"])

# =========================================
# 2. TABS LAYOUT
# =========================================
tab1, tab2, tab3 = st.tabs(["📊 Dashboard Analitik", "🛠️ Manajemen Project", "📆 Timeline Project"])

# ------------------------------------------------------------------
# TAB 1: DASHBOARD
# ------------------------------------------------------------------
with tab1:
    if df_projects.empty:
        st.info("Belum ada data project untuk dianalisis.")
    else:
        # --- Metrics Row ---
        col1, col2, col3, col4 = st.columns(4)
        
        total_proj = len(df_projects)
        ongoing = len(df_projects[df_projects["Status"] == "ongoing"])
        done = len(df_projects[df_projects["Status"] == "done"])
        est_revenue = df_projects["Total Pendapatan"].sum()
        est_profit = df_projects["Total Keuntungan"].sum()

        col1.metric("Total Project", f"{total_proj}", f"{ongoing} Ongoing")
        col2.metric("Selesai (Done)", f"{done}")
        col3.metric("Est. Pendapatan", f"Rp {est_revenue:,.0f}")
        col4.metric("Est. Keuntungan", f"Rp {est_profit:,.0f}")

        st.divider()

        # --- Charts Row 1 ---
        c1, c2 = st.columns([2, 1])

        # --- GANTI BAGIAN INI ---
        with c1:
            st.subheader("💰 Perbandingan Biaya vs Pendapatan")
            
            # 1. Siapkan Data (Ambil 10 project terakhir)
            # Kita ambil kolom yang dibutuhkan
            source = df_projects[["Nama Project", "Total Biaya", "Total Pendapatan"]].head(10)
            
            # 2. Ubah Data jadi format Panjang (Melt) agar bisa dikelompokkan
            # Ini teknik wajib kalau mau bikin grouped bar chart
            source_melt = source.melt(
                id_vars=["Nama Project"], 
                value_vars=["Total Biaya", "Total Pendapatan"],
                var_name="Kategori", 
                value_name="Nominal"
            )

            # 3. Buat Chart dengan Altair
            chart = alt.Chart(source_melt).mark_bar().encode(
                # Sumbu X: Nama Project
                x=alt.X('Nama Project:N', axis=alt.Axis(labelAngle=-45, title=None)),
                
                # Sumbu Y: Nominal Uang
                y=alt.Y('Nominal:Q', axis=alt.Axis(title='Rupiah (Rp)')),
                
                # Warna: Merah untuk Biaya, Hijau untuk Keuntungan
                color=alt.Color('Kategori:N', 
                                scale=alt.Scale(
                                    domain=['Total Biaya', 'Total Pendapatan'], 
                                    range=['#FF6C6C', '#4CAF50'] # Merah, Hijau
                                ),
                                legend=alt.Legend(title="Indikator")),
                
                # --- KUNCI AGAR SEBELAHAN (SIDE-BY-SIDE) ---
                xOffset='Kategori:N', 
                
                # Tooltip (Biar muncul angka saat di-hover mouse)
                tooltip=['Nama Project', 'Kategori', alt.Tooltip('Nominal:Q', format=',.0f')]
            ).interactive()

            st.altair_chart(chart, use_container_width=True)

        with c2:
            st.subheader("👕 Distribusi Jenis")
            # Hitung jumlah per jenis
            type_counts = df_projects["Jenis"].value_counts()
            st.bar_chart(type_counts, color="#36A2EB")

# ------------------------------------------------------------------
# TAB 2: MANAJEMEN DATA (CRUD)
# ------------------------------------------------------------------
with tab2:
    # --- ADD NEW PROJECT ---
    with st.expander("➕ Tambah Project Baru", expanded=False):
        with st.form("add_project_form"):
            col_a, col_b = st.columns(2)
            with col_a:
                project_name = st.text_input("Nama Project")
                customer_name = st.text_input("Nama Customer")
                clothes_type = st.selectbox("Jenis Pakaian", ["seragam sekolah", "seragam pramuka", "rok", "kemeja/batik", "custom/gamis/sulit"])
                amount = st.number_input("Jumlah (pcs)", min_value=1, step=1)
            
            with col_b:
                deadline = st.date_input("Deadline", min_value=date.today())
                base_fee = st.number_input("Biaya Dasar (Pola/Listrik)", min_value=0.0, step=1000.0)
                tailor_fee = st.number_input("Upah Jahit / Item", min_value=0.0, step=1000.0)
                price = st.number_input("Harga Jual / Item", min_value=0.0, step=1000.0)
            
            notes = st.text_area("Catatan Tambahan")
            submitted = st.form_submit_button("Simpan Project")

            if submitted:
                if not project_name or not customer_name:
                    st.warning("Nama project dan customer wajib diisi.")
                else:
                    c.execute("""
                        INSERT INTO projects (project_name, customer_name, clothes_type, amount, deadline, order_date, status, notes, tailor_fee_per_item, base_fee, price_per_item)
                        VALUES (?, ?, ?, ?, ?, DATE('now'), 'ongoing', ?, ?, ?, ?)
                    """, (project_name, customer_name, clothes_type, amount, deadline, notes, tailor_fee, base_fee, price))
                    conn.commit()
                    st.success("Project berhasil ditambahkan!")
                    st.rerun()

    st.subheader("📋 Daftar Project")
    st.dataframe(
        df_projects.style.format({
            "Total Biaya": "Rp {:,.0f}",
            "Total Pendapatan": "Rp {:,.0f}",
            "Total Keuntungan": "Rp {:,.0f}",
            "Harga Jual / Item": "Rp {:,.0f}",
            "Biaya Jahit / Item": "Rp {:,.0f}",
            "Harga Dasar": "Rp {:,.0f}"
        }), 
        use_container_width=True
    )

    # --- EDIT / ACTIONS ---
    st.divider()
    st.subheader("✏️ Edit Project")
    if not df_projects.empty:
        proj_list = df_projects["project_id"].tolist()
        sel_id = st.selectbox("Pilih ID Project", proj_list, format_func=lambda x: f"ID {x} - {df_projects[df_projects['project_id']==x]['Nama Project'].values[0]}")
        
        # Ambil data lama
        curr = df_projects[df_projects["project_id"] == sel_id].iloc[0]
        
        with st.form("edit_form"):
            col_a, col_b = st.columns(2)
            with col_a:
                project_name = st.text_input("Nama Project", curr["Nama Project"])
                customer_name = st.text_input("Nama Customer", curr["Customer"])
                clothes_type = st.selectbox("Jenis Pakaian", ["seragam sekolah", "seragam pramuka", "rok", "kemeja/batik", "custom/gamis/sulit"])
                amount = st.number_input("Jumlah (pcs)", min_value=1, step=1, value=curr["Jumlah (pcs)"])
                notes = st.text_area("Catatan Tambahan", value=curr["Catatan"])
            
            with col_b:
                deadline = st.date_input("Deadline", min_value=date.today(), value=curr["Deadline"])
                base_fee = st.number_input("Biaya Dasar (Pola/Listrik)", min_value=0.0, step=1000.0, value=curr["Harga Dasar"])
                tailor_fee = st.number_input("Upah Jahit / Item", min_value=0.0, step=1000.0, value=curr["Biaya Jahit / Item"])
                price = st.number_input("Harga Jual / Item", min_value=0.0, step=1000.0, value=curr["Harga Jual / Item"])
                n_status = st.selectbox("Status", ["ongoing", "done"], index=0 if curr["Status"]=="ongoing" else 1)
            
            btn_update = st.form_submit_button("Update Data")
            
            if btn_update:
                c.execute("UPDATE projects SET project_name=?, customer_name=?, deadline=?, status=?, clothes_type=?, base_fee=?, tailor_fee_per_item=?, price_per_item=?, amount=?, notes=? WHERE id=?", (project_name, customer_name, deadline, n_status, clothes_type, base_fee, tailor_fee, price, amount, notes, sel_id))
                conn.commit()
                st.success("Update berhasil!")
                st.rerun()
                    
    
    st.subheader("🗑️ Hapus / Selesai")
    if not df_projects.empty:
        if st.button("Tandai Selesai (Quick Action)"):
            c.execute("UPDATE projects SET status='done' WHERE id=?", (sel_id,))
            conn.commit()
            st.rerun()
        
        st.warning("Hapus project bersifat permanen.")
        if st.button("Hapus Project"):
            c.execute("DELETE FROM projects WHERE id=?", (sel_id,))
            conn.commit()
            st.error("Project dihapus.")
            st.rerun()

with tab3:
    cal_df = df_projects.copy()

    # Pastikan tanggal bertipe datetime
    cal_df["Deadline"] = pd.to_datetime(cal_df["Deadline"])
    cal_df["Order Date"] = pd.to_datetime(cal_df.get("Order Date", None))

    # Kalau order_date belum ada di SELECT, pakai fallback
    if "Order Date" not in cal_df.columns:
        cal_df["Order Date"] = cal_df["Deadline"] - pd.Timedelta(days=7)

    st.subheader("📅 Timeline Project Produksi")
    st.caption("Visualisasi durasi kerja setiap project dari order sampai deadline")

    if cal_df.empty:
        st.info("Belum ada project.")
    else:
        fig = px.timeline(
            cal_df,
            x_start="Order Date",
            x_end="Deadline",
            y="Nama Project",
            color="Status",
            color_discrete_map={
                "ongoing": "#FFA726",
                "done": "#66BB6A"
            },
            hover_data=[
                "Customer",
                "Jenis",
                "Jumlah (pcs)",
                "Total Keuntungan"
            ]
        )

        fig.update_yaxes(autorange="reversed")
        fig.update_layout(
            height=500 + len(cal_df) * 15,
            xaxis_title="Tanggal",
            yaxis_title="Project",
            legend_title="Status"
        )

        st.plotly_chart(fig, use_container_width=True)