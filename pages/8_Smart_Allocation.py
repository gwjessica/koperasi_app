import streamlit as st
import pandas as pd
import time
from datetime import date
from allocation import hitung_rekomendasi 

st.set_page_config(page_title="Smart Allocation", page_icon="🤖", layout="wide")

st.title("🤖 AI Smart Allocation")
st.markdown("Sistem rekomendasi penjahit berbasis **Deadline Matematis** dan **Kapasitas Real-time**.")

st.divider()

# --- FORM INPUT ---
with st.form("form_cari"):
    st.subheader("📝 Detail Order Baru")
    
    col1, col2 = st.columns(2)
    with col1:
        project_name = st.text_input("Nama Project", "Project Baru")
        jenis = st.selectbox("Jenis Kategori", 
            ["Seragam Sekolah", "Seragam Pramuka", "Rok Seragam", "Kemeja/Batik", "Custom/Gamis/Sulit"])
    with col2:
        pcs = st.number_input("Jumlah Pcs", 1, 5000, 100)
        deadline_date = st.date_input("Tanggal Deadline", min_value=date.today())
    
    btn_cari = st.form_submit_button("🔍 Kalkulasi & Cari Solusi")

# --- HASIL REKOMENDASI ---
if btn_cari:
    with st.spinner("Menghitung kapasitas & menyusun tim..."):
        time.sleep(0.5) 
        
        try:
            # 1. Panggil fungsi perhitungan dasar
            df_hasil, pesan = hitung_rekomendasi(jenis, pcs, deadline_date)
            
            # Hitung target speed di sini untuk logika UI (Redudansi aman)
            hari_sisa = (deadline_date - date.today()).days
            if hari_sisa <= 0: hari_sisa = 1
            target_speed = pcs / hari_sisa
            
            # --- BAGIAN 1: REKOMENDASI INDIVIDU ---
            if not df_hasil.empty:
                top = df_hasil.iloc[0]
                is_single_capable = top['Sanggup?']
                
                # Container Utama
                with st.container():
                    st.success("✅ Analisis Selesai!")
                    st.info(f"""
                    **Target Produksi:** {target_speed:.1f} pcs/hari (Selama {hari_sisa} hari)
                    """)

                    # Jika satu orang sanggup, tampilkan seperti biasa
                    if is_single_capable:
                        st.markdown(f"""
                        ### 🏆 Rekomendasi Utama: **{top['Nama']}**
                        - **Status:** {top['Status'].upper()}
                        - **Kapasitas:** {top['Max Speed (Pcs/Hari)']:.1f} pcs/hari
                        - **Prediksi:** ✅ Sanggup Mengerjakan Sendiri
                        """)
                    else:
                        # Jika tidak sanggup, beri warning merah
                        st.error(f"⚠️ Tidak ada penjahit yang sanggup mengerjakan {pcs} pcs sendirian dalam {hari_sisa} hari!")
                        st.markdown(f"**Kandidat Terbaik (Solo):** {top['Nama']} (Hanya mampu {top['Max Speed (Pcs/Hari)']:.1f} pcs/hari)")

                # Tampilkan Tabel Lengkap
                with st.expander("Lihat Detail Semua Kandidat", expanded=not is_single_capable):
                    st.dataframe(
                        df_hasil.style.format({
                            "FINAL_SCORE": "{:.2f}",
                            "Max Speed (Pcs/Hari)": "{:.1f}",
                            "Jarak (Km)": "{:.1f}"
                        }).background_gradient(subset=['FINAL_SCORE'], cmap="Greens"),
                        use_container_width=True
                    )

                # --- BAGIAN 2: REKOMENDASI TIM (FITUR BARU) ---
                # Hanya muncul jika Top 1 tidak sanggup ATAU user ingin opsi tim
                if not is_single_capable:
                    st.divider()
                    st.subheader("🤝 Solusi: Rekomendasi Tim (Split Order)")
                    st.markdown("Sistem mengkombinasikan beberapa penjahit **IDLE** terbaik untuk mencapai target.")

                    # Filter hanya yang IDLE (Jangan ganggu yang sibuk)
                    candidates = df_hasil[df_hasil['Status'] == 'idle'].copy()
                    
                    team = []
                    current_speed = 0
                    cukup = False

                    # Algoritma Greedy: Ambil yang skor tertinggi terus sampai target tercapai
                    for idx, row in candidates.iterrows():
                        team.append(row)
                        current_speed += row['Max Speed (Pcs/Hari)']
                        if current_speed >= target_speed:
                            cukup = True
                            break
                    
                    if team:
                        df_team = pd.DataFrame(team).reset_index(drop=True)
                        
                        # Hitung metrik tim
                        total_cap = df_team['Max Speed (Pcs/Hari)'].sum()
                        est_days = pcs / total_cap if total_cap > 0 else 999
                        
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Jumlah Anggota Tim", f"{len(team)} Orang")
                        c2.metric("Total Kapasitas Tim", f"{total_cap:.1f} pcs/hari", f"Target: {target_speed:.1f}")
                        c3.metric("Estimasi Selesai", f"{est_days:.1f} Hari", f"Deadline: {hari_sisa} Hari")

                        if cukup:
                            st.success("✅ Tim ini SANGGUP mengejar deadline!")
                        else:
                            st.warning("⚠️ Bahkan dengan menggabungkan semua penjahit IDLE, target masih sulit dicapai. Pertimbangkan negosiasi deadline.")

                        st.markdown("##### 📋 Daftar Anggota Tim:")
                        st.dataframe(
                            df_team[['Nama', 'Max Speed (Pcs/Hari)', 'Jarak (Km)', 'FINAL_SCORE']],
                            use_container_width=True
                        )
                        
                        # Distribusi Tugas Sederhana
                        st.markdown("##### ⚖️ Saran Pembagian Tugas:")
                        dist_cols = st.columns(len(team))
                        sisa_pcs = pcs
                        
                        for i, member in enumerate(team):
                            # Pembagian proporsional berdasarkan speed
                            proporsi = member['Max Speed (Pcs/Hari)'] / total_cap
                            tugas_pcs = int(proporsi * pcs)
                            
                            # Koreksi pembulatan di orang terakhir
                            if i == len(team) - 1:
                                tugas_pcs = sisa_pcs
                            else:
                                sisa_pcs -= tugas_pcs
                                
                            with dist_cols[i]:
                                st.info(f"**{member['Nama']}**\n\n🎯 {tugas_pcs} pcs")

                    else:
                        st.error("Tidak ada penjahit IDLE yang tersedia untuk membentuk tim.")

            else:
                st.warning("Database penjahit kosong atau tidak ada yang cocok dengan kriteria.")
            
        except Exception as e:
            st.error(f"Terjadi kesalahan: {e}")