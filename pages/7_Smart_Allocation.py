import streamlit as st
import time
# Sekarang kita bisa import karena allocation.py sudah satu folder
from allocation import hitung_rekomendasi 

st.set_page_config(page_title="Smart Allocation", page_icon="🤖")

st.title("🤖 AI Smart Allocation")
st.markdown("""
Fitur ini menggabungkan:
1.  **Data Skill** (dari CSV Machine Learning)
2.  **Ketersediaan Real-time** (dari Database Koperasi)
""")

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
        pcs = st.number_input("Jumlah Pcs", 1, 1000, 50)
        deadline = st.radio("Kondisi Deadline", ["Santai (Normal)", "Urgent (Buru-buru!)"])
    
    btn_cari = st.form_submit_button("🔍 Cari Penjahit Terbaik")

# --- HASIL REKOMENDASI ---
if btn_cari:
    with st.spinner("Mengecek database & menghitung skor kecocokan..."):
        time.sleep(0.5) # Gimmick loading
        
        try:
            # Panggil fungsi dari allocation.py
            df_hasil, pesan = hitung_rekomendasi(jenis, pcs, deadline)
            
            st.success(f"Analisis Selesai! {pesan}")
            
            # Highlight Penjahit Terbaik
            if not df_hasil.empty:
                top = df_hasil.iloc[0]
                st.info(f"🏆 Rekomendasi Utama: **{top['Nama']}** (Status: {top['Status Saat Ini'].upper()})")
            
            # Tampilkan Tabel
            st.dataframe(
                df_hasil.style.format({
                    "FINAL_SCORE": "{:.2f}",
                    "Est. Speed (Pcs/Hari)": "{:.1f}",
                    "Jarak (Km)": "{:.1f}"
                }).background_gradient(subset=['FINAL_SCORE'], cmap="Greens"),
                use_container_width=True,
                height=500
            )
            
            st.caption("💡 Catatan: Penjahit dengan status 'working' mendapat pengurangan skor drastis agar tidak dipilih.")
            
        except Exception as e:
            st.error(f"Terjadi kesalahan: {e}")
            st.warning("Pastikan file 'DATA_FINAL_CLUSTERED.csv' ada dan nama penjahit di Database sesuai dengan CSV.")