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
    
    # ... (BAGIAN SETUP DATA SAMA SEPERTI SEBELUMNYA) ...
    current_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(current_dir, 'DATA_FINAL_CLUSTERED.csv')
    
    try:
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        return pd.DataFrame(), "⚠️ Error: File CSV tidak ditemukan!"

    conn = get_connection()
    df_db = pd.read_sql_query("SELECT name AS Nama, status FROM tailors", conn)
    conn.close()
    
    df = pd.merge(df, df_db, on='Nama', how='left')
    df['status'] = df['status'].fillna('idle')

    scaler = MinMaxScaler()

    map_kapabilitas = {
        "Seragam Sekolah": ["Seragam Hem Putih (Pcs/hari)", "Seragam Hem Pramuka (Pcs/hari)"],
        "Seragam Pramuka": ["Seragam Hem Pramuka (Pcs/hari)", "Celana Pramuka Seragam (Pcs/hari)"],
        "Rok Seragam": ["Rok Seragam (Pcs/hari)"],
        "Kemeja/Batik": ["Kemeja Kerja (Pcs/hari)"],
        "Custom/Gamis/Sulit": ["Custom (Sulit) (Pcs/hari)"]
    }
    kolom_kapabilitas = map_kapabilitas.get(jenis_project, [])

    # ... (BAGIAN HITUNG DEADLINE & SKOR SAMA SEPERTI SEBELUMNYA) ...
    today = date.today()
    sisa_hari = (tgl_deadline - today).days
    if sisa_hari <= 0:
        sisa_hari = 1
        pesan_waktu = "🔥 DEADLINE HARI INI!"
    else:
        pesan_waktu = f"⏳ Sisa Waktu: {sisa_hari} hari."

    target_speed_per_hari = jumlah_pcs / sisa_hari

    # Hitung Real Speed
    if kolom_kapabilitas:
        df['Real_Speed'] = df[kolom_kapabilitas].mean(axis=1).fillna(0)
    else:
        df['Real_Speed'] = 0

    if jenis_project == "Custom/Gamis/Sulit":
        df = df[df['Real_Speed'] > 0].copy()

    df['Sanggup_Kejar_Deadline'] = df['Real_Speed'] >= (target_speed_per_hari * 0.9)

    # Normalisasi & Skor (Sama)
    df['Selisih_Usia'] = abs(df['Usia'] - 40)
    df['Skor_Usia'] = 1 - scaler.fit_transform(df[['Selisih_Usia']])
    df['Jarak_Norm'] = scaler.fit_transform(df[['Jarak Rumah ke Koperasi (Km)']])
    
    if jumlah_pcs < 20: df['Skor_Lokasi'] = 1 - df['Jarak_Norm'] 
    elif jumlah_pcs > 50: df['Skor_Lokasi'] = df['Jarak_Norm'] * 0.5 + 0.5 
    else: df['Skor_Lokasi'] = 0.5 

    df['Skor_Attitude'] = ((df['Kerapian'] * 30) + (df['Komitmen'] * 25) + (df['Ketepatan Waktu'] * 20))
    df['Skor_Kapabilitas'] = scaler.fit_transform(df[['Real_Speed']])

    def hitung_match(row):
        spec = str(row['Spesialis']).lower()
        proj = jenis_project.lower()
        if "seragam" in proj and "seragam" in spec: return 1.0
        elif "semua" in spec: return 0.9
        elif "rok" in proj and "rok" in spec: return 1.0
        return 0.3
    df['Skor_Spesialis'] = df.apply(hitung_match, axis=1)

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

    def penalti_status(row):
        if row['status'] == 'working': return 10000 
        return 0
    
    def penalti_ketidaksanggupan(row):
        if not row['Sanggup_Kejar_Deadline']: return 5000 
        return 0

    df['FINAL_SCORE'] = df['FINAL_SCORE'] - df.apply(penalti_status, axis=1)
    df['FINAL_SCORE'] = df['FINAL_SCORE'] - df.apply(penalti_ketidaksanggupan, axis=1)

    # --- PERUBAHAN UTAMA DISINI: HAPUS .head(10) ---
    # Kita kembalikan SEMUA penjahit yang ada agar algoritma tim bisa mencari sampai bawah
    df_sorted = df.sort_values(by='FINAL_SCORE', ascending=False)

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