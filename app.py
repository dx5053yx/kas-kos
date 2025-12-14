import streamlit as st
import pandas as pd
from pymongo import MongoClient
from datetime import datetime

#Konfig
st.set_page_config(page_title="Kas-Kos jasmin3", page_icon="🍃")

#mongodb
@st.cache_resource
def init_connection():
    # Mengambil URI dari secrets.toml
    return MongoClient(st.secrets["mongo"]["uri"])

try:
    client = init_connection()
    #Nama Database
    db = client.kas_db
    collection = db.transaksi
    #Tes koneksi
    client.server_info()
except Exception as e:
    st.error(f"Gagal konek ke MongoDB: {e}")
    st.stop()

#titel
st.title("Kas-KOS jasmin")
st.caption("anjai canggih")
st.markdown("---")

#input data
st.subheader("➕ Input Pembayaran")

with st.form("form_bayar", clear_on_submit=True):
    nama = st.selectbox("Nama", ["Aqil", "Ucup", "Wildan", "Diki", "Raka"])
    nominal = st.number_input("Jumlah (Rp)", min_value=1000, step=1000)
    keterangan = st.text_input("Keterangan")
    
    submitted = st.form_submit_button("Simpan Data")

    if submitted:
        # Siapkan data dalam bentuk Dictionary (JSON)
        data_baru = {
            "tanggal": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "nama": nama,
            "nominal": nominal,
            "keterangan": keterangan
        }
        
        # Insert ke MongoDB
        collection.insert_one(data_baru)
        st.success("Data berhasil masuk ke Cloud Database!")
        st.rerun()

# 2. MENAMPILKAN DATA (READ)
st.subheader("📊 Laporan Kas")

# Ambil semua data dari MongoDB
cursor = collection.find()
data_list = list(cursor)

if data_list:
    df = pd.DataFrame(data_list)
    
    # MongoDB otomatis nambahin kolom '_id' yang isinya kode aneh, kita buang aja biar rapi
    if '_id' in df.columns:
        df = df.drop(columns=['_id'])
    
    # Hitung total
    total_uang = df['nominal'].sum()
    st.metric(label="Total Saldo", value=f"Rp {total_uang:,.0f}")
    
    # Tampilkan tabel (urutkan tanggal desc)
    st.dataframe(df.sort_values(by="tanggal", ascending=False), use_container_width=True)
else:
    st.info("Database masih kosong. Yuk bayar kas!")