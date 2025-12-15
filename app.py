import streamlit as st
import pandas as pd
from pymongo import MongoClient
from datetime import datetime
import time

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Kas Kosan", page_icon="🏦", layout="wide")

# --- KONFIGURASI PENTING ---
TARGET_PER_ORANG = 50000  
TAHUN_MULAI = 2026  
BULAN_MULAI = 2     

# --- KONEKSI MONGODB ---
@st.cache_resource
def init_connection():
    return MongoClient(st.secrets["mongo"]["uri"])

try:
    client = init_connection()
    db = client.kas_kos_pro 
    col_users = db.users
    col_transaksi = db.transaksi
    col_pengeluaran = db.pengeluaran # COLLECTION BARU KHUSUS PENGELUARAN
except Exception as e:
    st.error(f"Koneksi Database Gagal: {e}")
    st.stop()

# --- INISIALISASI USER (Hanya jalan jika database user kosong) ---
if col_users.count_documents({}) == 0:
    users_awal = [
        {"username": "Aqil", "password": "123", "role": "admin"}, # Cuma Aqil yang Admin
        {"username": "Wildan", "password": "123", "role": "member"},
        {"username": "Diki", "password": "123", "role": "member"},
        {"username": "Raka", "password": "123", "role": "member"},
        {"username": "Ucup", "password": "123", "role": "member"},
    ]
    col_users.insert_many(users_awal)
    print("User berhasil dibuat!")

# --- FUNGSI UTILITIES ---
def check_login(username, password):
    return col_users.find_one({"username": username, "password": password})

def hitung_bulan_berjalan():
    now = datetime.now()
    if now.year < TAHUN_MULAI or (now.year == TAHUN_MULAI and now.month < BULAN_MULAI):
        return 0 
    jumlah_bulan = (now.year - TAHUN_MULAI) * 12 + (now.month - BULAN_MULAI) + 1
    return max(0, jumlah_bulan)

# --- HALAMAN LOGIN ---
def login_page():
    st.markdown("<h1 style='text-align: center;'>🔐 Login gak nih?</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        with st.form("login_form"):
            users_db = col_users.distinct("username")
            pilihan_user = users_db if users_db else ["Database Kosong"]
            
            username = st.selectbox("Siapa kamu?", pilihan_user)
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Masuk", use_container_width=True)
            
            if submit:
                user = check_login(username, password)
                if user:
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = user['username']
                    st.session_state['role'] = user['role'] # Simpan role (admin/member)
                    st.success("Akses Diterima!")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("Password salah!")

# --- HALAMAN UTAMA (DASHBOARD) ---
def dashboard():
    user_now = st.session_state['username']
    user_role = st.session_state.get('role', 'member') # Ambil role user
    
    bulan_berjalan = hitung_bulan_berjalan()
    wajib_bayar_total = bulan_berjalan * TARGET_PER_ORANG

    # --- SIDEBAR ---
    st.sidebar.title(f"Halo, {user_now} Ganteng 💦💦🥵")
    st.sidebar.caption(f"Status: {user_role.upper()}") # Tampilkan status Admin/Member
    
    if bulan_berjalan > 0:
        st.sidebar.info(f"📅 Bulan ke-{bulan_berjalan}")
    else:
        st.sidebar.warning("⏳ Sistem belum mulai")

    st.sidebar.markdown("---")
    
    # DAFTAR MENU (Dinamis berdasarkan Role)
    menu_options = ["📝 Input Data", "👤 Status Saya(jomblo)", "📊 Laporan Keuangan", "⚙️ Ganti Password"]
    
    # Menu Rahasia Admin disisipkan
    if user_role == "admin":
        menu_options.insert(1, "💦 Catat Pengeluaran")

    menu = st.sidebar.radio("Menu", menu_options)
    
    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state['logged_in'] = False
        st.rerun()

    # --- LOGIKA MENU ---
    
    # 1. INPUT PEMBAYARAN (Semua Bisa)
    if menu == "📝 Input Data":
        st.title("📝 Setoran")
        with st.form("form_input"):
            nominal = st.number_input("Nominal (Rp)", min_value=5000, step=5000)
            keterangan = st.text_input("Catatan", placeholder="Bayar apa nich")
            submitted = st.form_submit_button("Kirim Data (bener gak nih🤨🤨)", use_container_width=True)
            
            if submitted:
                data = {
                    "username": user_now,
                    "nominal": nominal,
                    "keterangan": keterangan if keterangan else "-",
                    "tanggal": datetime.now(),
                    "periode": datetime.now().strftime("%Y-%m")
                }
                col_transaksi.insert_one(data)
                st.balloons()
                st.success("Done mas!")
                time.sleep(1)
                st.rerun()

    # 2. CATAT PENGELUARAN (HANYA ADMIN AQIL)
    elif menu == "💦 Catat Pengeluaran":
        st.title("💦: Catat Pengeluaran")
        st.warning("Ini buat ngedit pengeluaran.")
        
        with st.form("form_keluar"):
            item = st.text_input("Beli Apa?", placeholder="Beli apa ya?")
            biaya = st.number_input("Biaya (Rp)", min_value=1000, step=1000)
            tanggal_beli = st.date_input("Tanggal Pembelian", value=datetime.now())
            submit_keluar = st.form_submit_button("Catat Pengeluaran 💦", use_container_width=True)
            
            if submit_keluar:
                data_keluar = {
                    "admin": user_now,
                    "item": item,
                    "nominal": biaya,
                    "tanggal": datetime.combine(tanggal_beli, datetime.min.time()),
                    "tanggal_input": datetime.now()
                }
                col_pengeluaran.insert_one(data_keluar)
                st.success(f"Tercatat: {item} seharga Rp {biaya:,.0f}")
                time.sleep(1)
                st.rerun()

    # 3. STATUS SAYA (Pribadi)
    elif menu == "👤 Status Saya(jomblo)":
        st.title("👤 dompet Saya")
        my_tx = list(col_transaksi.find({"username": user_now}))
        df = pd.DataFrame(my_tx)
        
        total_setor = df['nominal'].sum() if not df.empty else 0
        kurang = wajib_bayar_total - total_setor
        
        c1, c2 = st.columns(2)
        c1.metric("Total Kewajiban", f"Rp {wajib_bayar_total:,.0f}")
        c2.metric("Sudah Kamu Bayar", f"Rp {total_setor:,.0f}")
        
        if bulan_berjalan > 0:
            if kurang > 0:
                st.error(f"⚠️ HUTANG: Rp {kurang:,.0f}")
            else:
                st.success("✅ LUNAS")
        
        st.caption("Riwayat Setoran:")
        if not df.empty:
            if 'keterangan' not in df.columns: df['keterangan'] = "-"
            if 'tanggal' not in df.columns: df['tanggal'] = datetime.now()
            st.dataframe(df[['tanggal', 'nominal', 'keterangan']].sort_values('tanggal', ascending=False), use_container_width=True)

    # 4. LAPORAN KEUANGAN & TRANSPARANSI (Update Besar)
    elif menu == "📊 Laporan Keuangan":
        st.title("📊 Laporan Arus Kas")
        
        # Ambil Data Masuk & Keluar
        all_masuk = list(col_transaksi.find())
        all_keluar = list(col_pengeluaran.find())
        
        df_masuk = pd.DataFrame(all_masuk)
        df_keluar = pd.DataFrame(all_keluar)
        
        # Hitung Angka Penting
        total_masuk = df_masuk['nominal'].sum() if not df_masuk.empty else 0
        total_keluar = df_keluar['nominal'].sum() if not df_keluar.empty else 0
        saldo_akhir = total_masuk - total_keluar
        
        # Tampilkan Scoreboard
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Pemasukan", f"Rp {total_masuk:,.0f}")
        col2.metric("Total Pengeluaran", f"Rp {total_keluar:,.0f}", delta_color="inverse")
        col3.metric("💰 SALDO SAAT INI", f"Rp {saldo_akhir:,.0f}", delta=f"{'Aman' if saldo_akhir > 0 else 'Bahaya'}")
        
        st.divider()
        
        # Tabulasi Laporan
        tab1, tab2 = st.tabs(["📋 Status Anomali", "🧾 Riwayat Pengeluaran"])
        
        with tab1:
            st.subheader("Siapa yang nunggak?")
            all_users = col_users.distinct("username")
            laporan = []
            for u in all_users:
                bayar = df_masuk[df_masuk['username'] == u]['nominal'].sum() if not df_masuk.empty else 0
                hutang = wajib_bayar_total - bayar
                status = "✅ LUNAS" if hutang <= 0 else "❌ NUNGGAK"
                if bulan_berjalan == 0: status = "-"
                
                laporan.append({
                    "Nama": u,
                    "Total Setor": f"Rp {bayar:,.0f}",
                    "Hutang": f"Rp {max(0, hutang):,.0f}",
                    "Status": status,
                })
            st.dataframe(pd.DataFrame(laporan), use_container_width=True)
            
        with tab2:
            st.subheader("Uang dipakai buat apa aja?")
            if not df_keluar.empty:
                # Rapikan tabel
                tabel_keluar = df_keluar[['tanggal', 'item', 'nominal', 'admin']].copy()
                tabel_keluar = tabel_keluar.sort_values('tanggal', ascending=False)
                st.dataframe(tabel_keluar, use_container_width=True)
            else:
                st.info("Belum ada pengeluaran (buat muncak gak sih?)")

    # 5. GANTI PASSWORD
    elif menu == "⚙️ Ganti Password":
        st.header("Ganti Password")
        p_baru = st.text_input("Password Baru", type="password")
        if st.button("Simpan"):
            col_users.update_one({"username": user_now}, {"$set": {"password": p_baru}})
            st.success("Password diganti!")

# --- MAIN ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if st.session_state['logged_in']:
    dashboard()
else:
    login_page()