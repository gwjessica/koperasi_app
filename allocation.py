import pandas as pd
import numpy as np
import os
from datetime import date
from sklearn.preprocessing import MinMaxScaler
from db import get_connection

def hitung_rekomendasi(jenis_project, jumlah_pcs, tgl_deadline):
    """
    Sistem Alokasi Penjahit Cerdas Berbasis Deadline & Kapasitas Real
    """
    
    # ==========================================
    # 1. SETUP & LOAD DATA
    # ==========================================
    current_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(current_dir, 'DATA_FINAL_CLUSTERED.csv')
    
    try:
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        return pd.DataFrame(), "⚠️ Error: File CSV tidak ditemukan!"

    # Load Status Real-time
    conn = get_connection()
    df_db = pd.read_sql_query("SELECT name AS Nama, status FROM tailors", conn)
    conn.close()
    
    df = pd.merge(df, df_db, on='Nama', how='left')
    df['status'] = df['status'].fillna('idle')

    scaler = MinMaxScaler()

    # Mapping Kapabilitas (Sama seperti sebelumnya)
    map_kapabilitas = {
        "Seragam Sekolah": ["Seragam Hem Putih (Pcs/hari)", "Seragam Hem Pramuka (Pcs/hari)"],
        "Seragam Pramuka": ["Seragam Hem Pramuka (Pcs/hari)", "Celana Pramuka Seragam (Pcs/hari)"],
        "Rok Seragam": ["Rok Seragam (Pcs/hari)"],
        "Kemeja/Batik": ["Kemeja Kerja (Pcs/hari)"],
        "Custom/Gamis/Sulit": ["Custom (Sulit) (Pcs/hari)"]
    }
    kolom_kapabilitas = map_kapabilitas.get(jenis_project, [])

    # ==========================================
    # 2. HITUNG LOGIKA DEADLINE (MATEMATIKA)
    # ==========================================
    today = date.today()
    
    # Hitung selisih hari
    sisa_hari = (tgl_deadline - today).days
    
    # Handle jika deadline hari ini atau lewat (set minimal 1 hari kerja)
    if sisa_hari <= 0:
        sisa_hari = 1
        pesan_waktu = "🔥 DEADLINE HARI INI! Butuh penjahit super cepat."
    else:
        pesan_waktu = f"⏳ Sisa Waktu: {sisa_hari} hari."

    # Hitung Speed yang DIBUTUHKAN (Target)
    target_speed_per_hari = jumlah_pcs / sisa_hari

    # ==========================================
    # 3. PERHITUNGAN SKOR & KEMAMPUAN
    # ==========================================

    # --- A. HITUNG SPEED PENJAHIT (REAL) ---
    if kolom_kapabilitas:
        # Ambil rata-rata speed penjahit di kategori yang dipilih
        df['Real_Speed'] = df[kolom_kapabilitas].mean(axis=1).fillna(0)
    else:
        df['Real_Speed'] = 0

    # Filter khusus Custom
    if jenis_project == "Custom/Gamis/Sulit":
        df = df[df['Real_Speed'] > 0].copy()

    # --- B. CEK KESANGGUPAN (FEASIBILITY) ---
    # Apakah penjahit sanggup mengejar target harian?
    # Kita beri toleransi sedikit (misal speed 4.8 dianggap sanggup kejar 5.0)
    df['Sanggup_Kejar_Deadline'] = df['Real_Speed'] >= (target_speed_per_hari * 0.9)

    # --- C. NORMALISASI VARIABEL LAIN ---
    df['Selisih_Usia'] = abs(df['Usia'] - 40)
    df['Skor_Usia'] = 1 - scaler.fit_transform(df[['Selisih_Usia']])
    df['Jarak_Norm'] = scaler.fit_transform(df[['Jarak Rumah ke Koperasi (Km)']])
    
    # Logika Jarak (Sama)
    if jumlah_pcs < 20:
        df['Skor_Lokasi'] = 1 - df['Jarak_Norm'] 
    elif jumlah_pcs > 50:
        df['Skor_Lokasi'] = df['Jarak_Norm'] * 0.5 + 0.5 
    else:
        df['Skor_Lokasi'] = 0.5 

    df['Skor_Attitude'] = ((df['Kerapian'] * 30) + (df['Komitmen'] * 25) + (df['Ketepatan Waktu'] * 20))
    df['Skor_Kapabilitas'] = scaler.fit_transform(df[['Real_Speed']])

    # --- D. SKOR SPESIALIS ---
    def hitung_match(row):
        spec = str(row['Spesialis']).lower()
        proj = jenis_project.lower()
        if "seragam" in proj and "seragam" in spec: return 1.0
        elif "semua" in spec: return 0.9
        elif "rok" in proj and "rok" in spec: return 1.0
        return 0.3
    df['Skor_Spesialis'] = df.apply(hitung_match, axis=1)

    # ==========================================
    # 4. PEMBOBOTAN DINAMIS BERDASARKAN BEBAN
    # ==========================================
    
    # Jika target harian tinggi (> 8 pcs/hari), sistem anggap ini "Berat/Urgent"
    # Maka bobot Kecepatan ditingkatkan.
    if target_speed_per_hari > 8:
        bobot_speed = 40
        bobot_attitude = 15
        mode_msg = "🚀 Mode: **HIGH SPEED** (Target Tinggi)"
    else:
        bobot_speed = 15
        bobot_attitude = 40
        mode_msg = "💎 Mode: **QUALITY FOCUS** (Target Santai)"

    df['FINAL_SCORE'] = (
        (df['Skor_Kapabilitas'] * bobot_speed) +
        (df['Skor_Attitude'] * bobot_attitude) +
        (df['Skor_Lokasi'] * 15) +
        (df['Skor_Usia'] * 10) +
        (df['Skor_Spesialis'] * 20)
    )

    # ==========================================
    # 5. PENALTI & FILTERING
    # ==========================================
    
    # Penalti 1: Jika sedang WORKING (Sibuk)
    def penalti_status(row):
        if row['status'] == 'working': return 10000 
        return 0
    
    # Penalti 2: Jika SPEED TIDAK MUMPUNI (Sangat Penting)
    # Jika dia tidak sanggup mengejar deadline, kurangi nilai drastis
    def penalti_ketidaksanggupan(row):
        if not row['Sanggup_Kejar_Deadline']: return 5000 
        return 0

    df['FINAL_SCORE'] = df['FINAL_SCORE'] - df.apply(penalti_status, axis=1)
    df['FINAL_SCORE'] = df['FINAL_SCORE'] - df.apply(penalti_ketidaksanggupan, axis=1)

    # Urutkan
    df_sorted = df.sort_values(by='FINAL_SCORE', ascending=False).head(10)

    # ==========================================
    # 6. PERSIAPAN OUTPUT
    # ==========================================
    pesan_final = f"""
    {mode_msg}
    - Target: **{jumlah_pcs} pcs** dalam **{sisa_hari} hari**
    - Speed Min: **{target_speed_per_hari:.1f} pcs/hari**
    """

    rename_dict = {
        'Real_Speed': 'Max Speed (Pcs/Hari)',
        'Jarak Rumah ke Koperasi (Km)': 'Jarak (Km)',
        'status': 'Status',
        'Sanggup_Kejar_Deadline': 'Sanggup?'
    }
    
    cols = ['Nama', 'status', 'Sanggup_Kejar_Deadline', 'Real_Speed', 'Jarak Rumah ke Koperasi (Km)', 'FINAL_SCORE']
    
    return df_sorted[cols].rename(columns=rename_dict), pesan_final