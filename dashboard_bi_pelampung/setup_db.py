import pandas as pd
import sqlite3
import numpy as np
import os

# ─── CONFIG ──────────────────────────────────────────────────────────────────
EXCEL_PATH = "2025_Data_Transaksi_Pelampung_.xlsx"
DB_PATH    = "pelampung.db"

MONTH_NAMES = {
    1: "Januari", 2: "Februari", 3: "Maret", 4: "April",
    5: "Mei", 6: "Juni", 7: "Juli", 8: "Agustus",
    9: "September", 10: "Oktober", 11: "November", 12: "Desember"
}

# ─── STEP 1: LOAD MASTER TABLES ──────────────────────────────────────────────
def load_master_tables():
    print("📂 Memuat sheet master...")

    # Master Barang
    df_barang = pd.read_excel(EXCEL_PATH, sheet_name='Master_Barang_Harga')
    df_barang.columns = [c.strip() for c in df_barang.columns]
    df_barang = df_barang.rename(columns={
        'Tipe_ID (Unique)'         : 'ID_Produk',
        'Kategori_Model (Kategori)': 'Kategori_Model'
    })
    # Hitung 10kg/karung jika kosong (10.000g / Berat_Asli_gram)
    df_barang['Karung_Ukuran_60Kg'] = df_barang['Karung_Ukuran_60Kg'].fillna(
        10000 / df_barang['Berat_Asli']
    )
    df_barang['Karung_Ukuran_60Kg'] = df_barang['Karung_Ukuran_60Kg'].replace(0, np.nan)

    # Master Logistik
    df_logistik = pd.read_excel(EXCEL_PATH, sheet_name='Master_Logistik')
    df_logistik.columns = [c.strip() for c in df_logistik.columns]

    # Master Pelanggan
    df_pelanggan = pd.read_excel(EXCEL_PATH, sheet_name='Master_Pelanggan')
    df_pelanggan.columns = [c.strip() for c in df_pelanggan.columns]

    print(f"   ✅ Barang    : {len(df_barang)} produk")
    print(f"   ✅ Logistik  : {len(df_logistik)} kota")
    print(f"   ✅ Pelanggan : {len(df_pelanggan)} customer")
    return df_barang, df_logistik, df_pelanggan


# ─── STEP 2: LOAD TRANSAKSI (MASTER2025) ─────────────────────────────────────
def load_transaksi():
    print("\n📊 Memuat data transaksi MASTER2025...")
    df = pd.read_excel(EXCEL_PATH, sheet_name='MASTER2025')
    df.columns = [c.strip() for c in df.columns]

    # Bersihkan data kosong
    df = df.dropna(subset=['Nomor_PO', 'ID_Pelanggan', 'ID_Produk'])
    df = df[df['Qty'] > 0]

    # Parse tanggal & tambah kolom waktu
    df['Tanggal_PO']  = pd.to_datetime(df['Tanggal_PO'], errors='coerce')
    df['Bulan']       = df['Tanggal_PO'].dt.month
    df['Nama_Bulan']  = df['Bulan'].map(MONTH_NAMES)
    df['Tahun']       = df['Tanggal_PO'].dt.year
    df['Kuartal']     = df['Tanggal_PO'].dt.quarter.map(
        {1: 'Q1', 2: 'Q2', 3: 'Q3', 4: 'Q4'}
    )

    # Normalisasi tipe data
    df['Qty']         = pd.to_numeric(df['Qty'], errors='coerce').fillna(0)
    df['Harga_Satuan']= pd.to_numeric(df['Harga_Satuan'], errors='coerce').fillna(0)
    df['Total_Harga'] = pd.to_numeric(df['Total_Harga'], errors='coerce').fillna(0)
    df['Modal_Unit']  = pd.to_numeric(df['Modal_Unit'], errors='coerce').fillna(0)
    df['Kategori']    = df['Kategori'].astype(str)

    print(f"   ✅ Total transaksi valid: {len(df):,} baris")
    print(f"   📅 Periode: {df['Tanggal_PO'].min().strftime('%d %b %Y')} s/d "
          f"{df['Tanggal_PO'].max().strftime('%d %b %Y')}")
    return df


# ─── STEP 3: HITUNG TLC DAN METRIK PROFITABILITAS ────────────────────────────
def compute_profitabilitas(df_trans, df_barang, df_logistik):
    print("\n🧮 Menghitung TLC, Gross Profit, dan GPM...")

    # Join dengan Master Barang → dapat Karung_Ukuran_60Kg
    df_barang_join = df_barang[['ID_Produk', 'Karung_Ukuran_60Kg', 'Berat_Asli']]
    df = df_trans.merge(df_barang_join, on='ID_Produk', how='left')

    # Join dengan Master Logistik → dapat Estimasi_Biaya & Satuan_Biaya
    df_log_join = df_logistik[['Kota_Logistik', 'Estimasi_Biaya', 'Satuan_Biaya',
                               'Penanggung_Biaya', 'Nama_Ekspedisi']].rename(
        columns={'Kota_Logistik': 'Kota'}
    )
    df = df.merge(df_log_join, on='Kota', how='left')
    df['Estimasi_Biaya']     = pd.to_numeric(df['Estimasi_Biaya'], errors='coerce').fillna(0)
    df['Karung_Ukuran_60Kg'] = df['Karung_Ukuran_60Kg'].fillna(1)  # fallback aman

    # ── Hitung Biaya Logistik per Unit ──────────────────────────────────────
    df['Biaya_Logistik_Per_Unit'] = 0.0

    # Kasus 1: per karung 60kg → Estimasi_Biaya / jumlah_unit_per_karung
    mask_karung = df['Satuan_Biaya'].str.lower().str.contains('karung', na=False)
    df.loc[mask_karung, 'Biaya_Logistik_Per_Unit'] = (
        df.loc[mask_karung, 'Estimasi_Biaya'] /
        df.loc[mask_karung, 'Karung_Ukuran_60Kg']
    )

    # Kasus 2: per pengiriman → distribusi ke semua unit dalam 1 PO
    mask_pengiriman = df['Satuan_Biaya'].str.lower().str.contains('pengiriman', na=False)
    if mask_pengiriman.any():
        total_qty_per_po = df[mask_pengiriman].groupby('Nomor_PO')['Qty'].transform('sum')
        total_qty_per_po = total_qty_per_po.replace(0, 1)  # hindari division by zero
        df.loc[mask_pengiriman, 'Biaya_Logistik_Per_Unit'] = (
            df.loc[mask_pengiriman, 'Estimasi_Biaya'] / total_qty_per_po
        )

    # ── BOP (Listrik) — set 0, siap diisi jika data tersedia ───────────────
    # TODO: Tambahkan data BOP/Listrik di sini jika sudah ada
    df['BOP_Per_Unit'] = 0.0

    # ── Rumus Utama ──────────────────────────────────────────────────────────
    # TLC  = Modal_Unit (HPP Parsial) + BOP + Biaya Logistik
    df['TLC']                = df['Modal_Unit'] + df['BOP_Per_Unit'] + df['Biaya_Logistik_Per_Unit']

    # Gross Profit per unit & total
    df['Gross_Profit_Unit']  = df['Harga_Satuan'] - df['TLC']
    df['Gross_Profit_Total'] = df['Gross_Profit_Unit'] * df['Qty']

    # GPM (%) = (Harga_Jual - TLC) / Harga_Jual × 100
    df['GPM_Pct'] = np.where(
        df['Harga_Satuan'] > 0,
        (df['Gross_Profit_Unit'] / df['Harga_Satuan']) * 100,
        0.0
    ).round(2)

    # Total Revenue dan Total TLC per baris
    df['Revenue']            = df['Total_Harga']
    df['Total_TLC']          = df['TLC'] * df['Qty']

    # Total Profit (untuk ranking)
    df['Total_Profit']       = df['Gross_Profit_Total']

    # Popularitas per wilayah (dihitung saat query di dashboard)
    print(f"   ✅ Selesai. Sample metrik (5 baris pertama):")
    print(df[['ID_Produk', 'Kota', 'Modal_Unit', 'Biaya_Logistik_Per_Unit',
              'TLC', 'GPM_Pct']].head().to_string(index=False))

    return df


# ─── STEP 4: SIMPAN KE SQLITE ────────────────────────────────────────────────
def save_to_sqlite(df_analisis, df_barang, df_logistik, df_pelanggan):
    print(f"\n💾 Menyimpan ke database: {DB_PATH}")

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)

    # Tabel utama: hasil analisis + transaksi
    df_analisis['Tanggal_PO'] = df_analisis['Tanggal_PO'].astype(str)
    df_analisis.to_sql('transaksi_analisis', conn, if_exists='replace', index=False)

    # Tabel master
    df_barang.to_sql('master_barang', conn, if_exists='replace', index=False)
    df_logistik.to_sql('master_logistik', conn, if_exists='replace', index=False)
    df_pelanggan.to_sql('master_pelanggan', conn, if_exists='replace', index=False)

    # Buat index untuk performa query
    conn.execute("CREATE INDEX IF NOT EXISTS idx_wilayah  ON transaksi_analisis(Wilayah)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_bulan    ON transaksi_analisis(Bulan)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_produk   ON transaksi_analisis(ID_Produk)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_pelanggan ON transaksi_analisis(ID_Pelanggan)")

    # ── View: Profitabilitas Regional (agregat per Provinsi) ────────────────
    conn.execute("""
        CREATE VIEW IF NOT EXISTS v_profitabilitas_regional AS
        SELECT
            Wilayah,
            Provinsi,
            Bulan,
            Nama_Bulan,
            Kuartal,
            COUNT(DISTINCT Nomor_PO)        AS Jumlah_PO,
            SUM(Qty)                         AS Total_Volume,
            SUM(Revenue)                     AS Total_Revenue,
            SUM(Total_TLC)                   AS Total_TLC,
            SUM(Gross_Profit_Total)          AS Total_Gross_Profit,
            AVG(GPM_Pct)                     AS Avg_GPM,
            AVG(Biaya_Logistik_Per_Unit)     AS Avg_Biaya_Logistik_Per_Unit
        FROM transaksi_analisis
        WHERE Wilayah IS NOT NULL
        GROUP BY Wilayah, Provinsi, Bulan, Nama_Bulan, Kuartal
    """)

    # ── View: Product-Region Fit ─────────────────────────────────────────────
    conn.execute("""
        CREATE VIEW IF NOT EXISTS v_product_region_fit AS
        SELECT
            Wilayah,
            Provinsi,
            ID_Produk,
            Nama_Model,
            Kategori,
            Bulan,
            Nama_Bulan,
            SUM(Qty)                AS Total_Volume,
            SUM(Revenue)            AS Total_Revenue,
            SUM(Total_TLC)          AS Total_TLC,
            SUM(Gross_Profit_Total) AS Total_Gross_Profit,
            AVG(GPM_Pct)            AS Avg_GPM,
            AVG(TLC)                AS Avg_TLC,
            AVG(Harga_Satuan)       AS Avg_Harga_Jual
        FROM transaksi_analisis
        WHERE Wilayah IS NOT NULL
        GROUP BY Wilayah, Provinsi, ID_Produk, Nama_Model, Kategori, Bulan, Nama_Bulan
    """)

    # ── View: Customer Loyalty ───────────────────────────────────────────────
    conn.execute("""
        CREATE VIEW IF NOT EXISTS v_customer_loyalty AS
        SELECT
            ID_Pelanggan,
            Nama_Pelanggan,
            Wilayah,
            Provinsi,
            Kota,
            COUNT(DISTINCT Nomor_PO)   AS Total_Order,
            SUM(Qty)                   AS Total_Volume,
            SUM(Revenue)               AS Total_Revenue,
            SUM(Gross_Profit_Total)    AS Total_Gross_Profit,
            AVG(GPM_Pct)               AS Avg_GPM,
            GROUP_CONCAT(DISTINCT Nama_Model) AS Produk_Favorit
        FROM transaksi_analisis
        WHERE Wilayah IS NOT NULL
        GROUP BY ID_Pelanggan, Nama_Pelanggan, Wilayah, Provinsi, Kota
        ORDER BY Total_Revenue DESC
    """)

    conn.commit()
    conn.close()

    size_kb = os.path.getsize(DB_PATH) / 1024
    print(f"   ✅ Database berhasil dibuat! Ukuran: {size_kb:.1f} KB")
    print(f"\n✨ SELESAI! File '{DB_PATH}' siap digunakan.")
    print("   Sekarang jalankan: streamlit run app.py")


# ─── MAIN ────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("=" * 60)
    print("  SETUP DATABASE - Dashboard BI Pelampung 2025")
    print("=" * 60)

    df_barang, df_logistik, df_pelanggan = load_master_tables()
    df_trans                             = load_transaksi()
    df_analisis                          = compute_profitabilitas(df_trans, df_barang, df_logistik)
    save_to_sqlite(df_analisis, df_barang, df_logistik, df_pelanggan)
