import pandas as pd
import sqlite3
import os
from db import get_connection

def seed_database():
    print("🚀 Memulai proses pengisian database...")

    # 1. BACA DATA CSV
    current_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(current_dir, 'DATA_FINAL_CLUSTERED.csv')
    
    if not os.path.exists(csv_path):
        print("❌ Error: File DATA_FINAL_CLUSTERED.csv tidak ditemukan!")
        return

    df = pd.read_csv(csv_path)
    print(f"📄 Berhasil membaca {len(df)} data penjahit dari CSV.")

    # 2. KONEKSI KE DATABASE
    conn = get_connection()
    c = conn.cursor()

    # 3. LOOPING INPUT DATA
    count = 0
    
    # Daftar kolom kecepatan yang PASTI ADA di CSV
    cols_speed = [
        "Seragam Hem Putih (Pcs/hari)",
        "Seragam Hem Pramuka (Pcs/hari)", 
        "Celana Pramuka Seragam (Pcs/hari)", 
        "Rok Seragam (Pcs/hari)",
        "Kemeja Kerja (Pcs/hari)",
        "Custom (Sulit) (Pcs/hari)"
    ]
    
    # Filter hanya kolom yang benar-benar ada di CSV
    valid_speed_cols = [col for col in cols_speed if col in df.columns]

    for index, row in df.iterrows():
        name = row['Nama']
        
        # Cek apakah penjahit sudah ada di DB
        c.execute("SELECT id FROM tailors WHERE name = ?", (name,))
        if c.fetchone():
            # print(f"⚠️  Skip: {name} (Sudah ada)")
            continue

        age = int(row['Usia'])
        distance = float(row['Jarak Rumah ke Koperasi (Km)'])
        
        # --- LOGIKA HITUNG SPEED (RATA-RATA) ---
        if valid_speed_cols:
            speed_values = [row[col] for col in valid_speed_cols]
            speed = sum(speed_values) / len(speed_values) # Ambil rata-ratanya
        else:
            speed = 5.0 # Default jika tidak ada data
            
        # Spesialisasi
        spesialis_raw = str(row['Spesialis']).lower()
        if(spesialis_raw == "hanya bisa mengerjakan rok, atasan dan celana"):
            specialty = "atasan/rok/celana"
        else:
            specialty = spesialis_raw

        # Insert ke Database
        c.execute("""
            INSERT INTO tailors 
            (name, age, distance_km, speed_clothes_per_day, specialty, status, contact)
            VALUES (?, ?, ?, ?, ?, 'idle', '-')
        """, (name, age, distance, speed, specialty))
        
        count += 1

    conn.commit()
    conn.close()
    
    print("-" * 30)
    print(f"✅ SUKSES! {count} penjahit baru berhasil dimasukkan ke Database.")

if __name__ == "__main__":
    seed_database()