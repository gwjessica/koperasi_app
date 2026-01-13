# db_init.py (Script untuk inisialisasi database)
import sqlite3

def init_db():
    conn = sqlite3.connect('koperasi.db')
    c = conn.cursor()

    # 1. Tabel Admin (Login sederhana)
    c.execute('''CREATE TABLE IF NOT EXISTS admin (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE,
        password TEXT
    )''')

    # 2. Tabel Tailor (Penjahit) - Ditambah data untuk ML nanti
    c.execute('''CREATE TABLE IF NOT EXISTS tailors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        age INTEGER,
        distance_km REAL,
        speed_clothes_per_day REAL,
        specialty TEXT CHECK(specialty IN ('seragam', 'semua', 'atasan/rok/celana')), -- Uniform/Custom
        status TEXT CHECK(status IN ('idle', 'working')) DEFAULT 'idle', -- Idle/Working
        contact TEXT
    )''')

    # 3. Tabel Supplier
    c.execute('''CREATE TABLE IF NOT EXISTS suppliers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        address TEXT,
        contact TEXT,
        notes TEXT
    )''')

    # 4. Tabel Projects (Pesanan Masuk)
    c.execute('''CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_name TEXT,
        customer_name TEXT, -- Asumsi pengganti Customer ID jika belum ada tabel customer
        clothes_type TEXT CHECK(clothes_type IN ('seragam sekolah', 'seragam pramuka', 'rok', 'kemeja/batik', 'custom/gamis/sulit')), -- seragam sekolah, seragam pramuka, rok, kemeja/batik, custom/gamis/sulit
        amount INTEGER,
        deadline DATE,
        order_date DATE,
        status TEXT CHECK(status IN ('ongoing', 'done')) DEFAULT 'ongoing', -- Ongoing/Done
        notes TEXT,
        tailor_fee_per_item REAL,
        base_fee REAL,
        price_per_item REAL
    )''')

    # 5. Tabel Buy (Pembelian Bahan Baku saat Project Masuk)
    c.execute('''CREATE TABLE IF NOT EXISTS purchases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        supplier_id INTEGER,
        item TEXT,
        amount REAL,
        unit TEXT,
        price REAL,
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(project_id) REFERENCES projects(id),
        FOREIGN KEY(supplier_id) REFERENCES suppliers(id)
    )''')

    # 6. Tabel Stock (Inventory Sisa/Remnant)
    c.execute('''CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fabric_type TEXT,
        amount FLOAT,
        direction TEXT CHECK(direction IN ('IN', 'OUT')),
        reason TEXT CHECK(reason IN ('purchase', 'production', 'leftover', 'initial')),
        project_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # 7. Tabel Tailor History / Assignments (Hasil ML atau Manual)
    c.execute('''CREATE TABLE IF NOT EXISTS assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        tailor_id INTEGER,
        amount_assigned INTEGER,
        status TEXT CHECK(status IN ('assigned', 'submitted', 'paid')) DEFAULT 'assigned', -- Assigned/Submitted/Paid
        payment_amount REAL,
        FOREIGN KEY(project_id) REFERENCES projects(id),
        FOREIGN KEY(tailor_id) REFERENCES tailors(id)
    )''')

    conn.commit()
    conn.close()
    print("Database berhasil dibuat!")

if __name__ == "__main__":
    init_db()