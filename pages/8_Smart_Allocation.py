import streamlit as st
import pandas as pd
import time
import math
import urllib.parse
import random
from datetime import date
from allocation import hitung_rekomendasi 

st.set_page_config(page_title="Smart Allocation", page_icon="🤖", layout="wide")

st.title("🤖 AI Smart Allocation")
st.markdown("Sistem rekomendasi penjahit berbasis **Deadline Matematis** dan **Kapasitas Real-time**.")

st.divider()

# --- FUNGSI GENERATOR LINK WA ---
def add_whatsapp_link(df, nama_project, pcs_total):
    """
    Menambahkan kolom Link WA ke dataframe.
    """
    # Pastikan kita bekerja pada copy agar tidak error settingwithcopy
    df = df.copy()
    
    def generate_link(row):
        # 1. Dummy Nomor HP (Ganti dengan row['No HP'] jika ada kolom aslinya)
        nomor_hp = f"62812{random.randint(10000000, 99999999)}" 
        
        # 2. Template Pesan
        tugas_pcs = row.get('Tugas (Pcs)', pcs_total) 
        
        pesan = f"""Halo Ibu/Mbak *{row['Nama']}*,
        
Kami dari Admin Koperasi. Anda terpilih untuk project:
👕 *Project:* {nama_project}
📦 *Target:* {tugas_pcs} Pcs
📅 *Deadline:* Segera
        
Mohon konfirmasinya. Terima kasih."""
        
        pesan_encoded = urllib.parse.quote(pesan)
        return f"https://wa.me/{nomor_hp}?text={pesan_encoded}"

    df['Link WA'] = df.apply(generate_link, axis=1)
    return df

# ==========================================
# 0. INISIALISASI SESSION STATE
# ==========================================
if "search_done" not in st.session_state:
    st.session_state.search_done = False
if "df_hasil" not in st.session_state:
    st.session_state.df_hasil = None
if "input_pcs" not in st.session_state:
    st.session_state.input_pcs = 0
if "input_deadline" not in st.session_state:
    st.session_state.input_deadline = date.today()
if "project_name" not in st.session_state:
    st.session_state.project_name = "Project Baru"

# ==========================================
# 1. FORM INPUT
# ==========================================
with st.form("form_cari"):
    st.subheader("📝 Detail Order Baru")
    
    col1, col2 = st.columns(2)
    with col1:
        project_name = st.text_input("Nama Project", "Project Baru")
        jenis = st.selectbox("Jenis Kategori", 
            ["Seragam Sekolah", "Seragam Pramuka", "Rok Seragam", "Kemeja/Batik", "Custom/Gamis/Sulit"])
    with col2:
        pcs = st.number_input("Jumlah Pcs", 1, 1000000, 100) 
        deadline_date = st.date_input("Tanggal Deadline", min_value=date.today())
    
    btn_cari = st.form_submit_button("🔍 Kalkulasi & Cari Solusi")

if btn_cari:
    with st.spinner("Menghitung kapasitas & menyusun tim..."):
        time.sleep(0.5) 
        try:
            df_hasil, pesan = hitung_rekomendasi(jenis, pcs, deadline_date)
            
            st.session_state.search_done = True
            st.session_state.df_hasil = df_hasil
            st.session_state.input_pcs = pcs
            st.session_state.input_deadline = deadline_date
            st.session_state.project_name = project_name
            
        except Exception as e:
            st.error(f"Terjadi kesalahan sistem: {e}")

# ==========================================
# 2. MENAMPILKAN HASIL
# ==========================================
if st.session_state.search_done and st.session_state.df_hasil is not None:
    
    df_hasil = st.session_state.df_hasil
    pcs_val = st.session_state.input_pcs
    deadline_val = st.session_state.input_deadline
    proj_name = st.session_state.project_name
    
    hari_sisa = (deadline_val - date.today()).days
    if hari_sisa <= 0: hari_sisa = 1
    target_speed = pcs_val / hari_sisa
    
    if not df_hasil.empty:
        top = df_hasil.iloc[0]
        is_single_capable = top['Sanggup?']
        
        # --- BAGIAN A: REKOMENDASI UTAMA (SOLO) ---
        # Layout tetap bersih seperti awal (Text & Metrics saja)
        with st.container():
            st.success("✅ Analisis Selesai!")
            st.info(f"""
            **Target Produksi:** {target_speed:.1f} pcs/hari (Selama {hari_sisa} hari)
            """)

            if is_single_capable:
                st.markdown(f"""
                ### 🏆 Rekomendasi Solo: **{top['Nama']}**
                - **Status:** {top['Status'].upper()}
                - **Kapasitas:** {top['Max Speed (Pcs/Hari)']:.1f} pcs/hari
                - **Prediksi:** ✅ **Sanggup Mengerjakan Sendiri**
                """)
            else:
                st.error(f"⚠️ Tidak ada penjahit yang sanggup mengerjakan {pcs_val} pcs sendirian dalam {hari_sisa} hari!")
                st.markdown(f"**Kandidat Terbaik (Solo):** {top['Nama']} (Hanya mampu {top['Max Speed (Pcs/Hari)']:.1f} pcs/hari)")

        # Tabel Top 10 (WA Link disisipkan rapi di sini)
        with st.expander("Lihat Detail Top 10 Kandidat Individu", expanded=not is_single_capable):
            # Tambah link WA ke df_hasil (hanya untuk display)
            df_display = add_whatsapp_link(df_hasil.head(10), proj_name, pcs_val)
            
            st.dataframe(
                df_display,
                column_config={
                    "Link WA": st.column_config.LinkColumn(
                        "Hubungi", display_text="📲 Chat"
                    ),
                    "FINAL_SCORE": st.column_config.NumberColumn("Score", format="%.2f"),
                    "Max Speed (Pcs/Hari)": st.column_config.NumberColumn("Speed", format="%.1f"),
                    "Jarak (Km)": st.column_config.NumberColumn("Jarak", format="%.1f")
                },
                use_container_width=True
            )

        st.divider()

        # --- BAGIAN B: SIMULASI SPLIT ORDER (LAYOUT AWAL YANG RAPI) ---
        if is_single_capable:
            st.subheader("⚡ Opsi Alternatif: Custom Split Order")
            st.caption("Bagi beban kerja ke beberapa orang agar lebih ringan.")
        else:
            st.subheader("🤝 Solusi Wajib: Rekomendasi Tim")
            st.caption("Satu orang tidak sanggup. Gunakan tim di bawah ini.")

        # Layout Split: Input Kiri, Hasil Kanan (Sesuai request awal)
        col_sim1, col_sim2 = st.columns([1, 2])
        
        with col_sim1:
            st.markdown("##### ⚙️ Atur Beban Kerja")
            max_beban_user = st.number_input(
                "Maksimal Pcs per Orang:", 
                min_value=1, max_value=1000000,
                value=int(pcs_val) if not is_single_capable else int(pcs_val/2),
                step=10,
                help="Sistem akan memastikan beban per orang tidak melebihi angka ini."
            )
        
        with col_sim2:
            # --- LOGIKA HITUNG TIM (STRICT CAPPING) ---
            safe_max_beban = max(1, max_beban_user)
            jumlah_org_butuh = math.ceil(pcs_val / safe_max_beban)
            
            candidates = df_hasil[df_hasil['Status'] == 'idle'].copy()
            team = candidates.head(jumlah_org_butuh)
            current_speed = team['Max Speed (Pcs/Hari)'].sum()
            
            while current_speed < target_speed and len(team) < len(candidates):
                jumlah_org_butuh += 1
                team = candidates.head(jumlah_org_butuh)
                current_speed = team['Max Speed (Pcs/Hari)'].sum()

            final_team = []
            for idx, row in team.iterrows():
                final_team.append(row)

            if final_team:
                # --- LOGIKA DISTRIBUSI TUGAS (WATER FILLING) ---
                total_speed_team = sum([p['Max Speed (Pcs/Hari)'] for p in final_team])
                temp_allocations = []
                for p in final_team:
                    ideal_share = (p['Max Speed (Pcs/Hari)'] / total_speed_team) * pcs_val
                    capped_share = min(ideal_share, safe_max_beban) 
                    temp_allocations.append(capped_share)
                
                allocations = [int(x) for x in temp_allocations]
                
                remaining_pcs = pcs_val - sum(allocations)
                sorted_indices = sorted(range(len(final_team)), key=lambda k: final_team[k]['Max Speed (Pcs/Hari)'], reverse=True)
                
                while remaining_pcs > 0:
                    distributed = False
                    for idx in sorted_indices:
                        if remaining_pcs <= 0: break
                        if allocations[idx] < safe_max_beban:
                            allocations[idx] += 1
                            remaining_pcs -= 1
                            distributed = True
                    if not distributed: break

                # PREPARE DATA UNTUK TABEL AKHIR
                dist_data = []
                for i, member in enumerate(final_team):
                    row_data = member.to_dict()
                    row_data['Tugas (Pcs)'] = allocations[i]
                    dist_data.append(row_data)
                
                df_team_final = pd.DataFrame(dist_data)
                
                # Tambah Link WA ke Tim
                df_team_final = add_whatsapp_link(df_team_final, proj_name, pcs_val)
                
                # --- DISPLAY METRICS & TABLE ---
                # Metrics
                df_team_ori = pd.DataFrame(final_team)
                total_cap = df_team_ori['Max Speed (Pcs/Hari)'].sum()
                est_days = pcs_val / total_cap if total_cap > 0 else 999

                st.info(f"Hasil Simulasi: Membatasi max **{safe_max_beban} pcs/orang** ➝ Butuh **{len(final_team)} Penjahit**.")

                m1, m2, m3 = st.columns(3)
                m1.metric("Kapasitas Tim", f"{total_cap:.1f} pcs/hari", f"Target: {target_speed:.1f}")
                
                if est_days <= hari_sisa:
                    m2.metric("Estimasi Selesai", f"{est_days:.1f} Hari", f"✅ Aman (< {hari_sisa} hari)")
                else:
                    m2.metric("Estimasi Selesai", f"{est_days:.1f} Hari", f"⚠️ Telat", delta_color="inverse")
                    st.warning("Kapasitas masih kurang. Tambah orang atau undur deadline.")

                # Table Tim
                st.markdown("##### ⚖️ Saran Pembagian Tugas & Kontak:")
                st.dataframe(
                    df_team_final[['Nama', 'Status', 'Max Speed (Pcs/Hari)', 'Tugas (Pcs)', 'Link WA']],
                    column_config={
                        "Link WA": st.column_config.LinkColumn(
                            "Hubungi", display_text="📲 Chat"
                        ),
                        "Max Speed (Pcs/Hari)": st.column_config.NumberColumn("Speed", format="%.1f")
                    },
                    use_container_width=True
                )

            else:
                st.error("Tidak cukup penjahit tersedia.")

    else:
        st.warning("Data tidak ditemukan.")

if st.session_state.search_done:
    if st.button("🔄 Reset / Cari Ulang"):
        st.session_state.search_done = False
        st.session_state.df_hasil = None
        st.rerun()