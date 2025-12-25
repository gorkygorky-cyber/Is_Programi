import sys
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
from datetime import datetime, timedelta

from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget, 
                             QPushButton, QFileDialog, QLabel, QStackedWidget, 
                             QHBoxLayout, QFrame, QTextEdit, QSizePolicy, QSpacerItem)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QFont

# --- STİL TANIMLAMALARI (CSS) ---
SIDEBAR_STYLE = """
    QWidget {
        background-color: #2c3e50;
        color: white;
    }
    QPushButton {
        background-color: transparent;
        border: none;
        color: #bdc3c7;
        text-align: left;
        padding: 15px;
        font-size: 14px;
        font-family: 'Segoe UI', sans-serif;
    }
    QPushButton:hover {
        background-color: #34495e;
        color: white;
        border-left: 4px solid #3498db;
    }
    QPushButton:checked {
        background-color: #34495e;
        color: white;
        border-left: 4px solid #3498db;
        font-weight: bold;
    }
    QLabel {
        color: white;
        font-weight: bold;
        font-size: 18px;
        padding: 20px;
    }
"""

CONTENT_STYLE = """
    QWidget {
        background-color: #ecf0f1;
    }
    QLabel {
        color: #2c3e50;
    }
"""

# --- YARDIMCI FONKSİYONLAR ---
def parse_turkish_date(date_str):
    if not isinstance(date_str, str) or date_str == "Yok":
        return pd.NaT
    tr_months = {
        "Ocak": "January", "Şubat": "February", "Mart": "March", "Nisan": "April", 
        "Mayıs": "May", "Haziran": "June", "Temmuz": "July", "Ağustos": "August", 
        "Eylül": "September", "Ekim": "October", "Kasım": "November", "Aralık": "December"
    }
    for tr, en in tr_months.items():
        if tr in date_str:
            date_str = date_str.replace(tr, en)
            break
    try:
        return pd.to_datetime(date_str)
    except:
        return pd.NaT

def clean_duration(val):
    if isinstance(val, str):
        val = val.lower().replace(" gün", "").replace("g", "").replace(" ", "")
        try:
            return float(val)
        except:
            return 0.0
    return val

# --- KPI KART CLASS (Yenilenmiş Tasarım) ---
class KPICard(QFrame):
    def __init__(self, title, value, color="#3498db", icon="📊"):
        super().__init__()
        self.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border-radius: 10px;
                border-left: 5px solid {color};
            }}
            QLabel {{
                background-color: transparent;
                border: none;
            }}
        """)
        self.setFixedSize(220, 100)
        layout = QVBoxLayout()
        
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("color: #7f8c8d; font-size: 12px; text-transform: uppercase; letter-spacing: 1px;")
        layout.addWidget(lbl_title)
        
        lbl_value = QLabel(value)
        lbl_value.setStyleSheet(f"color: {color}; font-size: 24px; font-weight: bold;")
        layout.addWidget(lbl_value)
        
        self.setLayout(layout)

# --- ANA UYGULAMA ---
class ProjectApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Proje Yönetim Paneli v5.0")
        self.setGeometry(100, 100, 1600, 900)
        
        # Veri Saklama
        self.df_current = None
        self.df_baseline = None

        # Ana Layout (Yatay: Sidebar + İçerik)
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.main_layout = QHBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.main_widget.setLayout(self.main_layout)

        # 1. SIDEBAR OLUŞTURMA
        self.create_sidebar()

        # 2. İÇERİK ALANI (Stacked Widget)
        self.content_area = QWidget()
        self.content_area.setStyleSheet(CONTENT_STYLE)
        self.content_layout = QVBoxLayout()
        self.content_area.setLayout(self.content_layout)
        
        # Üst Bar (Dosya Yükleme Alanı)
        self.create_top_bar()
        
        # Sayfaların Tutulduğu Stack
        self.pages = QStackedWidget()
        self.content_layout.addWidget(self.pages)
        
        self.main_layout.addWidget(self.sidebar_frame, 1) # Sidebar %10-15
        self.main_layout.addWidget(self.content_area, 5)  # İçerik %85-90

        # Sayfaları Hazırla
        self.setup_pages()

        # İlk Sayfayı Aç
        self.btn_dash.setChecked(True)
        self.pages.setCurrentIndex(0)

    def create_sidebar(self):
        self.sidebar_frame = QFrame()
        self.sidebar_frame.setStyleSheet(SIDEBAR_STYLE)
        self.sidebar_layout = QVBoxLayout()
        self.sidebar_frame.setLayout(self.sidebar_layout)

        # Logo / Başlık
        lbl_logo = QLabel("PROJE\nKONTROL\nMERKEZİ")
        lbl_logo.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.sidebar_layout.addWidget(lbl_logo)

        # Menü Butonları
        self.btn_dash = self.add_menu_btn("🚀 Yönetici Özeti", 0)
        self.btn_comp = self.add_menu_btn("⚖️ Kıyas Tablosu", 1)
        self.btn_gantt = self.add_menu_btn("📅 Kritik Hat (Gantt)", 2)
        self.btn_time = self.add_menu_btn("⏳ Zaman Çizelgesi", 3)
        self.btn_note = self.add_menu_btn("🤖 Analiz & Notlar", 4)

        self.sidebar_layout.addStretch()
        
        lbl_version = QLabel("v5.0 Stable")
        lbl_version.setStyleSheet("font-size: 10px; color: #7f8c8d; padding: 10px;")
        self.sidebar_layout.addWidget(lbl_version)

    def add_menu_btn(self, text, index):
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setAutoExclusive(True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda: self.pages.setCurrentIndex(index))
        self.sidebar_layout.addWidget(btn)
        return btn

    def create_top_bar(self):
        top_bar = QFrame()
        top_bar.setStyleSheet("background-color: white; border-bottom: 1px solid #bdc3c7;")
        top_bar.setFixedHeight(70)
        layout = QHBoxLayout()
        top_bar.setLayout(layout)

        self.btn_load_cur = QPushButton("📂 1. Güncel Programı Yükle")
        self.btn_load_cur.setStyleSheet("background-color: #3498db; color: white; border-radius: 5px; padding: 8px;")
        self.btn_load_cur.clicked.connect(lambda: self.load_file(False))
        
        self.lbl_cur_status = QLabel("Yüklü Değil")
        self.lbl_cur_status.setStyleSheet("color: #95a5a6; margin-right: 20px;")

        self.btn_load_base = QPushButton("📂 2. Baseline Yükle (Kıyas)")
        self.btn_load_base.setStyleSheet("background-color: #95a5a6; color: white; border-radius: 5px; padding: 8px;")
        self.btn_load_base.clicked.connect(lambda: self.load_file(True))
        
        self.lbl_base_status = QLabel("Yüklü Değil")
        self.lbl_base_status.setStyleSheet("color: #95a5a6;")

        layout.addWidget(self.btn_load_cur)
        layout.addWidget(self.lbl_cur_status)
        layout.addStretch()
        layout.addWidget(self.btn_load_base)
        layout.addWidget(self.lbl_base_status)

        self.content_layout.addWidget(top_bar)

    def setup_pages(self):
        # 1. Dashboard
        self.page_dash = QWidget()
        layout_dash = QVBoxLayout()
        self.kpi_layout = QHBoxLayout() # KPI Kartları
        layout_dash.addLayout(self.kpi_layout)
        self.web_dash = QWebEngineView() # Grafikler
        layout_dash.addWidget(self.web_dash)
        self.page_dash.setLayout(layout_dash)
        self.pages.addWidget(self.page_dash)

        # 2. Kıyas Tablosu
        self.page_comp = QWidget()
        layout_comp = QVBoxLayout()
        self.web_comp = QWebEngineView()
        self.web_comp.setHtml("<h3 style='font-family:Segoe UI; padding:20px; color:#7f8c8d'>Lütfen Kıyaslama için Baseline dosyasını yükleyiniz.</h3>")
        layout_comp.addWidget(self.web_comp)
        self.page_comp.setLayout(layout_comp)
        self.pages.addWidget(self.page_comp)

        # 3. Gantt
        self.web_gantt = QWebEngineView()
        self.pages.addWidget(self.web_gantt)

        # 4. Timeline
        self.web_time = QWebEngineView()
        self.pages.addWidget(self.web_time)

        # 5. Notlar
        self.txt_notes = QTextEdit()
        self.txt_notes.setReadOnly(True)
        self.txt_notes.setStyleSheet("border: none; padding: 20px; font-size: 15px; font-family: 'Segoe UI'; background-color: white;")
        self.pages.addWidget(self.txt_notes)

    # --- LOJİK VE VERİ İŞLEME ---
    def load_file(self, is_baseline):
        file_path, _ = QFileDialog.getOpenFileName(self, "Dosya Seç", "", "Excel/CSV (*.xlsx *.csv)")
        if not file_path: return

        try:
            df = self.process_data(file_path)
            if is_baseline:
                self.df_baseline = df
                self.lbl_base_status.setText(f"✅ {os.path.basename(file_path)}")
                self.lbl_base_status.setStyleSheet("color: #27ae60; font-weight: bold;")
                self.btn_load_base.setStyleSheet("background-color: #27ae60; color: white; border-radius: 5px; padding: 8px;")
            else:
                self.df_current = df
                self.lbl_cur_status.setText(f"✅ {os.path.basename(file_path)}")
                self.lbl_cur_status.setStyleSheet("color: #27ae60; font-weight: bold;")
            
            self.refresh_ui()
        except Exception as e:
            print(e)

    def process_data(self, path):
        if path.endswith('.csv'): df = pd.read_csv(path)
        else: df = pd.read_excel(path)
        
        df['Başlangıç_Date'] = df['Başlangıç'].apply(parse_turkish_date)
        df['Bitiş_Date'] = df['Bitiş'].apply(parse_turkish_date)
        df['Süre_Num'] = df['Süre'].apply(clean_duration)
        df['Bolluk_Num'] = df['Toplam_Bolluk'].apply(clean_duration)
        # Kritiklik Mantığı: Bolluk <= 0 ve Tamamlanmamış
        df['Kritik'] = (df['Bolluk_Num'] <= 0) & (df['Tamamlanma_Yüzdesi'] < 1.0)
        df['Durum'] = df.apply(lambda x: 'Kritik' if x['Kritik'] else ('Tamamlandı' if x['Tamamlanma_Yüzdesi'] == 1.0 else 'Normal'), axis=1)
        return df

    def refresh_ui(self):
        if self.df_current is None: return

        # Dashboard Güncelle
        self.update_dashboard(self.df_current)
        self.update_gantt(self.df_current)
        self.update_timeline(self.df_current)
        self.update_notes(self.df_current, self.df_baseline)

        if self.df_baseline is not None:
            self.update_comparison(self.df_current, self.df_baseline)

    def update_dashboard(self, df):
        # KPI Kartlarını Yenile
        for i in reversed(range(self.kpi_layout.count())): 
            self.kpi_layout.itemAt(i).widget().setParent(None)
        
        today = pd.Timestamp.now()
        start = df['Başlangıç_Date'].min()
        finish = df['Bitiş_Date'].max()
        total_days = (finish - start).days
        elapsed = max(0, (today - start).days)
        
        # Ana İlerleme
        summ = df[df['Benzersiz_Kimlik'] == 1]
        progress = summ.iloc[0]['Tamamlanma_Yüzdesi']*100 if not summ.empty else df['Tamamlanma_Yüzdesi'].mean()*100
        
        self.kpi_layout.addWidget(KPICard("Toplam Süre", f"{total_days} GÜN"))
        self.kpi_layout.addWidget(KPICard("Geçen Süre", f"{elapsed} GÜN", "#e67e22"))
        self.kpi_layout.addWidget(KPICard("Gerçekleşen", f"%{progress:.1f}", "#9b59b6"))
        self.kpi_layout.addStretch()

        # Grafikler
        fig = make_subplots(rows=2, cols=2, specs=[[{"type": "indicator"}, {"type": "table", "rowspan": 2}], [{"type": "domain"}, None]],
                            column_widths=[0.4, 0.6])
        
        # Gauge
        time_prog = min(100, (elapsed/total_days)*100) if total_days > 0 else 0
        fig.add_trace(go.Indicator(
            mode = "gauge+number+delta", value = progress,
            delta = {'reference': time_prog, 'relative': False},
            gauge = {'axis': {'range': [None, 100]}, 'bar': {'color': "#3498db"}, 'threshold': {'line': {'color': "red", 'width': 4}, 'value': time_prog}}
        ), row=1, col=1)

        # Tablo
        crit = df[df['Kritik']==True].sort_values('Başlangıç_Date')
        urgent = crit[crit['Başlangıç_Date'] <= today].head(8)
        future = crit[crit['Başlangıç_Date'] > today].head(8)
        urgent['Tip'] = "🔴 ACİL"
        future['Tip'] = "📅 PLANLI"
        comb = pd.concat([urgent, future])
        
        if not comb.empty:
            fig.add_trace(go.Table(
                header=dict(values=["Durum", "İş Adı", "Bitiş", "%"], fill_color='#2c3e50', font=dict(color='white')),
                cells=dict(values=[comb['Tip'], comb['Ad'].str.slice(0,30), comb['Bitiş_Date'].dt.strftime('%d-%m'), (comb['Tamamlanma_Yüzdesi']*100).map('{:.0f}'.format)],
                           fill_color='#ecf0f1', font=dict(color='#2c3e50'))
            ), row=1, col=2)
        
        # Pie
        cnt = df['Durum'].value_counts()
        fig.add_trace(go.Pie(labels=cnt.index, values=cnt.values, hole=.5, marker_colors=['#e74c3c', '#3498db', '#2ecc71']), row=2, col=1)
        
        fig.update_layout(margin=dict(l=10, r=10, t=30, b=10), font={'family': "Segoe UI"})
        self.web_dash.setHtml(fig.to_html(include_plotlyjs='cdn'))

    def update_comparison(self, df_c, df_b):
        merged = pd.merge(df_c, df_b, on="Benzersiz_Kimlik", how="inner", suffixes=('_cur', '_base'))
        merged['Start_Delay'] = (merged['Başlangıç_Date_cur'] - merged['Başlangıç_Date_base']).dt.days
        merged['Finish_Delay'] = (merged['Bitiş_Date_cur'] - merged['Bitiş_Date_base']).dt.days
        merged['Dur_Diff'] = merged['Süre_Num_cur'] - merged['Süre_Num_base']
        
        # --- KRİTİK FİLTRESİ (Bolluk <= 30) ---
        # Önce sadece 30 günden az bolluğu olanları (kritik ve yakını) alıyoruz
        risky_tasks = merged[merged['Bolluk_Num_cur'] <= 30]

        fig = make_subplots(rows=2, cols=2, subplot_titles=("Başlaması Gecikenler (Bolluk<=30)", "Bitmesi Gecikenler (Bolluk<=30)", 
                                                            "Süresi Kısılanlar (Bolluk<=30)", "Kritikliği Artanlar (Bolluk<=30)"),
                            specs=[[{"type": "table"}, {"type": "table"}], [{"type": "table"}, {"type": "table"}]])

        # Tablo Fonksiyonu
        def add_comp_table(data, sort_col, asc, col_idx, row_idx, val_col, header_txt):
            # Filtrelenmiş data üzerinden sıralama ve top 10 al
            top_data = data.sort_values(sort_col, ascending=asc).head(10)
            fig.add_trace(go.Table(
                header=dict(values=["Aktivite", header_txt, "Mevcut Bolluk"], fill_color='#34495e', font=dict(color='white')),
                cells=dict(values=[top_data['Ad_cur'].str.slice(0,25), top_data[val_col], top_data['Bolluk_Num_cur']],
                           fill_color='#ecf0f1', font=dict(color='black'))
            ), row=row_idx, col=col_idx)

        # 1. Başlaması Gecikenler (Start_Delay > 0)
        add_comp_table(risky_tasks[risky_tasks['Start_Delay'] > 0], 'Start_Delay', False, 1, 1, 'Start_Delay', "Gecikme (Gün)")
        
        # 2. Bitmesi Gecikenler (Finish_Delay > 0)
        add_comp_table(risky_tasks[risky_tasks['Finish_Delay'] > 0], 'Finish_Delay', False, 2, 1, 'Finish_Delay', "Öteleme (Gün)")

        # 3. Süresi Kısılanlar (Dur_Diff < 0)
        add_comp_table(risky_tasks[risky_tasks['Dur_Diff'] < 0], 'Dur_Diff', True, 1, 2, 'Dur_Diff', "Kısalma (Gün)")

        # 4. Kritikliği Artanlar (Bolluk Azalanlar) -> Bolluk Farkı
        merged['Slack_Diff'] = merged['Bolluk_Num_cur'] - merged['Bolluk_Num_base']
        # Burada yine ana listeden filtreleyelim ama bolluk farkı negatif olanları alacağız
        # Not: risky_tasks zaten bolluğu düşük olanlar, bir de bolluğu eskiye göre düşmüş olanları arıyoruz
        worsening = risky_tasks[risky_tasks['Slack_Diff'] < 0]
        add_comp_table(worsening, 'Slack_Diff', True, 2, 2, 'Slack_Diff', "Bolluk Kaybı")

        fig.update_layout(height=800, margin=dict(l=10, r=10, t=40, b=10), font={'family': "Segoe UI"})
        self.web_comp.setHtml(fig.to_html(include_plotlyjs='cdn'))

    def update_gantt(self, df):
        data = df[(df['Özet']=='Evet') & (df['Kritik']==True)]
        if data.empty: 
            self.web_gantt.setHtml("<h3>Veri yok</h3>")
            return
        fig = px.timeline(data, x_start="Başlangıç_Date", x_end="Bitiş_Date", y="Ad", color="Tamamlanma_Yüzdesi", color_continuous_scale="Reds")
        fig.update_yaxes(autorange="reversed")
        self.web_gantt.setHtml(fig.to_html(include_plotlyjs='cdn'))

    def update_timeline(self, df):
        data = df[(df['Özet']=='Evet') & (df['Kritik']==True)]
        if data.empty: 
            self.web_time.setHtml("<h3>Veri yok</h3>")
            return
        fig = px.scatter(data, x="Bitiş_Date", y="Ad", size="Süre_Num", color="Tamamlanma_Yüzdesi")
        fig.update_yaxes(autorange="reversed")
        for i, r in data.iterrows():
            fig.add_shape(type="line", x0=r['Başlangıç_Date'], x1=r['Bitiş_Date'], y0=r['Ad'], y1=r['Ad'], line=dict(color='gray'))
        self.web_time.setHtml(fig.to_html(include_plotlyjs='cdn'))

    def update_notes(self, df_cur, df_base):
        html = """
        <html><head><style>
            body { font-family: 'Segoe UI'; padding: 20px; color: #2c3e50; }
            h2 { border-bottom: 2px solid #3498db; padding-bottom: 5px; color: #2980b9; }
            h3 { color: #c0392b; margin-top: 20px; }
            .highlight { background: #f1c40f; padding: 2px 5px; border-radius: 3px; font-weight: bold; }
            li { margin-bottom: 8px; }
        </style></head><body>
        """
        
        # --- BÖLÜM 1: STANDART NOTLAR (Eski Sürümden) ---
        html += "<h2>🤖 Proje Analiz Raporu</h2>"
        
        crit = df_cur[df_cur['Kritik']==True]
        if crit.empty:
            html += "<p style='color:green'><b>✅ DURUM İYİ:</b> Projede kritik hat üzerinde aktif bir risk görünmemektedir.</p>"
        else:
            html += f"<p>Proje bitişini tehdit eden <b>{len(crit)}</b> adet kritik görev aktiftir.</p>"
            html += "<h3>⚠️ Takip Edilmesi Gereken Top 5 İş</h3><ul>"
            for _, r in crit.sort_values('Başlangıç_Date').head(5).iterrows():
                html += f"<li><b>{r['Ad']}</b> (Bitiş: {r['Bitiş_Date'].strftime('%d-%m')})</li>"
            html += "</ul>"

        today = pd.Timestamp.now()
        delayed = df_cur[(df_cur['Bitiş_Date'] < today) & (df_cur['Tamamlanma_Yüzdesi'] < 1.0)]
        if not delayed.empty:
            html += "<h3>🚫 Gecikmiş Aktiviteler</h3><ul>"
            for _, r in delayed.head(5).iterrows():
                d = (today - r['Bitiş_Date']).days
                html += f"<li><b>{r['Ad']}</b> - <span class='highlight'>{d} Gün Gecikme</span></li>"
            html += "</ul>"

        # --- BÖLÜM 2: KIYAS NOTLARI (Sadece Baseline Varsa) ---
        if df_base is not None:
            merged = pd.merge(df_cur, df_base, on="Benzersiz_Kimlik", how="inner", suffixes=('_cur', '_base'))
            merged['Dur_Diff'] = merged['Süre_Num_cur'] - merged['Süre_Num_base']
            merged['Slack_Diff'] = merged['Bolluk_Num_cur'] - merged['Bolluk_Num_base']
            merged['Finish_Delay'] = (merged['Bitiş_Date_cur'] - merged['Bitiş_Date_base']).dt.days

            html += "<br><hr>"
            html += "<h2>⚖️ Baseline Karşılaştırma Analizi</h2>"

            # 1. Süresi Kısılanlar (Duration Compression)
            # Süresi azalmış VE (Gecikmesi olmayan veya Gecikmesi Süre Kısılması kadar olmayanlar)
            compressed = merged[merged['Dur_Diff'] < 0]
            if not compressed.empty:
                html += "<h3>⚡ Süresi Kısılarak Hızlandırılan Aktiviteler</h3>"
                html += "<p>Aşağıdaki aktivitelerin süreleri Baseline'a göre kısaltılmıştır. Bu durum, gecikmeleri telafi etmek için yapılan bir 'Crashing' (Süre sıkıştırma) hamlesi olabilir:</p><ul>"
                for _, r in compressed.sort_values('Dur_Diff').head(5).iterrows():
                    html += f"<li><b>{r['Ad_cur']}</b>: {abs(r['Dur_Diff'])} gün kısıldı. (Yeni Süre: {r['Süre_Num_cur']} gün)</li>"
                html += "</ul>"
            
            # 2. Kritikliği Artanlar
            more_critical = merged[(merged['Slack_Diff'] < 0) & (merged['Bolluk_Num_cur'] <= 10)]
            if not_critical.empty:
                html += "<h3>🔥 Kritikliği Artan (Riskli) İşler</h3>"
                html += "<p>Aşağıdaki işlerin 'Bolluk' değerleri Baseline'a göre azalmıştır. Bu işler artık kritik yola çok daha yakın:</p><ul>"
                for _, r in more_critical.sort_values('Slack_Diff').head(5).iterrows():
                    html += f"<li><b>{r['Ad_cur']}</b>: Bolluk {abs(r['Slack_Diff'])} gün azaldı. (Mevcut Bolluk: {r['Bolluk_Num_cur']} gün)</li>"
                html += "</ul>"

            # 3. İyileşen Gecikmeler (Negatif Delay)
            recovered = merged[merged['Finish_Delay'] < 0]
            if not recovered.empty:
                 html += "<h3>✅ Planlanandan Erken Bitenler (Kazanım)</h3>"
                 html += f"<p>Toplam <b>{len(recovered)}</b> aktivite Baseline tarihlerinden daha erken tamamlanmıştır/planlanmıştır.</p>"

        html += "</body></html>"
        self.txt_notes.setHtml(html)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ProjectApp()
    window.show()
    sys.exit(app.exec())
