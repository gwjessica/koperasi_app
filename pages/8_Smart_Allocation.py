import streamlit as st
import pandas as pd
import time
import math
from datetime import date
from allocation import hitung_rekomendasi 

st.set_page_config(page_title="Smart Allocation", page_icon="🤖", layout="wide")

st.title("🤖 AI Smart Allocation")
st.markdown("Sistem rekomendasi penjahit berbasis **Deadline Matematis** dan **Kapasitas Real-time**.")

st.divider()

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
        # Input Unlimited
        pcs = st.number_input("Jumlah Pcs", 1, 1000000, 100) 
        deadline_date = st.date_input("Tanggal Deadline", min_value=date.today())
    
    btn_cari = st.form_submit_button("🔍 Kalkulasi & Cari Solusi")

# LOGIKA UTAMA
if btn_cari:
    with st.spinner("Menghitung kapasitas & menyusun tim..."):
        time.sleep(0.5) 
        try:
            df_hasil, pesan = hitung_rekomendasi(jenis, pcs, deadline_date)
            
            # SIMPAN KE SESSION STATE
            st.session_state.search_done = True
            st.session_state.df_hasil = df_hasil
            st.session_state.input_pcs = pcs
            st.session_state.input_deadline = deadline_date
            
        except Exception as e:
            st.error(f"Terjadi kesalahan sistem: {e}")

# ==========================================
# 2. MENAMPILKAN HASIL
# ==========================================
if st.session_state.search_done and st.session_state.df_hasil is not None:
    
    df_hasil = st.session_state.df_hasil
    pcs_val = st.session_state.input_pcs
    deadline_val = st.session_state.input_deadline
    
    hari_sisa = (deadline_val - date.today()).days
    if hari_sisa <= 0: hari_sisa = 1
    target_speed = pcs_val / hari_sisa
    
    if not df_hasil.empty:
        top = df_hasil.iloc[0]
        is_single_capable = top['Sanggup?']
        
        # --- BAGIAN A: REKOMENDASI UTAMA (SOLO) ---
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

        with st.expander("Lihat Detail Top 10 Kandidat Individu", expanded=not is_single_capable):
            st.dataframe(
                df_hasil.head(10).style.format({
                    "FINAL_SCORE": "{:.2f}",
                    "Max Speed (Pcs/Hari)": "{:.1f}",
                    "Jarak (Km)": "{:.1f}"
                }).background_gradient(subset=['FINAL_SCORE'], cmap="Greens"),
                use_container_width=True
            )

        st.divider()

        # --- BAGIAN B: SIMULASI SPLIT ORDER (CUSTOM) ---
        
        if is_single_capable:
            st.subheader("⚡ Opsi Alternatif: Custom Split Order")
            st.caption("Bagi beban kerja ke beberapa orang agar lebih ringan.")
        else:
            st.subheader("🤝 Solusi Wajib: Rekomendasi Tim")
            st.caption("Satu orang tidak sanggup. Gunakan tim di bawah ini.")

        col_sim1, col_sim2 = st.columns([1, 2])
        
        with col_sim1:
            st.markdown("##### ⚙️ Atur Beban Kerja")
            
            # [PERBAIKAN 1]: Max Value dibuat unlimited (1 Juta) agar user bebas input > 1
            max_beban_user = st.number_input(
                "Maksimal Pcs per Orang:", 
                min_value=1,              # Bisa input 1, 2, 3...
                max_value=1000000,        # Batas atas sangat tinggi
                value=int(pcs_val) if not is_single_capable else int(pcs_val/2),
                step=10,
                help="Sistem akan memastikan TIDAK ADA penjahit yang mendapat tugas lebih dari angka ini."
            )
        
        with col_sim2:
            # 1. Hitung butuh berapa orang
            # Pastikan max_beban_user tidak 0 (untuk menghindari division by zero)
            safe_max_beban = max(1, max_beban_user)
            jumlah_org_butuh = math.ceil(pcs_val / safe_max_beban)
            
            candidates = df_hasil[df_hasil['Status'] == 'idle'].copy()
            
            # Ambil Top N orang
            team = candidates.head(jumlah_org_butuh)
            current_speed = team['Max Speed (Pcs/Hari)'].sum()
            
            # Cek Speed Target (Jika kurang, tambah orang)
            while current_speed < target_speed and len(team) < len(candidates):
                jumlah_org_butuh += 1
                team = candidates.head(jumlah_org_butuh)
                current_speed = team['Max Speed (Pcs/Hari)'].sum()

            final_team = []
            for idx, row in team.iterrows():
                final_team.append(row)

            if final_team:
                df_team = pd.DataFrame(final_team).reset_index(drop=True)
                total_cap = df_team['Max Speed (Pcs/Hari)'].sum()
                est_days = pcs_val / total_cap if total_cap > 0 else 999
                
                st.info(f"""
                **Hasil Simulasi:**
                Membatasi max **{safe_max_beban} pcs/orang** ➝ Butuh **{len(final_team)} Penjahit**.
                """)

                m1, m2, m3 = st.columns(3)
                m1.metric("Kapasitas Tim", f"{total_cap:.1f} pcs/hari", f"Target: {target_speed:.1f}")
                
                if est_days <= hari_sisa:
                    m2.metric("Estimasi Selesai", f"{est_days:.1f} Hari", f"✅ Aman (< {hari_sisa} hari)")
                else:
                    m2.metric("Estimasi Selesai", f"{est_days:.1f} Hari", f"⚠️ Telat", delta_color="inverse")
                    st.warning("Meski sudah dibagi tim, kapasitas masih kurang. Tambah orang atau undur deadline.")

        # --- [PERBAIKAN UTAMA] LOGIKA PEMBAGIAN TUGAS (STRICT CAPPING) ---
        st.markdown("##### ⚖️ Saran Pembagian Tugas:")
        
        if final_team:
            dist_data = []
            
            # Algoritma "Water Filling" (Strict Cap)
            # 1. Siapkan wadah (orang) dan kapasitas maksimal mereka
            team_indices = list(range(len(final_team)))
            allocations = [0] * len(final_team)
            remaining_pcs = pcs_val
            
            # 2. Distribusi Proporsional dulu (tapi dijaga max_beban)
            total_speed_team = sum([p['Max Speed (Pcs/Hari)'] for p in final_team])
            
            # Hitung 'share' ideal, tapi langsung di-cap di max_beban
            temp_allocations = []
            for p in final_team:
                ideal_share = (p['Max Speed (Pcs/Hari)'] / total_speed_team) * pcs_val
                # Kunci: Langsung batasi dengan max_beban_user
                capped_share = min(ideal_share, safe_max_beban) 
                temp_allocations.append(capped_share)
            
            # 3. Hitung sisa yang belum terbagi gara-gara di-cap
            assigned_so_far = sum([int(x) for x in temp_allocations])
            remaining_pcs = pcs_val - assigned_so_far
            
            allocations = [int(x) for x in temp_allocations]
            
            # 4. Jika masih ada sisa, distribusikan ke orang yang BELUM PENUH
            # Urutkan prioritas berdasarkan speed (kasih ke yg cepat dulu selama belum penuh)
            
            # Kita buat list index yang diurutkan dari yang tercepat
            sorted_by_speed_indices = sorted(range(len(final_team)), key=lambda k: final_team[k]['Max Speed (Pcs/Hari)'], reverse=True)
            
            while remaining_pcs > 0:
                distributed_in_this_loop = False
                for idx in sorted_by_speed_indices:
                    if remaining_pcs <= 0: break
                    
                    # Cek apakah orang ini masih punya ruang?
                    if allocations[idx] < safe_max_beban:
                        allocations[idx] += 1
                        remaining_pcs -= 1
                        distributed_in_this_loop = True
                
                # Safety break jika semua orang sudah full tapi pcs masih sisa 
                # (harusnya gak mungkin krn jumlah org dihitung berdasar kapasitas, tapi buat safety)
                if not distributed_in_this_loop:
                    st.warning(f"⚠️ Ada sisa {remaining_pcs} pcs yang tidak muat dibagikan karena semua penjahit sudah mentok di {safe_max_beban} pcs. Mohon naikkan sedikit batas maksimalnya.")
                    break

            # 5. Render ke Tabel
            for i, member in enumerate(final_team):
                dist_data.append({
                    "Nama Anggota": member['Nama'],
                    "Tugas (Pcs)": allocations[i], # Ini PASTI <= max_beban_user
                    "Kapasitas Harian": f"{member['Max Speed (Pcs/Hari)']:.1f}",
                    "Status": member['Status'].upper()
                })
            
            st.dataframe(pd.DataFrame(dist_data), use_container_width=True)
        else:
            st.error("Tidak cukup penjahit tersedia.")

    else:
        st.warning("Data tidak ditemukan.")

if st.session_state.search_done:
    if st.button("🔄 Reset / Cari Ulang"):
        st.session_state.search_done = False
        st.session_state.df_hasil = None
        st.rerun()