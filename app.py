# --- GÜNCELLENMİŞ VERİ YÜKLEME KISMI ---

# Önce Excel, sonra CSV arayalım
file_path = None
if os.path.exists("data.xlsx"):
    file_path = "data.xlsx"
    file_type = "xlsx"
elif os.path.exists("data.csv"):
    file_path = "data.csv"
    file_type = "csv"

df = None

# Dosya bulunduysa oku
if file_path:
    try:
        if file_type == "xlsx":
            # Excel okuma motoru
            df = pd.read_excel(file_path)
        else:
            # CSV okuma motoru
            df = pd.read_csv(file_path)
        st.success(f"✅ Veri '{file_path}' dosyasından başarıyla yüklendi.")
    except Exception as e:
        st.error(f"Dosya okunurken hata oluştu: {e}")

# Dosya yoksa veya kullanıcı yeni yükleme yaparsa
if df is None:
    st.warning("Otomatik veri dosyası (data.xlsx veya data.csv) bulunamadı.")
    uploaded_file = st.sidebar.file_uploader("Dosya Yükle", type=["csv", "xlsx"])
    if uploaded_file is not None:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
else:
    # Dosya zaten yüklü ama kullanıcı değiştirmek isterse
    uploaded_file = st.sidebar.file_uploader("Farklı dosya yükle", type=["csv", "xlsx"])
    if uploaded_file is not None:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)