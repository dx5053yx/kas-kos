import streamlit as st
import pandas as pd
from pymongo import MongoClient
from datetime import datetime
import time

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Sistem Kas Kosan", page_icon="🏦", layout="wide")

# --- KONEKSI MONGODB ---
@st.cache_resource
def init_connection():
    return MongoClient(st.secrets["mongo"]["uri"])

try:
    client = init_connection()
    db = client.kas_kos_pro 
    col_users = db.users
    col_transaksi = db.transaksi
except Exception as e:
    st.error(f"Koneksi Database Gagal: {e}")
    st.stop()

# --- KONFIGURASI TARGET ---
TARGET_PER_ORANG = 50000  # Ubah sesuai kesepakatan

# --- FUNGSI AUTH ---
def check_login(username, password):
    return col_users.find_one({"username": username, "password": password})

# --- HALAMAN LOGIN ---
def login_page():
    st.markdown("<h1 style='text-align: center;'>🔐 Login Bendahara</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        with st.form("login_form"):
            users_db = col_users.distinct("username")
            username = st.selectbox("Siapa kamu?", users_db)
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Masuk", use_container_width=True)
            
            if submit:
                user = check_login(username, password)
                if user:
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = user['username']
                    st.session_state['role'] = user['role']
                    st.success("Akses Diterima!")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("Password salah!")

# --- HALAMAN UTAMA (DASHBOARD) ---
def dashboard():
    user_now = st.session_state['username']
    
    # --- SIDEBAR MENU ---
    st.sidebar.title(f"Hai, {user_now} 👋")
    st.sidebar.markdown("---")
    
    # Opsi Menu Baru
    menu = st.sidebar.radio(
        "Menu Utama", 
        ["📝 Input Bayar", "👤 Riwayat Saya", "📅 Laporan Bulan Ini", "💰 Total Kas Semesta", "⚙️ Ganti Password"]
    )
    
    st.sidebar.markdown("---")
    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state['logged_in'] = False
        st.rerun()

    # --- LOGIKA PER MENU ---

    # 1. INPUT PEMBAYARAN
    if menu == "📝 Input Bayar":
        st.title("📝 Input Pembayaran Kas")
        st.info("Form ini untuk mencatat uang yang masuk.")
        
        with st.form("form_input"):
            nominal = st.number_input("Nominal (Rp)", min_value=10000, step=5000)
            keterangan = st.text_input("Catatan (Opsional)", placeholder="Contoh: Bayar tunggakan bulan lalu")
            submitted = st.form_submit_button("Kirim Uang 💸", use_container_width=True)
            
            if submitted:
                bulan_ini = datetime.now().strftime("%Y-%m")
                data = {
                    "username": user_now,
                    "nominal": nominal,
                    "keterangan": keterangan,
                    "tanggal": datetime.now(),
                    "periode": bulan_ini
                }
                col_transaksi.insert_one(data)
                st.balloons()
                st.success(f"Mantap! Rp {nominal:,.0f} berhasil disimpan.")

    # 2. RIWAYAT SAYA
    elif menu == "👤 Riwayat Saya":
        st.title("👤 Riwayat Transaksi Saya")
        
        # Ambil data HANYA milik user yang login
        data_saya = list(col_transaksi.find({"username": user_now}))
        
        if data_saya:
            df = pd.DataFrame(data_saya)
    
             # --- TAMBAHAN KODE ANTI ERROR ---
                # Jika kolom belum ada, kita isi manual dengan strip "-"
            if 'keterangan' not in df.columns:
                df['keterangan'] = "-"
            if 'tanggal' not in df.columns:
                df['tanggal'] = datetime.now() # Atau tanggal default
            if 'nominal' not in df.columns:
                df['nominal'] = 0


    #panggil kodenya
            st.dataframe(
                df[['tanggal', 'nominal', 'keterangan']].sort_values('tanggal', ascending=False),
                use_container_width=True
            )
        else:
            st.warning("Kamu belum pernah bayar kas sama sekali. Parah!")

    # 3. LAPORAN BULAN INI (TARGET & REALISASI)
    elif menu == "📅 Laporan Bulan Ini":
        bulan_ini_str = datetime.now().strftime("%B %Y") # Contoh: December 2025
        kode_bulan = datetime.now().strftime("%Y-%m")
        
        st.title(f"📅 Laporan: {bulan_ini_str}")
        
        # Ambil data bulan ini
        data_bulan = list(col_transaksi.find({"periode": kode_bulan}))
        df = pd.DataFrame(data_bulan)
        
        # Hitung Target
        jumlah_anak = col_users.count_documents({}) # Hitung jumlah user otomatis
        target_total = jumlah_anak * TARGET_PER_ORANG
        
        if not df.empty:
            realisasi_total = df['nominal'].sum()
        else:
            realisasi_total = 0
            
        # Tampilkan Metric Besar
        col1, col2, col3 = st.columns(3)
        col1.metric("Target Bulan Ini", f"Rp {target_total:,.0f}", help=f"{jumlah_anak} orang x Rp {TARGET_PER_ORANG}")
        col2.metric("Terkumpul", f"Rp {realisasi_total:,.0f}")
        col3.metric("Sisa Target", f"Rp {max(0, target_total - realisasi_total):,.0f}")
        
        # Progress Bar
        persen = min(realisasi_total / target_total, 1.0) if target_total > 0 else 0
        st.progress(persen, text=f"Progress Terkumpul: {int(persen*100)}%")
        
        st.markdown("---")
        st.subheader("📋 Siapa yang belum lunas?")
        
        # Logic rumit dikit: Cek status per anak
        all_users = col_users.distinct("username")
        status_list = []
        
        for u in all_users:
            # Berapa yang si U ini bayar bulan ini?
            if not df.empty:
                bayar_u = df[df['username'] == u]['nominal'].sum()
            else:
                bayar_u = 0
            
            status = "✅ LUNAS" if bayar_u >= TARGET_PER_ORANG else "❌ KURANG"
            kekurangan = max(0, TARGET_PER_ORANG - bayar_u)
            
            status_list.append({
                "Nama": u,
                "Sudah Bayar": f"Rp {bayar_u:,.0f}",
                "Kekurangan": f"Rp {kekurangan:,.0f}",
                "Status": status
            })
            
        st.dataframe(pd.DataFrame(status_list), use_container_width=True)

    # 4. TOTAL KAS SEMESTA (KESELURUHAN)
    elif menu == "💰 Total Kas Semesta":
        st.title("💰 Brankas Utama")
        st.caption("Total akumulasi uang kas dari awal dunia terbentuk.")
        
        all_data = list(col_transaksi.find())
        if all_data:
            df_all = pd.DataFrame(all_data)
            grand_total = df_all['nominal'].sum()
            
            # Tampilan Angka Besar
            st.markdown(f"<h1 style='font-size: 72px; color: #4CAF50;'>Rp {grand_total:,.0f}</h1>", unsafe_allow_html=True)
            
            st.markdown("### 📈 Grafik Pertumbuhan Kas")
            # Bikin grafik sederhana per tanggal
            chart_data = df_all[['tanggal', 'nominal']].copy()
            chart_data['tanggal'] = pd.to_datetime(chart_data['tanggal']).dt.date
            # Group by tanggal biar rapi
            daily_data = chart_data.groupby('tanggal').sum()
            # Kumulatif (biar grafiknya naik terus)
            daily_data['Total Akumulasi'] = daily_data['nominal'].cumsum()
            
            st.line_chart(daily_data['Total Akumulasi'])
            
        else:
            st.info("Belum ada uang sepeserpun di database.")

    # 5. GANTI PASSWORD
    elif menu == "⚙️ Ganti Password":
        st.title("🔐 Ganti Password")
        pass_baru = st.text_input("Password Baru", type="password")
        if st.button("Simpan"):
            if pass_baru:
                col_users.update_one({"username": user_now}, {"$set": {"password": pass_baru}})
                st.success("Password diperbarui!")
            else:
                st.warning("Isi dulu passwordnya.")

# --- MAIN LOOP ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if st.session_state['logged_in']:
    dashboard()
else:
    login_page()