import pandas as pd
import numpy as np
import os
from sklearn.preprocessing import MinMaxScaler
from db import get_connection  # KITA IMPORT KONEKSI DATABASE DISINI

def hitung_rekomendasi(jenis_project, jumlah_pcs, kondisi_deadline):
    """
    Sistem Alokasi Penjahit Cerdas (Hybrid: CSV Skill + Database Availability)
    """
    
    # ==========================================
    # 1. SETUP & LOAD DATA (GABUNGAN CSV + DB)
    # ==========================================
    
    # A. Load Skill Statis (CSV)
    # Kita pakai trik 'os.path' biar filenya pasti ketemu
    current_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(current_dir, 'DATA_FINAL_CLUSTERED.csv')
    
    try:
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        # Return kosong jika file hilang (safety net)
        return pd.DataFrame(), "⚠️ Error: File DATA_FINAL_CLUSTERED.csv tidak ditemukan!"

    # B. Load Status Real-time (Database SQLite)
    # Ini langkah kuncinya: Membaca siapa yang sedang 'working'
    conn = get_connection()
    query = "SELECT name AS Nama, status FROM tailors"
    df_db = pd.read_sql_query(query, conn)
    conn.close()
    
    # C. Gabungkan Data (Merge)
    # Tempelkan status dari DB ke data CSV berdasarkan Nama
    df = pd.merge(df, df_db, on='Nama', how='left')
    df['status'] = df['status'].fillna('idle') # Kalau tidak ada di DB, anggap idle

    scaler = MinMaxScaler()

    # Mapping Input User ke Kolom Kapabilitas
    map_kapabilitas = {
        "Seragam Sekolah": ["Seragam Hem Putih (Pcs/hari)", "Seragam Hem Pramuka (Pcs/hari)"],
        "Seragam Pramuka": ["Seragam Hem Pramuka (Pcs/hari)", "Celana Pramuka Seragam (Pcs/hari)"],
        "Rok Seragam": ["Rok Seragam (Pcs/hari)"],
        "Kemeja/Batik": ["Kemeja Kerja (Pcs/hari)"],
        "Custom/Gamis/Sulit": ["Custom (Sulit) (Pcs/hari)"]
    }
    kolom_kapabilitas = map_kapabilitas.get(jenis_project, [])

    # ==========================================
    # 2. FILTERING
    # ==========================================
    if jenis_project == "Custom/Gamis/Sulit":
        df = df[df['Custom (Sulit) (Pcs/hari)'] > 0].copy()
        if df.empty:
            return df, "⚠️ Tidak ada penjahit untuk Custom/Sulit!"

    # ==========================================
    # 3. PERHITUNGAN SKOR
    # ==========================================

    # --- A. SKOR USIA ---
    df['Selisih_Usia'] = abs(df['Usia'] - 40)
    df['Skor_Usia'] = 1 - scaler.fit_transform(df[['Selisih_Usia']])

    # --- B. SKOR JARAK ---
    df['Jarak_Norm'] = scaler.fit_transform(df[['Jarak Rumah ke Koperasi (Km)']])
    
    if jumlah_pcs < 20:
        df['Skor_Lokasi'] = 1 - df['Jarak_Norm'] 
        pesan_jarak = "📦 Order Kecil: Prioritas TERDEKAT."
    elif jumlah_pcs > 50:
        df['Skor_Lokasi'] = df['Jarak_Norm'] * 0.5 + 0.5 
        pesan_jarak = "🚛 Order Besar: Jarak jauh tidak masalah."
    else:
        # Ini bug yang tadi sudah difix
        df['Skor_Lokasi'] = 0.5 
        pesan_jarak = "⚖️ Order Menengah: Lokasi Netral."

    # --- C. SKOR PERFORMA ---
    df['Skor_Attitude'] = (
        (df['Kerapian'] * 30) + 
        (df['Komitmen'] * 25) + 
        (df['Ketepatan Waktu'] * 20)
    )

    # --- D. SKOR KAPABILITAS ---
    if kolom_kapabilitas:
        df['Raw_Kapabilitas'] = df[kolom_kapabilitas].mean(axis=1)
        df['Skor_Kapabilitas'] = scaler.fit_transform(df[['Raw_Kapabilitas']])
    else:
        df['Raw_Kapabilitas'] = 0 
        df['Skor_Kapabilitas'] = 0.5

    # --- E. SKOR SPESIALIS ---
    def hitung_match_spesialis(row):
        spesialis = str(row['Spesialis']).lower()
        project = jenis_project.lower()
        if "seragam" in project and "seragam" in spesialis and "semua" not in spesialis: return 1.0
        elif "semua" in spesialis: return 0.8
        elif "rok" in project and "rok" in spesialis: return 0.9
        else: return 0.2
            
    df['Skor_Spesialis'] = df.apply(hitung_match_spesialis, axis=1)

    # ==========================================
    # 4. FINAL CALCULATION & PENALTY
    # ==========================================
    
    if kondisi_deadline == "Urgent (Buru-buru!)":
        df['FINAL_SCORE'] = (
            (df['Skor_Kapabilitas'] * 35) +
            (df['Skor_Attitude'] * 20) +
            (df['Skor_Lokasi'] * 15) +
            (df['Skor_Usia'] * 10) +
            (df['Skor_Spesialis'] * 20)
        )
        strategi_msg = f"🚀 **URGENT**: Fokus Speed & Lokasi.\n\n{pesan_jarak}"
        df = df[df['Kategori_ML'] != 'Perlu Bimbingan']
    else:
        df['FINAL_SCORE'] = (
            (df['Skor_Attitude'] * 40) +
            (df['Skor_Spesialis'] * 20) +
            (df['Skor_Usia'] * 20) +
            (df['Skor_Lokasi'] * 10) +
            (df['Skor_Kapabilitas'] * 10)
        )
        strategi_msg = f"⚖️ **SANTAI**: Fokus Kerapian & Pemerataan.\n\n{pesan_jarak}"

    # --- LOGIKA PENALTI STATUS ---
    # Jika status = 'working', kurangi nilai drastis (misal 10.000 poin)
    # Ini akan membuat penjahit sibuk jatuh ke urutan paling bawah
    def beri_hukuman(status):
        if status == 'working':
            return 10000 
        return 0

    df['Penalti_Sibuk'] = df['status'].apply(beri_hukuman)
    df['FINAL_SCORE'] = df['FINAL_SCORE'] - df['Penalti_Sibuk']

    # ==========================================
    # 5. OUTPUT
    # ==========================================
    df_sorted = df.sort_values(by='FINAL_SCORE', ascending=False)
    
    tampilan = [
        'Nama', 
        'status',          # Kita tampilkan statusnya biar jelas
        'Kategori_ML', 
        'Spesialis', 
        'Jarak Rumah ke Koperasi (Km)',
        'Kerapian', 
        'FINAL_SCORE'
    ]
    
    if kolom_kapabilitas:
        tampilan.insert(5, 'Raw_Kapabilitas')

    rename_dict = {
        'Raw_Kapabilitas': 'Est. Speed (Pcs/Hari)',
        'Jarak Rumah ke Koperasi (Km)': 'Jarak (Km)',
        'status': 'Status Saat Ini'
    }
    
    # Return Top 10
    return df_sorted[tampilan].rename(columns=rename_dict).head(10), strategi_msg