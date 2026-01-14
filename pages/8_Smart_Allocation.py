import streamlit as st
import time
from datetime import date
from allocation import hitung_rekomendasi 

st.set_page_config(page_title="Smart Allocation", page_icon="🤖", layout="wide")

st.title("🤖 AI Smart Allocation")
st.markdown("Sistem rekomendasi penjahit berbasis **Deadline Matematister** dan **Kapasitas Real-time**.")

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
        # GANTI RADIO BUTTON DENGAN DATE INPUT
        deadline_date = st.date_input("Tanggal Deadline", min_value=date.today())
    
    btn_cari = st.form_submit_button("🔍 Kalkulasi & Cari Penjahit")

# --- HASIL REKOMENDASI ---
if btn_cari:
    with st.spinner("Menghitung hari kerja & kapasitas produksi..."):
        time.sleep(0.5) 
        
        try:
            # Pass tanggal deadline ke fungsi
            df_hasil, pesan = hitung_rekomendasi(jenis, pcs, deadline_date)
            
            # Tampilkan Pesan Strategi
            st.success("Kalkulasi Selesai!")
            st.info(pesan)
            
            # Highlight Penjahit Terbaik
            if not df_hasil.empty:
                top = df_hasil.iloc[0]
                
                # Cek apakah rekomendasi utama sanggup?
                sanggup_icon = "✅" if top['Sanggup?'] else "⚠️"
                status_msg = f"{top['Status'].upper()}"
                
                if not top['Sanggup?']:
                    st.warning(f"⚠️ Peringatan: Rekomendasi teratas ({top['Nama']}) mungkin butuh lembur/bantuan karena speed pas-pasan.")
                
                st.markdown(f"""
                ### 🏆 Rekomendasi Utama: **{top['Nama']}**
                - **Status:** {status_msg}
                - **Kapasitas:** {top['Max Speed (Pcs/Hari)']:.1f} pcs/hari
                - **Prediksi:** {sanggup_icon} {'Sanggup Kejar Tayang' if top['Sanggup?'] else 'Resiko Terlambat'}
                """)
            
            # Tampilkan Tabel
            st.dataframe(
                df_hasil.style.format({
                    "FINAL_SCORE": "{:.2f}",
                    "Max Speed (Pcs/Hari)": "{:.1f}",
                    "Jarak (Km)": "{:.1f}"
                }).background_gradient(subset=['FINAL_SCORE'], cmap="Greens"),
                use_container_width=True,
                height=500
            )
            
            st.caption("💡 **Catatan:** Kolom 'Sanggup?' menghitung apakah Speed Harian Penjahit >= Target Harian Project.")
            
        except Exception as e:
            st.error(f"Terjadi kesalahan: {e}")