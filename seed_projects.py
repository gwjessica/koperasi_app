import pandas as pd
import os
from datetime import timedelta
from db import get_connection


def detect_clothes_type(project_name):
    name = project_name.lower()
    if "pramuka" in name:
        return "seragam pramuka"
    elif "rok" in name:
        return "rok"
    elif "kaos" in name or "kemeja" in name or "batik" in name:
        return "kemeja/batik"
    elif "seragam" in name:
        return "seragam sekolah"
    else:
        return "custom/gamis/sulit"


def seed_projects():
    print("🚀 Mulai seeding data projects...")

    # === LOAD EXCEL ===
    current_dir = os.path.dirname(os.path.abspath(__file__))
    excel_path = os.path.join(current_dir, "REKAP_PROJECT_2025_KSMB.xlsx")

    if not os.path.exists(excel_path):
        print("❌ File Excel tidak ditemukan!")
        return

    df = pd.read_excel(excel_path)
    print(f"📄 {len(df)} data project dibaca dari Excel")

    # === CONNECT DB ===
    conn = get_connection()
    c = conn.cursor()

    inserted = 0

    for _, row in df.iterrows():
        project_name = str(row["ITEM PROJECT"]).strip()
        customer_name = str(row["INSTANSI"]).strip()
        order_date = pd.to_datetime(row["TANGGAL PEMESANAN"]).date()

        amount = int(row["QTY"])
        price_per_item = float(row["HARGA"])
        base_fee = float(row["REALISASI"])

        clothes_type = detect_clothes_type(project_name)

        # Estimasi deadline: 30 hari setelah order
        deadline = order_date + timedelta(days=30)

        # Estimasi upah jahit (contoh: 65% dari harga jual)
        # tailor_fee_per_item = price_per_item * 0.65

        notes = f"Data impor dari rekap koperasi 2025. Realisasi: Rp {row['REALISASI']:,.0f}"

        # Cegah duplikasi
        c.execute("""
            SELECT id FROM projects
            WHERE project_name = ? AND customer_name = ?
        """, (project_name, customer_name))

        if c.fetchone():
            continue

        c.execute("""
            INSERT INTO projects (
                project_name,
                customer_name,
                clothes_type,
                amount,
                deadline,
                order_date,
                status,
                notes,
                base_fee,
                price_per_item
            ) VALUES (?, ?, ?, ?, ?, ?, 'done', ?, ?, ?)
        """, (
            project_name,
            customer_name,
            clothes_type,
            amount,
            deadline,
            order_date,
            notes,
            base_fee,
            price_per_item
        ))

        inserted += 1

    conn.commit()
    conn.close()

    print("-" * 40)
    print(f"✅ Selesai! {inserted} project berhasil dimasukkan.")


if __name__ == "__main__":
    seed_projects()