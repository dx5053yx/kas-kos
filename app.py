import streamlit as st
import pandas as pd
from pymongo import MongoClient
from datetime import datetime
import time

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Sistem Kas Kosan", page_icon="🏦", layout="wide")

# --- KONFIGURASI PENTING (EDIT DISINI) ---
TARGET_PER_ORANG = 50000  
# Tentukan kapan kas dimulai (Tahun, Bulan). 
# Contoh: Mulai Januari 2025, maka isikan 2025 dan 1.
TAHUN_MULAI = 2025
BULAN_MULAI = 1 

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

# --- FUNGSI AUTH ---
def check_login(username, password):
    return col_users.find_one({"username": username, "password": password})

# --- FUNGSI HITUNG BULAN BERJALAN ---
def hitung_bulan_berjalan():
    now = datetime.now()
    # Rumus selisih bulan
    jumlah_bulan = (now.year - TAHUN_MULAI) * 12 + (now.month - BULAN_MULAI) + 1
    return max(1, jumlah_bulan) # Minimal 1 bulan

# --- HALAMAN LOGIN ---
def login_page():
    st.markdown("<h1 style='text-align: center;'>🔐 Login Bendahara</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        with st.form("login_form"):
            try:
                users_db = col_users.distinct("username")
            except:
                users_db = []
            
            username = st.selectbox("Siapa kamu?", users_db if users_db else ["Belum ada user"])
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
    
    # Hitung data kumulatif global
    bulan_berjalan = hitung_bulan_berjalan()
    wajib_bayar_total = bulan_berjalan * TARGET_PER_ORANG

    # --- SIDEBAR ---
    st.sidebar.title(f"Hai, {user_now} 👋")
    st.sidebar.caption(f"📅 Kas berjalan: {bulan_berjalan} Bulan")
    st.sidebar.markdown("---")
    
    menu = st.sidebar.radio(
        "Menu Utama", 
        ["📝 Input Bayar", "👤 Status Keuangan Saya", "📋 Laporan & Tunggakan", "💰 Brankas Utama", "⚙️ Ganti Password"]
    )
    
    st.sidebar.markdown("---")
    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state['logged_in'] = False
        st.rerun()

    # --- MENU 1: INPUT ---
    if menu == "📝 Input Bayar":
        st.title("📝 Input Pembayaran")
        
        with st.form("form_input"):
            nominal = st.number_input("Nominal (Rp)", min_value=10000, step=5000)
            keterangan = st.text_input("Catatan", placeholder="Bayar kas bulan ini...")
            submitted = st.form_submit_button("Kirim Uang 💸", use_container_width=True)
            
            if submitted:
                bulan_ini = datetime.now().strftime("%Y-%m")
                data = {
                    "username": user_now,
                    "nominal": nominal,
                    "keterangan": keterangan if keterangan else "-",
                    "tanggal": datetime.now(),
                    "periode": bulan_ini
                }
                col_transaksi.insert_one(data)
                st.balloons()
                st.success(f"Diterima! Rp {nominal:,.0f} berhasil masuk database.")
                time.sleep(1)
                st.rerun()

    # --- MENU 2: STATUS KEUANGAN SAYA ---
    elif menu == "👤 Status Keuangan Saya":
        st.title("👤 Dompet Saya")
        
        # Hitung Keuangan Pribadi
        my_tx = list(col_transaksi.find({"username": user_now}))
        df = pd.DataFrame(my_tx)
        
        total_setor = df['nominal'].sum() if not df.empty else 0
        kurang_bayar = wajib_bayar_total - total_setor
        
        # Tampilkan Status dengan Warna
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Seharusnya Total Setor", f"Rp {wajib_bayar_total:,.0f}", help=f"{bulan_berjalan} bulan x {TARGET_PER_ORANG}")
        with col2:
            st.metric("Total Kamu Setor", f"Rp {total_setor:,.0f}")
        
        st.divider()
        
        if kurang_bayar > 0:
            st.error(f"⚠️ KAMU MASIH PUNYA HUTANG: Rp {kurang_bayar:,.0f}")
            st.info(f"Target bulan ini ({TARGET_PER_ORANG:,.0f}) + Tunggakan ({kurang_bayar - TARGET_PER_ORANG:,.0f})")
        elif kurang_bayar == 0:
            st.success("✅ STATUS: LUNAS. Terima kasih orang baik!")
        else:
            st.success(f"🎉 STATUS: DEPOSIT (Lebih Rp {abs(kurang_bayar):,.0f})")
            st.caption("Kamu bayar lebih, mantap! Bisa buat bulan depan.")

        # Riwayat
        st.subheader("Riwayat Transfer")
        if not df.empty:
            # Handle missing columns error
            if 'keterangan' not in df.columns: df['keterangan'] = "-"
            if 'tanggal' not in df.columns: df['tanggal'] = datetime.now()
            
            st.dataframe(
                df[['tanggal', 'nominal', 'keterangan']].sort_values('tanggal', ascending=False),
                use_container_width=True
            )

    # --- MENU 3: LAPORAN (CORE FEATURE) ---
    elif menu == "📋 Laporan & Tunggakan":
        st.title("📋 Laporan Status Member")
        st.caption(f"Posisi Keuangan per Bulan ke-{bulan_berjalan} (Sejak Mulai).")

        # Ambil semua data
        all_tx = list(col_transaksi.find())
        df_all = pd.DataFrame(all_tx)
        
        # Ambil semua user
        all_users = col_users.distinct("username")
        
        laporan_list = []
        
        for u in all_users:
            if not df_all.empty:
                # Hitung total bayar per user
                bayar_user = df_all[df_all['username'] == u]['nominal'].sum()
            else:
                bayar_user = 0
            
            hutang = wajib_bayar_total - bayar_user
            
            # Tentukan Status Text
            if hutang > 0:
                status_text = "❌ NUNGGAK"
            elif hutang == 0:
                status_text = "✅ LUNAS"
            else:
                status_text = "💎 DEPOSIT"
                
            laporan_list.append({
                "Nama": u,
                "Wajib Setor (Total)": f"Rp {wajib_bayar_total:,.0f}",
                "Sudah Setor": f"Rp {bayar_user:,.0f}",
                "Tagihan / Hutang": f"Rp {max(0, hutang):,.0f}", # Max 0 biar gak minus tampilannya
                "Status": status_text
            })
            
        # Tampilkan Tabel
        df_laporan = pd.DataFrame(laporan_list)
        st.dataframe(df_laporan, use_container_width=True)
        
        # Highlight Total Hutang
        total_hutang_semua = (len(all_users) * wajib_bayar_total) - df_all['nominal'].sum() if not df_all.empty else 0
        if total_hutang_semua > 0:
            st.warning(f"Masih ada total tunggakan anak-anak sebesar: Rp {total_hutang_semua:,.0f}")

    # --- MENU 4: BRANKAS ---
    elif menu == "💰 Brankas Utama":
        st.title("💰 Uang Kas Terkumpul")
        
        all_data = list(col_transaksi.find())
        if all_data:
            df = pd.DataFrame(all_data)
            total_uang = df['nominal'].sum()
            st.markdown(f"<h1 style='font-size: 60px; color: #4CAF50;'>Rp {total_uang:,.0f}</h1>", unsafe_allow_html=True)
            
            # Grafik
            if 'tanggal' in df.columns:
                chart_data = df[['tanggal', 'nominal']].copy()
                chart_data['tanggal'] = pd.to_datetime(chart_data['tanggal']).dt.date
                daily = chart_data.groupby('tanggal').sum().cumsum()
                st.area_chart(daily)
        else:
            st.info("Brankas kosong melompong.")

    # --- MENU 5: GANTI PASSWORD ---
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