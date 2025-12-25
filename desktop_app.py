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

# --- SİHİRLİ FONKSİYON: EXE İÇİNDEN DOSYA BULMA ---
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# --- STİL TANIMLAMALARI ---
STYLE_SHEET = """
    QMainWindow { background-color: #f4f7f6; }
    QTabWidget::pane { border: 1px solid #bdc3c7; background: white; border-radius: 5px; margin-top: -1px; }
    QTabBar::tab { background: #ecf0f1; color: #7f8c8d; padding: 10px 20px; margin-right: 4px; border-top-left-radius: 6px; border-top-right-radius: 6px; font-family: 'Segoe UI'; font-weight: bold; font-size: 13px; }
    QTabBar::tab:selected { background: #0078D7; color: white; }
    QTabBar::tab:hover { background: #d5dbdb; }
    QPushButton { font-family: 'Segoe UI'; font-weight: bold; }
"""

# --- YARDIMCI FONKSİYONLAR ---
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
        val = val.lower().replace(" gün", "").replace("g", "").replace(" ", "")
        try: return float(val)
        except: return 0.0
    return 0.0

def normalize_id(val):
    """
    ID'leri standartlaştırır:
    100 -> "100"
    100.0 -> "100"
    " 100 " -> "100"
    """
    try:
        # Önce float'a çevirmeyi dene (100.0 veya "100.0" yakalamak için)
        f_val = float(val)
        # Eğer tam sayı ise (100.0) int yap (100) sonra string yap ("100")
        if f_val.is_integer():
            return str(int(f_val))
        # Değilse normal string yap
        return str(f_val)
    except:
        # Sayı değilse (örn: "Task_1") sadece boşlukları sil
        return str(val).strip()

# --- KPI KART CLASS ---
class KPICard(QFrame):
    def __init__(self, title, value, color="#0078D7"):
        super().__init__()
        self.setStyleSheet(f"""
            QFrame {{ background-color: white; border-radius: 8px; border-left: 5px solid {color}; border: 1px solid #e0e0e0; }}
            QLabel {{ border: none; background: transparent; }}
        """)
        self.setFixedSize(220, 100)
        layout = QVBoxLayout()
        lbl_t = QLabel(title); lbl_t.setStyleSheet("color: #7f8c8d; font-size: 12px; font-weight: bold;")
        lbl_v = QLabel(value); lbl_v.setStyleSheet(f"color: {color}; font-size: 22px; font-weight: bold;")
        layout.addWidget(lbl_t); layout.addWidget(lbl_v); self.setLayout(layout)

# --- ANA UYGULAMA ---
class ProjectApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Proje Kontrol Merkezi v9.0 (Final Fix)")
        self.setGeometry(100, 100, 1600, 900)
        self.setStyleSheet(STYLE_SHEET)

        try:
            icon_path = resource_path("app_icon.ico")
            self.setWindowIcon(QIcon(icon_path))
        except: pass

        self.df_current = None; self.df_baseline = None
        main_widget = QWidget(); self.setCentralWidget(main_widget)
        self.main_layout = QVBoxLayout(); main_widget.setLayout(self.main_layout)

        self.create_top_bar()
        self.tabs = QTabWidget(); self.main_layout.addWidget(self.tabs)
        self.setup_pages()

    def create_top_bar(self):
        top_frame = QFrame(); top_frame.setStyleSheet("background-color: white; border-radius: 5px; margin-bottom: 5px;"); top_frame.setFixedHeight(80)
        layout = QHBoxLayout(); top_frame.setLayout(layout)
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
        self.main_layout.addWidget(top_frame)

    def setup_pages(self):
        # 1. Dashboard
        self.dash_tab = QWidget(); dash_layout = QVBoxLayout(); self.dash_tab.setLayout(dash_layout)
        self.kpi_layout = QHBoxLayout(); dash_layout.addLayout(self.kpi_layout)
        self.web_dash = QWebEngineView(); dash_layout.addWidget(self.web_dash)
        self.tabs.addTab(self.dash_tab, "🚀 Yönetici Özeti")

        # 2. Kıyas Tablosu
        self.comp_tab = QWidget(); comp_layout = QVBoxLayout(); self.comp_tab.setLayout(comp_layout)
        self.web_comp = QWebEngineView()
        self.web_comp.setHtml("<h3 style='font-family:Segoe UI; padding:20px; color:#7f8c8d'>Kıyaslama verilerini görmek için Baseline dosyasını yükleyiniz.</h3>")
        comp_layout.addWidget(self.web_comp)
        self.tabs.addTab(self.comp_tab, "⚖️ Kıyas Tablosu")

        # 3. Gantt ve Timeline
        self.web_gantt = QWebEngineView(); self.tabs.addTab(self.web_gantt, "📅 Kritik Hat (Gantt)")
        self.web_time = QWebEngineView(); self.tabs.addTab(self.web_time, "⏳ Zaman Çizelgesi")

        # 4. Notlar
        self.txt_notes = QTextEdit(); self.txt_notes.setReadOnly(True)
        self.txt_notes.setStyleSheet("QTextEdit { background-color: white; color: black; font-size: 15px; padding: 15px; border: none; }")
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
        
        # Sütun isimlerindeki boşlukları temizle
        df.columns = df.columns.str.strip()
        
        # ID Kontrolü
        if 'Benzersiz_Kimlik' not in df.columns:
             if 'Unique_ID' in df.columns: df.rename(columns={'Unique_ID': 'Benzersiz_Kimlik'}, inplace=True)
             else: raise ValueError("Dosyada 'Benzersiz_Kimlik' (veya Unique_ID) sütunu bulunamadı!")
        
        # --- KRİTİK DÜZELTME: ID NORMALİZASYONU ---
        # "100" ile "100.0" eşleşmez. Hepsini normalize ediyoruz.
        df['Benzersiz_Kimlik'] = df['Benzersiz_Kimlik'].apply(normalize_id)

        df['Başlangıç_Date'] = df['Başlangıç'].apply(parse_turkish_date)
        df['Bitiş_Date'] = df['Bitiş'].apply(parse_turkish_date)
        df['Süre_Num'] = df['Süre'].apply(clean_duration)
        df['Bolluk_Num'] = df['Toplam_Bolluk'].apply(clean_duration)
        df['Kritik'] = (df['Bolluk_Num'] <= 0) & (df['Tamamlanma_Yüzdesi'] < 1.0)
        df['Durum'] = df.apply(lambda x: 'Kritik' if x['Kritik'] else ('Tamamlandı' if x['Tamamlanma_Yüzdesi'] == 1.0 else 'Normal'), axis=1)
        return df

    def refresh_ui(self):
        try:
            if self.df_current is None: return
            self.update_dashboard(self.df_current)
            self.update_gantt(self.df_current)
            self.update_timeline(self.df_current)
            # Notlar fonksiyonuna baseline'ı da gönderiyoruz
            self.generate_insights(self.df_current, self.df_baseline)
            
            if self.df_baseline is not None: 
                self.update_comparison(self.df_current, self.df_baseline)
        except Exception as e:
            QMessageBox.critical(self, "Arayüz Hatası", f"Ekran yenilenirken hata: {str(e)}")

    def update_dashboard(self, df):
        # Güvenli Temizlik
        while self.kpi_layout.count():
            item = self.kpi_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        
        today = pd.Timestamp.now(); start = df['Başlangıç_Date'].min(); finish = df['Bitiş_Date'].max()
        total = (finish-start).days; elapsed = max(0, (today-start).days)
        
        # ID Normalize olduğu için string "1" arıyoruz
        summ = df[df['Benzersiz_Kimlik']=="1"]
        prog = summ.iloc[0]['Tamamlanma_Yüzdesi']*100 if not summ.empty else df['Tamamlanma_Yüzdesi'].mean()*100
        
        self.kpi_layout.addWidget(KPICard("Toplam Süre", f"{total} GÜN"))
        self.kpi_layout.addWidget(KPICard("Geçen Süre", f"{elapsed} GÜN", "#FF9800"))
        self.kpi_layout.addWidget(KPICard("İlerleme", f"%{prog:.1f}", "#9C27B0"))
        self.kpi_layout.addStretch()

        fig = make_subplots(rows=2, cols=2, specs=[[{"type":"indicator"}, {"type":"table", "rowspan":2}], [{"type":"domain"}, None]], column_widths=[0.4, 0.6])
        t_prog = min(100, (elapsed/total)*100) if total>0 else 0
        fig.add_trace(go.Indicator(mode="gauge+number+delta", value=prog, delta={'reference': t_prog}, gauge={'axis':{'range':[None,100]}, 'bar':{'color':"#0078D7"}, 'threshold':{'line':{'color':'red','width':4}, 'value':t_prog}}), row=1, col=1)
        
        crit = df[df['Kritik']==True].sort_values('Başlangıç_Date')
        urg = crit[crit['Başlangıç_Date']<=today].head(8).copy(); urg['Tip']="🔴 ACİL"
        fut = crit[crit['Başlangıç_Date']>today].head(8).copy(); fut['Tip']="📅 PLANLI"
        comb = pd.concat([urg, fut])
        
        if not comb.empty:
            fig.add_trace(go.Table(header=dict(values=["Durum", "İş Adı", "Bitiş", "%"], fill_color='#2c3e50', font=dict(color='white')), cells=dict(values=[comb['Tip'], comb['Ad'].str.slice(0,30), comb['Bitiş_Date'].dt.strftime('%d-%m'), (comb['Tamamlanma_Yüzdesi']*100).map('{:.0f}'.format)], fill_color='#ecf0f1', font=dict(color='black'))), row=1, col=2)
        
        cnt = df['Durum'].value_counts()
        fig.add_trace(go.Pie(labels=cnt.index, values=cnt.values, hole=.5, marker_colors=['#e74c3c', '#3498db', '#2ecc71']), row=2, col=1)
        fig.update_layout(margin=dict(l=10, r=10, t=30, b=10), font={'family':"Segoe UI"})
        self.web_dash.setHtml(fig.to_html(include_plotlyjs='cdn'))

    def update_comparison(self, df_c, df_b):
        # Eşleşme (ID'ler zaten normalize edildiği için güvenli)
        merged = pd.merge(df_c, df_b, on="Benzersiz_Kimlik", how="inner", suffixes=('_cur', '_base'))
        
        if merged.empty:
            self.web_comp.setHtml("<h3 style='color:red; padding:20px'>HATA: Hiçbir aktivite eşleşmedi! ID formatlarını kontrol edin.</h3>")
            return

        merged['Start_Delay'] = (merged['Başlangıç_Date_cur'] - merged['Başlangıç_Date_base']).dt.days
        merged['Finish_Delay'] = (merged['Bitiş_Date_cur'] - merged['Bitiş_Date_base']).dt.days
        merged['Dur_Diff'] = merged['Süre_Num_cur'] - merged['Süre_Num_base']
        merged['Slack_Diff'] = merged['Bolluk_Num_cur'] - merged['Bolluk_Num_base']
        
        # Filtre (Bolluk <= 30) - NaN varsa 0 kabul et
        risky_pool = merged[merged['Bolluk_Num_cur'].fillna(0) <= 30]

        fig = make_subplots(rows=2, cols=2, 
            subplot_titles=("Başlaması Gecikenler (Bolluk<=30)", "Bitmesi Gecikenler (Bolluk<=30)", "Süresi Kısılanlar (Bolluk<=30)", "Kritikliği Artanlar (Bolluk<=30)"), 
            specs=[[{"type": "table"}, {"type": "table"}], [{"type": "table"}, {"type": "table"}]])

        def add_comp_table(data, sort_col, asc, col_idx, row_idx, val_col, header):
            if data.empty:
                headers = ["Bilgi"]; cells = [[f"Filtreye ({header}) uyan veri yok"]]
            else:
                top = data.sort_values(sort_col, ascending=asc).head(10)
                headers = ["Aktivite", header, "Bolluk"]
                cells = [top['Ad_cur'].str.slice(0, 25), top[val_col], top['Bolluk_Num_cur']]

            fig.add_trace(go.Table(header=dict(values=headers, fill_color='#2c3e50', font=dict(color='white')), cells=dict(values=cells, fill_color='#ecf0f1', font=dict(color='black'))), row=row_idx, col=col_idx)

        add_comp_table(risky_pool[risky_pool['Start_Delay'] > 0], 'Start_Delay', False, 1, 1, 'Start_Delay', "Gecikme (Gün)")
        add_comp_table(risky_pool[risky_pool['Finish_Delay'] > 0], 'Finish_Delay', False, 2, 1, 'Finish_Delay', "Öteleme (Gün)")
        add_comp_table(risky_pool[risky_pool['Dur_Diff'] < 0], 'Dur_Diff', True, 1, 2, 'Dur_Diff', "Kısalma (Gün)")
        worsening = risky_pool[risky_pool['Slack_Diff'] < 0]
        add_comp_table(worsening, 'Slack_Diff', True, 2, 2, 'Slack_Diff', "Bolluk Kaybı")

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
            body { font-family: 'Segoe UI', sans-serif; background-color: white; color: black; padding: 20px; }
            h2 { color: #0078D7; border-bottom: 2px solid #eee; padding-bottom: 10px; }
            h3 { color: #d32f2f; margin-top: 20px; }
            h4 { color: #2c3e50; margin-top: 15px; border-left: 4px solid #0078D7; padding-left: 10px;}
            li { margin-bottom: 8px; line-height: 1.6; }
            .highlight { background-color: #fff3cd; padding: 2px 5px; border-radius: 3px; font-weight: bold; }
            .safe { color: green; font-weight: bold; }
            .danger { color: red; font-weight: bold; }
        </style></head><body>
        """
        html += "<h2>🤖 Akıllı Proje Analizi</h2>"
        
        crit_active = df_curr[df_curr['Kritik'] == True]
        if crit_active.empty:
            html += "<p class='safe'>✅ MÜKEMMEL: Şu anda projenin bitiş tarihini tehdit eden 'Kritik' ve 'Tamamlanmamış' aktivite bulunmamaktadır.</p>"
        else:
            html += f"<p>Şu anda proje genelinde, gecikmesi proje bitişini doğrudan öteleyecek <b>{len(crit_active)}</b> adet aktif kritik görev bulunmaktadır.</p>"
            html += "<h3>⚠️ Dikkat Edilmesi Gereken Kritik Aktiviteler (Top 5)</h3><ul>"
            for _, row in crit_active.sort_values(by='Başlangıç_Date').head(5).iterrows():
                html += f"<li><b>{row['Ad']}</b> (Bitiş: {row['Bitiş_Date'].strftime('%d-%m-%Y')}) - <span class='danger'>Tamamlanma: %{int(row['Tamamlanma_Yüzdesi']*100)}</span></li>"
            html += "</ul>"

        today = pd.Timestamp.now()
        delayed = df_curr[(df_curr['Bitiş_Date'] < today) & (df_curr['Tamamlanma_Yüzdesi'] < 1.0)]
        if not delayed.empty:
            html += "<h3>🚫 Gecikmiş İşler (Acil Müdahale)</h3>"
            html += f"<p>Bitiş tarihi geçmiş <b>{len(delayed)}</b> aktivite var.</p><ul>"
            for _, row in delayed.head(5).iterrows():
                delay_days = (today - row['Bitiş_Date']).days
                html += f"<li><b>{row['Ad']}</b> - <span class='highlight'>{delay_days} Gün Gecikmiş</span></li>"
            html += "</ul>"

        summary_row = df_curr[df_curr['Benzersiz_Kimlik'] == "1"]
        progress = summary_row.iloc[0]['Tamamlanma_Yüzdesi']*100 if not summary_row.empty else df_curr['Tamamlanma_Yüzdesi'].mean()*100
        html += "<h3>💡 Yönetici Özeti</h3>"
        html += f"<p>Proje genel ilerlemesi <b>%{progress:.1f}</b> seviyesindedir.</p>"

        # KIYAS RAPORU
        if df_base is not None:
            merged = pd.merge(df_curr, df_base, on="Benzersiz_Kimlik", how="inner", suffixes=('_cur', '_base'))
            merged['Start_Delay'] = (merged['Başlangıç_Date_cur'] - merged['Başlangıç_Date_base']).dt.days
            merged['Finish_Delay'] = (merged['Bitiş_Date_cur'] - merged['Bitiş_Date_base']).dt.days
            merged['Dur_Diff'] = merged['Süre_Num_cur'] - merged['Süre_Num_base']
            merged['Slack_Diff'] = merged['Bolluk_Num_cur'] - merged['Bolluk_Num_base']

            html += "<br><hr>"
            html += "<h2>⚖️ Baseline Karşılaştırma Raporu</h2>"
            
            d_starts = len(merged[merged['Start_Delay'] > 0])
            d_finish = len(merged[merged['Finish_Delay'] > 0])
            html += f"<p>Baseline programa göre <b>{d_starts}</b> aktivitenin başlangıcı, <b>{d_finish}</b> aktivitenin bitişi ötelenmiştir.</p>"
            
            compressed = merged[merged['Dur_Diff'] < 0]
            if not compressed.empty:
                html += "<h3>⚡ Hızlandırılan (Süresi Kısılan) İşler</h3><ul>"
                for _, r in compressed.sort_values('Dur_Diff').head(5).iterrows():
                    html += f"<li><b>{r['Ad_cur']}</b>: {abs(r['Dur_Diff'])} gün kısıldı.</li>"
                html += "</ul>"

            # Kritikliği Artanlar (Riskli Olanlar)
            risky_worsening = merged[(merged['Slack_Diff'] < 0) & (merged['Bolluk_Num_cur'] <= 30)]
            if not risky_worsening.empty:
                html += "<h3>🔥 Kritikliği Artan (Riskli) İşler</h3>"
                html += "<p>Aşağıdaki işlerin bolluk süreleri Baseline'a göre azalmıştır ve şu an 30 günün altındadır:</p><ul>"
                for _, r in risky_worsening.sort_values('Slack_Diff').head(5).iterrows():
                    html += f"<li><b>{r['Ad_cur']}</b>: Bolluk {abs(r['Slack_Diff'])} gün azaldı. (Mevcut: {r['Bolluk_Num_cur']})</li>"
                html += "</ul>"

        html += "</body></html>"
        self.txt_notes.setHtml(html)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ProjectApp()
    window.show()
    sys.exit(app.exec())
