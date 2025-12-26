import sys
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
from datetime import datetime, timedelta

from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget, 
                             QPushButton, QFileDialog, QLabel, QTabWidget, 
                             QHBoxLayout, QFrame, QTextEdit, QMessageBox)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

# --- SİHİRLİ FONKSİYON ---
def resource_path(relative_path):
    try: base_path = sys._MEIPASS
    except Exception: base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# --- STİL ---
STYLE_SHEET = """
    QMainWindow { background-color: #f4f7f6; }
    QTabWidget::pane { border: 1px solid #bdc3c7; background: white; border-radius: 5px; margin-top: -1px; }
    QTabBar::tab { background: #ecf0f1; color: #7f8c8d; padding: 10px 20px; margin-right: 4px; border-top-left-radius: 6px; border-top-right-radius: 6px; font-family: 'Segoe UI'; font-weight: bold; font-size: 13px; }
    QTabBar::tab:selected { background: #0078D7; color: white; }
    QTabBar::tab:hover { background: #d5dbdb; }
    QPushButton { font-family: 'Segoe UI'; font-weight: bold; }
    QTextEdit { font-family: 'Segoe UI'; line-height: 1.6; }
"""

# --- YARDIMCI FONKSİYONLAR ---
def format_date_tr(date_obj):
    if pd.isna(date_obj): return "-"
    months = {
        1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan", 5: "Mayıs", 6: "Haziran",
        7: "Temmuz", 8: "Ağustos", 9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık"
    }
    return f"{date_obj.day} {months[date_obj.month]} {date_obj.year}"

def parse_turkish_date(date_str):
    if isinstance(date_str, (pd.Timestamp, datetime)): return date_str
    if not isinstance(date_str, str) or str(date_str).lower() in ["yok", "nan", "nat", ""]: return pd.NaT
    tr_months = {"Ocak":"January", "Şubat":"February", "Mart":"March", "Nisan":"April", "Mayıs":"May", "Haziran":"June", "Temmuz":"July", "Ağustos":"August", "Eylül":"September", "Ekim":"October", "Kasım":"November", "Aralık":"December"}
    clean_str = str(date_str)
    for tr, en in tr_months.items():
        if tr in clean_str:
            clean_str = clean_str.replace(tr, en)
            break
    try: return pd.to_datetime(clean_str)
    except: return pd.NaT

def clean_duration(val):
    if isinstance(val, (int, float)): return float(val)
    if isinstance(val, str):
        val = val.lower().replace(" gün", "").replace("g", "").replace("day", "").replace("dy", "").replace(" ", "")
        try: return float(val)
        except: return 0.0
    return 0.0

def normalize_id(val):
    try:
        f_val = float(val)
        if f_val.is_integer(): return str(int(f_val))
        return str(f_val)
    except: return str(val).strip()

# --- KPI KART CLASS ---
class KPICard(QFrame):
    def __init__(self, title, value, color="#0078D7"):
        super().__init__()
        self.setStyleSheet(f"QFrame {{ background-color: white; border-radius: 8px; border-left: 5px solid {color}; border: 1px solid #e0e0e0; }} QLabel {{ border: none; background: transparent; }}")
        self.setFixedSize(220, 100)
        layout = QVBoxLayout()
        lbl_t = QLabel(title); lbl_t.setStyleSheet("color: #7f8c8d; font-size: 12px; font-weight: bold;")
        lbl_v = QLabel(value); lbl_v.setStyleSheet(f"color: {color}; font-size: 22px; font-weight: bold;")
        layout.addWidget(lbl_t); layout.addWidget(lbl_v); self.setLayout(layout)

# --- ANA UYGULAMA ---
class ProjectApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Proje Kontrol Merkezi v11.1 (ID & Updates)")
        self.setGeometry(100, 100, 1600, 900)
        self.setStyleSheet(STYLE_SHEET)
        try: self.setWindowIcon(QIcon(resource_path("app_icon.ico")))
        except: pass

        self.df_current = None; self.df_baseline = None
        main_widget = QWidget(); self.setCentralWidget(main_widget)
        self.main_layout = QVBoxLayout(); main_widget.setLayout(self.main_layout)

        self.create_top_bar()
        self.tabs = QTabWidget(); self.main_layout.addWidget(self.tabs)
        self.setup_pages()

    def create_top_bar(self):
        top = QFrame(); top.setStyleSheet("background-color: white; border-radius: 5px; margin-bottom: 5px;"); top.setFixedHeight(80)
        layout = QHBoxLayout(); top.setLayout(layout)
        title = QLabel("PROJE KONTROL MERKEZİ"); title.setStyleSheet("font-size: 20px; font-weight: bold; color: #2c3e50; margin-left: 10px;")
        
        self.btn_cur = QPushButton("📂 1. Güncel Programı Yükle")
        self.btn_cur.setStyleSheet("background-color: #0078D7; color: white; padding: 10px; border-radius: 5px; border:none;")
        self.btn_cur.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cur.clicked.connect(lambda: self.load_file(False))
        self.lbl_cur = QLabel("Yüklü Değil"); self.lbl_cur.setStyleSheet("color: #95a5a6; margin-right: 20px;")

        self.btn_base = QPushButton("📂 2. Baseline Yükle (Kıyas)")
        self.btn_base.setStyleSheet("background-color: #7f8c8d; color: white; padding: 10px; border-radius: 5px; border:none;")
        self.btn_base.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_base.clicked.connect(lambda: self.load_file(True))
        self.lbl_base = QLabel("Yüklü Değil"); self.lbl_base.setStyleSheet("color: #95a5a6;")

        layout.addWidget(title); layout.addStretch()
        layout.addWidget(self.btn_cur); layout.addWidget(self.lbl_cur)
        layout.addWidget(self.btn_base); layout.addWidget(self.lbl_base)
        self.main_layout.addWidget(top)

    def setup_pages(self):
        self.dash_tab = QWidget(); l1 = QVBoxLayout(); self.dash_tab.setLayout(l1)
        self.kpi_layout = QHBoxLayout(); l1.addLayout(self.kpi_layout)
        self.web_dash = QWebEngineView(); l1.addWidget(self.web_dash)
        self.tabs.addTab(self.dash_tab, "🚀 Yönetici Özeti")

        self.comp_tab = QWidget(); l2 = QVBoxLayout(); self.comp_tab.setLayout(l2)
        self.web_comp = QWebEngineView(); self.web_comp.setHtml("<h3 style='font-family:Segoe UI; padding:20px; color:#7f8c8d'>Kıyaslama verilerini görmek için Baseline dosyasını yükleyiniz.</h3>")
        l2.addWidget(self.web_comp); self.tabs.addTab(self.comp_tab, "⚖️ Kıyas Tablosu")

        self.web_gantt = QWebEngineView(); self.tabs.addTab(self.web_gantt, "📅 Kritik Hat (Gantt)")
        self.web_time = QWebEngineView(); self.tabs.addTab(self.web_time, "⏳ Zaman Çizelgesi")
        
        self.txt_notes = QTextEdit(); self.txt_notes.setReadOnly(True)
        self.txt_notes.setStyleSheet("QTextEdit { background-color: white; color: #2c3e50; font-size: 15px; padding: 30px; border: none; }")
        self.tabs.addTab(self.txt_notes, "🤖 Analiz & Notlar")

    def load_file(self, is_base):
        path, _ = QFileDialog.getOpenFileName(self, "Dosya Seç", "", "Excel/CSV (*.xlsx *.csv)")
        if not path: return
        try:
            df = self.process_data(path)
            if is_base:
                self.df_baseline = df
                self.lbl_base.setText(f"✅ {os.path.basename(path)}"); self.lbl_base.setStyleSheet("color: #27ae60; font-weight: bold;")
                self.btn_base.setStyleSheet("background-color: #27ae60; color: white;")
            else:
                self.df_current = df
                self.lbl_cur.setText(f"✅ {os.path.basename(path)}"); self.lbl_cur.setStyleSheet("color: #27ae60; font-weight: bold;")
            self.refresh_ui()
        except Exception as e: QMessageBox.critical(self, "Hata", str(e))

    def process_data(self, path):
        df = pd.read_csv(path) if path.endswith('.csv') else pd.read_excel(path)
        df.columns = df.columns.str.strip()
        
        if 'Benzersiz_Kimlik' not in df.columns:
             if 'Unique_ID' in df.columns: df.rename(columns={'Unique_ID': 'Benzersiz_Kimlik'}, inplace=True)
             else: raise ValueError("Dosyada 'Benzersiz_Kimlik' sütunu bulunamadı!")
        
        df['Benzersiz_Kimlik'] = df['Benzersiz_Kimlik'].apply(normalize_id)
        df['Başlangıç_Date'] = df['Başlangıç'].apply(parse_turkish_date)
        df['Bitiş_Date'] = df['Bitiş'].apply(parse_turkish_date)
        df['Fiili_Başlangıç_Date'] = df['Fiili_Başlangıç'].apply(parse_turkish_date)
        df['Fiili_Bitiş_Date'] = df['Fiili_Bitiş'].apply(parse_turkish_date)
        
        df['Süre_Num'] = df['Süre'].apply(clean_duration)
        df['Bolluk_Num'] = df['Toplam_Bolluk'].apply(clean_duration)
        
        # Kritiklik: Bolluk <= 0 ve Tamamlanmamış
        df['Kritik'] = (df['Bolluk_Num'] <= 0) & (pd.isna(df['Fiili_Bitiş_Date']))
        df['Durum'] = df.apply(lambda x: 'Kritik' if x['Kritik'] else ('Tamamlandı' if pd.notna(x['Fiili_Bitiş_Date']) else 'Normal'), axis=1)
        return df

    def refresh_ui(self):
        try:
            if self.df_current is None: return
            self.update_dashboard(self.df_current)
            self.update_gantt(self.df_current)
            self.update_timeline(self.df_current)
            self.generate_insights(self.df_current, self.df_baseline)
            if self.df_baseline is not None: self.update_comparison(self.df_current, self.df_baseline)
        except Exception as e:
            QMessageBox.critical(self, "Arayüz Hatası", f"Hata: {str(e)}")

    def update_dashboard(self, df):
        while self.kpi_layout.count():
            item = self.kpi_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        
        today = pd.Timestamp.now(); start = df['Başlangıç_Date'].min(); finish = df['Bitiş_Date'].max()
        total = (finish-start).days; elapsed = max(0, (today-start).days)
        summ = df[df['Benzersiz_Kimlik']=="1"]
        prog = summ.iloc[0]['Tamamlanma_Yüzdesi']*100 if not summ.empty else df['Tamamlanma_Yüzdesi'].mean()*100
        
        self.kpi_layout.addWidget(KPICard("Toplam Süre", f"{total} GÜN"))
        self.kpi_layout.addWidget(KPICard("Geçen Süre", f"{elapsed} GÜN", "#FF9800"))
        self.kpi_layout.addWidget(KPICard("İlerleme", f"%{prog:.1f}", "#9C27B0"))
        self.kpi_layout.addStretch()

        # SUBPLOTS TITLE EKLENDI
        fig = make_subplots(
            rows=2, cols=2, 
            specs=[[{"type":"indicator"}, {"type":"table", "rowspan":2}], [{"type":"domain"}, None]], 
            column_widths=[0.4, 0.6],
            subplot_titles=("", "Önümüzdeki 1 Hafta içerisinde başlaması ve/veya bitmesi planlanan kritik aktiviteler")
        )

        t_prog = min(100, (elapsed/total)*100) if total>0 else 0
        fig.add_trace(go.Indicator(mode="gauge+number+delta", value=prog, delta={'reference': t_prog}, gauge={'axis':{'range':[None,100]}, 'bar':{'color':"#0078D7"}, 'threshold':{'line':{'color':'red','width':4}, 'value':t_prog}}), row=1, col=1)
        
        # --- TABLO FILTRELERI (Özet Olmayanlar) ---
        target_date = today + timedelta(days=7)
        has_summary_col = 'Özet' in df.columns
        
        # 1. Başlaması Kritik Olanlar
        mask_start = (pd.isna(df['Fiili_Başlangıç_Date'])) & \
                     (df['Başlangıç_Date'] <= target_date) & \
                     (df['Bolluk_Num'] <= 30)
        
        if has_summary_col: mask_start = mask_start & (df['Özet'] == 'Hayır')
        start_crit = df[mask_start].sort_values('Başlangıç_Date').head(10)

        # 2. Tamamlanması Kritik Olanlar
        mask_finish = (pd.isna(df['Fiili_Bitiş_Date'])) & \
                      (df['Bitiş_Date'] <= target_date) & \
                      (df['Bolluk_Num'] <= 30)
        
        if has_summary_col: mask_finish = mask_finish & (df['Özet'] == 'Hayır')
        finish_crit = df[mask_finish].sort_values('Bitiş_Date').head(10)

        # ISIMLER VE KOLONLAR GUNCELLENDI
        start_crit['Kategori'] = "🟢 BAŞLAMASI PLANLANAN"
        start_crit['Tarih_Gosterim'] = start_crit['Başlangıç_Date']
        
        finish_crit['Kategori'] = "🔴 BİTMESİ PLANLANAN"
        finish_crit['Tarih_Gosterim'] = finish_crit['Bitiş_Date']

        comb = pd.concat([start_crit, finish_crit])

        if not comb.empty:
            tarihler = comb['Tarih_Gosterim'].apply(format_date_tr)
            
            # Aktivite ID KOLONU EKLENDI
            fig.add_trace(go.Table(
                header=dict(values=["Aktivite ID", "Risk Türü", "Aktivite Adı", "Kritik Tarih", "Bolluk"], 
                            fill_color='#2c3e50', font=dict(color='white')), 
                cells=dict(values=[comb['Benzersiz_Kimlik'], comb['Kategori'], comb['Ad'].str.slice(0,40), tarihler, comb['Bolluk_Num']], 
                           fill_color='#ecf0f1', font=dict(color='black'))
            ), row=1, col=2)
        else:
            fig.add_trace(go.Table(header=dict(values=["Bilgi"]), cells=dict(values=[["Önümüzdeki hafta için kritik risk bulunamadı."]])), row=1, col=2)
        
        cnt = df['Durum'].value_counts()
        fig.add_trace(go.Pie(labels=cnt.index, values=cnt.values, hole=.5, marker_colors=['#e74c3c', '#3498db', '#2ecc71']), row=2, col=1)
        fig.update_layout(margin=dict(l=10, r=10, t=30, b=10), font={'family':"Segoe UI"})
        self.web_dash.setHtml(fig.to_html(include_plotlyjs='cdn'))

    def update_comparison(self, df_c, df_b):
        merged = pd.merge(df_c, df_b, on="Benzersiz_Kimlik", how="inner", suffixes=('_cur', '_base'))
        today = pd.Timestamp.now()

        if 'Özet_cur' in merged.columns:
            merged = merged[merged['Özet_cur'] == 'Hayır']

        active_pool = merged[pd.isna(merged['Fiili_Bitiş_Date_cur'])]

        # A. Başlaması Gecikenler
        start_delayed = active_pool[
            (active_pool['Başlangıç_Date_base'] < today) & 
            (pd.isna(active_pool['Fiili_Başlangıç_Date_cur'])) &
            (active_pool['Başlangıç_Date_cur'] > active_pool['Başlangıç_Date_base']) &
            (active_pool['Bolluk_Num_cur'] <= 30)
        ]
        
        # B. Bitmesi Gecikenler
        finish_delayed = active_pool[
            (active_pool['Bitiş_Date_base'] < today) &
            (active_pool['Bitiş_Date_cur'] > active_pool['Bitiş_Date_base']) &
            (active_pool['Bolluk_Num_cur'] <= 30)
        ]

        # C. Süresi Kısılanlar
        active_pool_copy = active_pool.copy()
        active_pool_copy['Süre_Fark'] = active_pool_copy['Süre_Num_base'] - active_pool_copy['Süre_Num_cur']
        compressed = active_pool_copy[
            (active_pool_copy['Süre_Fark'] > 0) &
            (active_pool_copy['Bolluk_Num_cur'] <= 30)
        ]

        # D. Kritikliği Artanlar
        active_pool_copy['Bolluk_Fark'] = active_pool_copy['Bolluk_Num_base'] - active_pool_copy['Bolluk_Num_cur']
        worsening = active_pool_copy[
            (active_pool_copy['Bolluk_Fark'] > 0) & 
            (active_pool_copy['Bolluk_Num_cur'] <= 30)
        ]

        fig = make_subplots(rows=2, cols=2, 
            subplot_titles=("Başlaması Gecikenler (Bolluk<=30)", "Bitmesi Gecikenler (Bolluk<=30)", 
                            "Süresi Kısılanlar (Bolluk<=30)", "Kritikliği Artanlar (Bolluk<=30)"), 
            specs=[[{"type": "table"}, {"type": "table"}], [{"type": "table"}, {"type": "table"}]])

        def add_comp_table(data, col1, header1, col2, header2, row, col):
            if data.empty:
                fig.add_trace(go.Table(header=dict(values=["Durum"], fill_color='#34495e', font=dict(color='white')), cells=dict(values=[["Kriterlere uygun veri yok"]], fill_color='#ecf0f1', font=dict(color='black'))), row=row, col=col)
            else:
                top = data.head(10)
                v1 = top[col1].apply(format_date_tr) if 'Date' in col1 else top[col1]
                v2 = top[col2].apply(format_date_tr) if 'Date' in col2 else top[col2]

                # Aktivite ID EKLENDI
                fig.add_trace(go.Table(
                    header=dict(values=["Aktivite ID", "Aktivite", header1, header2, "Bolluk"], fill_color='#34495e', font=dict(color='white')),
                    cells=dict(values=[top['Benzersiz_Kimlik'], top['Ad_cur'].str.slice(0, 30), v1, v2, top['Bolluk_Num_cur']], fill_color='#ecf0f1', font=dict(color='black'))
                ), row=row, col=col)

        add_comp_table(start_delayed, 'Başlangıç_Date_base', 'Base Başlangıç', 'Başlangıç_Date_cur', 'Güncel Başlangıç', 1, 1)
        add_comp_table(finish_delayed, 'Bitiş_Date_base', 'Base Bitiş', 'Bitiş_Date_cur', 'Güncel Bitiş', 1, 2)
        add_comp_table(compressed, 'Süre_Num_base', 'Base Süre', 'Süre_Num_cur', 'Güncel Süre', 2, 1)
        add_comp_table(worsening, 'Bolluk_Num_base', 'Base Bolluk', 'Bolluk_Num_cur', 'Güncel Bolluk', 2, 2)

        fig.update_layout(height=800, margin=dict(l=10, r=10, t=50, b=10), font={'family': "Segoe UI"})
        self.web_comp.setHtml(fig.to_html(include_plotlyjs='cdn'))

    def update_gantt(self, df):
        data = df[(df['Özet']=='Evet') & (df['Kritik']==True)]
        if data.empty: self.web_gantt.setHtml("<h3>Veri Yok</h3>"); return
        fig = px.timeline(data, x_start="Başlangıç_Date", x_end="Bitiş_Date", y="Ad", color="Tamamlanma_Yüzdesi", color_continuous_scale="Reds")
        fig.update_yaxes(autorange="reversed"); self.web_gantt.setHtml(fig.to_html(include_plotlyjs='cdn'))

    def update_timeline(self, df):
        data = df[(df['Özet']=='Evet') & (df['Kritik']==True)]
        if data.empty: self.web_time.setHtml("<h3>Veri Yok</h3>"); return
        fig = px.scatter(data, x="Bitiş_Date", y="Ad", size="Süre_Num", color="Tamamlanma_Yüzdesi")
        fig.update_yaxes(autorange="reversed")
        for i,r in data.iterrows(): fig.add_shape(type="line", x0=r['Başlangıç_Date'], x1=r['Bitiş_Date'], y0=r['Ad'], y1=r['Ad'], line=dict(color='gray'))
        self.web_time.setHtml(fig.to_html(include_plotlyjs='cdn'))

    def generate_insights(self, df_curr, df_base=None):
        html = """
        <html><head><style>
            body { font-family: 'Segoe UI', sans-serif; background-color: white; color: #2c3e50; padding: 20px; }
            h2 { color: #0078D7; border-bottom: 2px solid #eee; padding-bottom: 10px; margin-bottom: 20px;}
            h3 { color: #c0392b; margin-top: 30px; font-size: 18px; display: flex; align-items: center;}
            .category { background: #ecf0f1; padding: 15px; border-radius: 8px; margin-bottom: 20px; border-left: 5px solid #bdc3c7; }
            .cat-critical { border-left-color: #e74c3c; background: #fdedec; }
            .cat-delay { border-left-color: #f39c12; background: #fef9e7; }
            .cat-compare { border-left-color: #3498db; background: #ebf5fb; }
            p { margin: 0 0 10px 0; line-height: 1.6; }
            b { color: #2c3e50; }
        </style></head><body>
        """
        html += "<h2>🤖 Proje Analiz Raporu</h2>"
        
        # Filtre: Özet olmayanlar
        tasks_curr = df_curr[df_curr['Özet'] == 'Hayır'] if 'Özet' in df_curr.columns else df_curr

        # 1. KRİTİK HAT ANALİZİ
        crit_active = tasks_curr[tasks_curr['Kritik'] == True]
        html += "<div class='category cat-critical'>"
        html += "<h3>🔥 Kritik Hat Analizi</h3>"
        if crit_active.empty:
            html += "<p>Projede şu an kritik hat üzerinde aktif (tamamlanmamış) bir aktivite bulunmamaktadır. Bu durum projenin zamanında bitmesi açısından olumludur.</p>"
        else:
            count = len(crit_active)
            html += f"<p>Proje genelinde bitiş tarihini doğrudan etkileyen <b>{count} adet</b> aktif kritik aktivite bulunmaktadır.</p>"
            for _, row in crit_active.sort_values('Başlangıç_Date').head(3).iterrows():
                tarih = format_date_tr(row['Bitiş_Date'])
                html += f"<p>➡ <b>{row['Ad']}</b> aktivitesi şu an kritik yoldadır ve {tarih} tarihinde bitmesi planlanmaktadır. Bu aktivitedeki herhangi bir gecikme, projenin teslim tarihini öteleyecektir.</p>"
        html += "</div>"

        # 2. GECİKME ANALİZİ (Bugüne Göre)
        today = pd.Timestamp.now()
        delayed = tasks_curr[(tasks_curr['Bitiş_Date'] < today) & (pd.isna(tasks_curr['Fiili_Bitiş_Date']))]
        
        if not delayed.empty:
            html += "<div class='category cat-delay'>"
            html += "<h3>🚫 Mevcut Gecikmeler</h3>"
            html += f"<p>Planlanan bitiş tarihi geçmiş olmasına rağmen henüz tamamlanmamış <b>{len(delayed)}</b> aktivite tespit edilmiştir.</p>"
            for _, row in delayed.head(3).iterrows():
                delay = (today - row['Bitiş_Date']).days
                html += f"<p>➡ <b>{row['Ad']}</b> aktivitesinin {delay} gün önce bitmesi gerekiyordu. Bu gecikme, ardıl aktivitelerin başlangıcını engelleyebilir.</p>"
            html += "</div>"

        # 3. KIYASLAMA ANALİZİ
        if df_base is not None:
            html += "<div class='category cat-compare'>"
            html += "<h3>⚖️ Baseline Karşılaştırma Analizi</h3>"
            
            merged = pd.merge(df_curr, df_base, on="Benzersiz_Kimlik", how="inner", suffixes=('_cur', '_base'))
            if 'Özet_cur' in merged.columns: merged = merged[merged['Özet_cur'] == 'Hayır']

            merged['Start_Delay'] = (merged['Başlangıç_Date_cur'] - merged['Başlangıç_Date_base']).dt.days
            merged['Finish_Delay'] = (merged['Bitiş_Date_cur'] - merged['Bitiş_Date_base']).dt.days
            merged['Süre_Fark'] = merged['Süre_Num_base'] - merged['Süre_Num_cur']
            merged['Bolluk_Fark'] = merged['Bolluk_Num_base'] - merged['Bolluk_Num_cur']
            
            active_pool = merged[pd.isna(merged['Fiili_Bitiş_Date_cur'])]

            # a) Kritikleşenler
            newly_critical = active_pool[(active_pool['Bolluk_Num_base'] > 0) & (active_pool['Bolluk_Num_cur'] <= 0)]
            if not newly_critical.empty:
                for _, row in newly_critical.head(3).iterrows():
                    html += f"<p>⚠️ <b>{row['Ad_cur']}</b> aktivitesi önceki planda kritik değilken, şu an kritik yola girmiştir. Öncelik seviyesi artırılmalıdır.</p>"
            
            # b) Süresi Kısılanlar
            compressed = active_pool[active_pool['Süre_Fark'] > 0]
            if not compressed.empty:
                for _, row in compressed.head(3).iterrows():
                    html += f"<p>⚡ <b>{row['Ad_cur']}</b> aktivitesinin süresi, önceki plana göre <b>{int(row['Süre_Fark'])} gün</b> kısaltılmıştır. Bu durum, gecikmeleri telafi etmek için yapılan bir sıkıştırma işlemidir.</p>"

            # c) Başlaması Gecikenler (Cümle Olarak)
            start_delayed = active_pool[
                (active_pool['Başlangıç_Date_base'] < today) & 
                (pd.isna(active_pool['Fiili_Başlangıç_Date_cur'])) &
                (active_pool['Başlangıç_Date_cur'] > active_pool['Başlangıç_Date_base'])
            ]
            if not start_delayed.empty:
                row = start_delayed.iloc[0]
                t1 = format_date_tr(row['Başlangıç_Date_base'])
                t2 = format_date_tr(row['Başlangıç_Date_cur'])
                html += f"<p>📉 <b>{row['Ad_cur']}</b> aktivitesinin başlaması gerekiyordu ({t1}) ancak güncel planda {t2} tarihine ötelenmiştir.</p>"

            html += "</div>"

        html += "</body></html>"
        self.txt_notes.setHtml(html)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ProjectApp()
    window.show()
    sys.exit(app.exec())
