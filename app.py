import streamlit as st
import pandas as pd
from pymongo import MongoClient
from datetime import datetime
import time

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Sistem Kas Pro", page_icon="🔐")

# --- KONEKSI MONGODB ---
@st.cache_resource
def init_connection():
    return MongoClient(st.secrets["mongo"]["uri"])

client = init_connection()
db = client.kas_kos_pro  # Kita pakai nama database baru biar bersih
col_users = db.users
col_transaksi = db.transaksi

# --- FUNGSI AUTHENTICATION (LOGIN) ---
def check_login(username, password):
    user = col_users.find_one({"username": username, "password": password})
    return user

# --- INISIALISASI USER (Hanya dijalankan sekali di awal) ---
# Biar database user gak kosong, kita buat akun default otomatis
if col_users.count_documents({}) == 0:
    users_awal = [
        {"username": "Aqil", "password": "123", "role": "admin"},
        {"username": "Daffa", "password": "123", "role": "member"},
        {"username": "Naufal", "password": "123", "role": "member"},
        {"username": "Budi", "password": "123", "role": "member"},
        {"username": "Siti", "password": "123", "role": "member"},
    ]
    col_users.insert_many(users_awal)
    print("User default berhasil dibuat!")

# --- HALAMAN LOGIN ---
def login_page():
    st.title("🔐 Login Kas Kosan")
    
    with st.form("login_form"):
        # Dropdown biar gak typo nulis nama
        users_db = col_users.distinct("username")
        username = st.selectbox("Pilih Nama Kamu", users_db)
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Masuk")
        
        if submit:
            user = check_login(username, password)
            if user:
                # SIMPAN SESI LOGIN
                st.session_state['logged_in'] = True
                st.session_state['username'] = user['username']
                st.session_state['role'] = user['role']
                st.success("Login Berhasil!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Password salah bro!")

# --- HALAMAN UTAMA (DASHBOARD) ---
def dashboard():
    user_now = st.session_state['username']
    
    # Sidebar untuk Menu & Logout
    st.sidebar.title(f"Halo, {user_now} 👋")
    menu = st.sidebar.radio("Menu", ["Dashboard Kas", "Ganti Password"])
    
    if st.sidebar.button("Logout"):
        st.session_state['logged_in'] = False
        st.rerun()

    # LOGIKA DASHBOARD
    if menu == "Dashboard Kas":
        st.title("💰 Dashboard Kas Bulanan")
        
        # 1. FILTER WAKTU (Otomatis deteksi bulan ini)
        bulan_ini = datetime.now().strftime("%Y-%m") # Contoh: "2023-12"
        st.info(f"📅 Periode Aktif: **{bulan_ini}**")

        # Target Kas (Bisa dihardcode atau ambil dari db)
        TARGET_PER_ORANG = 50000 
        
        # 2. INPUT BAYAR
        with st.expander("💸 Bayar Kas Disini", expanded=True):
            with st.form("bayar"):
                nominal = st.number_input("Jumlah Bayar", min_value=10000, step=5000)
                submit_bayar = st.form_submit_button("Kirim Uang")
                
                if submit_bayar:
                    data = {
                        "username": user_now,
                        "nominal": nominal,
                        "tanggal": datetime.now(),      # Untuk sorting detail
                        "periode": bulan_ini            # KUNCI: Untuk filtering bulanan
                    }
                    col_transaksi.insert_one(data)
                    st.success("Berhasil bayar! Bendahara senang.")
                    time.sleep(1)
                    st.rerun()

        st.markdown("---")

        # 3. LOGIKA REKAP (AGGREGATION)
        # Ambil semua data periode ini
        semua_transaksi = list(col_transaksi.find({"periode": bulan_ini}))
        df = pd.DataFrame(semua_transaksi)

        col1, col2 = st.columns(2)
        
        # Hitung Total Kas Bulan Ini (Semua Anak)
        if not df.empty:
            total_bulan_ini = df['nominal'].sum()
            # Hitung Total Kas Pribadi (User yg login)
            df_pribadi = df[df['username'] == user_now]
            total_pribadi = df_pribadi['nominal'].sum()
        else:
            total_bulan_ini = 0
            total_pribadi = 0

        with col1:
            st.metric("Total Terkumpul (Semua)", f"Rp {total_bulan_ini:,.0f}")
        with col2:
            # Logic Status Lunas/Belum
            kurang = TARGET_PER_ORANG - total_pribadi
            if kurang <= 0:
                st.metric("Status Kamu", "LUNAS ✅", delta="Aman")
            else:
                st.metric("Status Kamu", f"Kurang Rp {kurang:,.0f}", delta="-Belum Lunas", delta_color="inverse")

        # 4. TABEL PEMBAYARAN SEMUA ORANG
        st.subheader("Siapa yang sudah bayar?")
        if not df.empty:
            # Grouping biar kelihatan per anak totalnya berapa
            rekap_anak = df.groupby("username")["nominal"].sum().reset_index()
            rekap_anak['Status'] = rekap_anak['nominal'].apply(lambda x: "✅ Lunas" if x >= TARGET_PER_ORANG else "❌ Belum")
            st.dataframe(rekap_anak, use_container_width=True)
            
            with st.expander("Lihat Detail Riwayat Transaksi"):
                st.dataframe(df[['tanggal', 'username', 'nominal']].sort_values('tanggal', ascending=False))
        else:
            st.warning("Belum ada data bulan ini.")

    # LOGIKA GANTI PASSWORD
    elif menu == "Ganti Password":
        st.subheader("🔐 Ganti Password")
        pass_baru = st.text_input("Password Baru", type="password")
        if st.button("Simpan Password Baru"):
            if len(pass_baru) > 0:
                col_users.update_one(
                    {"username": user_now},
                    {"$set": {"password": pass_baru}}
                )
                st.success("Password berhasil diganti! Jangan lupa ya.")
            else:
                st.error("Password gak boleh kosong.")

# --- ROUTING HALAMAN ---
# Cek apakah user sudah login atau belum
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if st.session_state['logged_in']:
    dashboard()
else:
    login_page()