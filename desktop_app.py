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
    if not isinstance(date_str, str) or date_str == "Yok": return pd.NaT
    tr_months = {"Ocak":"January", "Şubat":"February", "Mart":"March", "Nisan":"April", "Mayıs":"May", "Haziran":"June", "Temmuz":"July", "Ağustos":"August", "Eylül":"September", "Ekim":"October", "Kasım":"November", "Aralık":"December"}
    for tr, en in tr_months.items():
        if tr in date_str:
            date_str = date_str.replace(tr, en)
            break
    try: return pd.to_datetime(date_str)
    except: return pd.NaT

def clean_duration(val):
    if isinstance(val, str):
        val = val.lower().replace(" gün", "").replace("g", "").replace(" ", "")
        try: return float(val)
        except: return 0.0
    return val

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
        self.setWindowTitle("Proje Kontrol Merkezi v7.0")
        self.setGeometry(100, 100, 1600, 900)
        self.setStyleSheet(STYLE_SHEET)

        # İKONU AYARLA
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

        # 3. Gantt
        self.web_gantt = QWebEngineView(); self.tabs.addTab(self.web_gantt, "📅 Kritik Hat (Gantt)")

        # 4. Timeline
        self.web_time = QWebEngineView(); self.tabs.addTab(self.web_time, "⏳ Zaman Çizelgesi")

        # 5. Notlar (Senin istediğin Stil)
        self.txt_notes = QTextEdit(); self.txt_notes.setReadOnly(True)
        self.txt_notes.setStyleSheet("""
            QTextEdit {
                background-color: white; color: black; font-size: 15px; 
                padding: 15px; border: none;
            }
        """)
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
        df['Başlangıç_Date'] = df['Başlangıç'].apply(parse_turkish_date)
        df['Bitiş_Date'] = df['Bitiş'].apply(parse_turkish_date)
        df['Süre_Num'] = df['Süre'].apply(clean_duration)
        df['Bolluk_Num'] = df['Toplam_Bolluk'].apply(clean_duration)
        df['Kritik'] = (df['Bolluk_Num'] <= 0) & (df['Tamamlanma_Yüzdesi'] < 1.0)
        df['Durum'] = df.apply(lambda x: 'Kritik' if x['Kritik'] else ('Tamamlandı' if x['Tamamlanma_Yüzdesi'] == 1.0 else 'Normal'), axis=1)
        return df

    def refresh_ui(self):
        if self.df_current is None: return
        self.update_dashboard(self.df_current)
        self.update_gantt(self.df_current)
        self.update_timeline(self.df_current)
        # Notları üret (Baseline varsa o da gidiyor)
        self.generate_insights(self.df_current, self.df_baseline)
        
        if self.df_baseline is not None: 
            self.update_comparison(self.df_current, self.df_baseline)

    def update_dashboard(self, df):
        # KPI Temizle
        for i in reversed(range(self.kpi_layout.count())): self.kpi_layout.itemAt(i).widget().setParent(None)
        
        today = pd.Timestamp.now(); start = df['Başlangıç_Date'].min(); finish = df['Bitiş_Date'].max()
        total = (finish-start).days; elapsed = max(0, (today-start).days)
        summ = df[df['Benzersiz_Kimlik']==1]; prog = summ.iloc[0]['Tamamlanma_Yüzdesi']*100 if not summ.empty else df['Tamamlanma_Yüzdesi'].mean()*100
        
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
        # 1. Veri Birleştirme
        merged = pd.merge(df_c, df_b, on="Benzersiz_Kimlik", how="inner", suffixes=('_cur', '_base'))
        
        # 2. Fark Hesaplama
        merged['Start_Delay'] = (merged['Başlangıç_Date_cur'] - merged['Başlangıç_Date_base']).dt.days
        merged['Finish_Delay'] = (merged['Bitiş_Date_cur'] - merged['Bitiş_Date_base']).dt.days
        merged['Dur_Diff'] = merged['Süre_Num_cur'] - merged['Süre_Num_base'] # Negatif = Kısaldı
        merged['Slack_Diff'] = merged['Bolluk_Num_cur'] - merged['Bolluk_Num_base'] # Negatif = Kritikleşti
        
        # 3. İSTEK: Sadece Bolluğu 30 ve Altında Olanları Göster
        # Bu filtre ana filtre olsun, böylece sadece riskli işleri kıyaslayalım.
        risky_pool = merged[merged['Bolluk_Num_cur'] <= 30]

        # Grafik Hazırlığı
        fig = make_subplots(
            rows=2, cols=2, 
            subplot_titles=(
                "Başlaması Gecikenler (Bolluk<=30)", 
                "Bitmesi Gecikenler (Bolluk<=30)", 
                "Süresi Kısılanlar (Bolluk<=30)", 
                "Kritikliği Artanlar (Bolluk<=30)"
            ),
            specs=[[{"type": "table"}, {"type": "table"}], [{"type": "table"}, {"type": "table"}]]
        )

        def add_comp_table(data, sort_col, asc, col_idx, row_idx, val_col, header):
            # Veri boşsa bile tabloyu boş da olsa çizelim ki grafik bozulmasın
            if data.empty:
                headers = ["Bilgi"]
                cells = [["Kriterlere uygun veri yok"]]
            else:
                top = data.sort_values(sort_col, ascending=asc).head(10)
                headers = ["Aktivite", header, "Bolluk"]
                # İsimleri biraz kısaltalım
                cells = [top['Ad_cur'].str.slice(0, 25), top[val_col], top['Bolluk_Num_cur']]

            fig.add_trace(go.Table(
                header=dict(values=headers, fill_color='#2c3e50', font=dict(color='white')),
                cells=dict(values=cells, fill_color='#ecf0f1', font=dict(color='black'))
            ), row=row_idx, col=col_idx)

        # Tablo 1: Başlaması Gecikenler
        add_comp_table(risky_pool[risky_pool['Start_Delay'] > 0], 'Start_Delay', False, 1, 1, 'Start_Delay', "Gecikme (Gün)")
        
        # Tablo 2: Bitmesi Gecikenler
        add_comp_table(risky_pool[risky_pool['Finish_Delay'] > 0], 'Finish_Delay', False, 2, 1, 'Finish_Delay', "Öteleme (Gün)")
        
        # Tablo 3: Süresi Kısılanlar (Dur_Diff < 0)
        add_comp_table(risky_pool[risky_pool['Dur_Diff'] < 0], 'Dur_Diff', True, 1, 2, 'Dur_Diff', "Kısalma (Gün)")
        
        # Tablo 4: Kritikliği Artanlar (Slack_Diff < 0) - Zaten risky_pool bolluk<=30, bir de bolluk kaybı olanlara bakıyoruz
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
        # SENİN SEVDİĞİN NOT FORMATI (Aynen korundu)
        html = """
        <html>
        <head>
            <style>
                body { font-family: 'Segoe UI', sans-serif; background-color: white; color: black; padding: 20px; }
                h2 { color: #0078D7; border-bottom: 2px solid #eee; padding-bottom: 10px; }
                h3 { color: #d32f2f; margin-top: 20px; }
                h4 { color: #2c3e50; margin-top: 15px; border-left: 4px solid #0078D7; padding-left: 10px;}
                li { margin-bottom: 8px; line-height: 1.6; }
                .highlight { background-color: #fff3cd; padding: 2px 5px; border-radius: 3px; font-weight: bold; }
                .safe { color: green; font-weight: bold; }
                .danger { color: red; font-weight: bold; }
            </style>
        </head>
        <body>
        """
        html += "<h2>🤖 Akıllı Proje Analizi ve Risk Raporu</h2>"
        
        # 1. Kritik Hat Analizi
        crit_active = df_curr[df_curr['Kritik'] == True]
        
        if crit_active.empty:
            html += "<p class='safe'>✅ MÜKEMMEL: Şu anda projenin bitiş tarihini tehdit eden 'Kritik' ve 'Tamamlanmamış' aktivite bulunmamaktadır.</p>"
        else:
            html += f"<p>Şu anda proje genelinde, gecikmesi proje bitişini doğrudan öteleyecek <b>{len(crit_active)}</b> adet aktif (tamamlanmamış) kritik görev bulunmaktadır.</p>"
            
            # Kritik Görev İsimleri (Top 5)
            html += "<h3>⚠️ Dikkat Edilmesi Gereken Kritik Aktiviteler (İlk 5)</h3><ul>"
            for _, row in crit_active.sort_values(by='Başlangıç_Date').head(5).iterrows():
                html += f"<li><b>{row['Ad']}</b> (Bitiş: {row['Bitiş_Date'].strftime('%d-%m-%Y')}) - <span class='danger'>Tamamlanma: %{int(row['Tamamlanma_Yüzdesi']*100)}</span></li>"
            html += "</ul>"

        # 2. Gecikme Analizi
        today = pd.Timestamp.now()
        delayed = df_curr[(df_curr['Bitiş_Date'] < today) & (df_curr['Tamamlanma_Yüzdesi'] < 1.0)]
        
        if not delayed.empty:
            html += "<h3>🚫 Gecikmiş İşler (Acil Müdahale)</h3>"
            html += f"<p>Planlanan bitiş tarihi geçmiş olmasına rağmen henüz %100 tamamlanmamış <b>{len(delayed)}</b> aktivite tespit edilmiştir.</p>"
            html += "<ul>"
            for _, row in delayed.head(5).iterrows():
                delay_days = (today - row['Bitiş_Date']).days
                html += f"<li><b>{row['Ad']}</b> - <span class='highlight'>{delay_days} Gün Gecikmiş</span></li>"
            html += "</ul>"
        
        # 3. Darboğaz Tahmini (Mevcut kodundan)
        if not crit_active.empty:
            longest = crit_active.loc[crit_active['Süre_Num'].idxmax()]
            html += "<h3>🔗 Potansiyel Darboğaz</h3>"
            html += f"<p>Kritik hat üzerindeki en uzun süreli aktivite: <b>{longest['Ad']}</b> ({longest['Süre']}). Bu aktivitedeki verimlilik kaybı projenin genelini en çok etkileyecek faktördür.</p>"

        # 4. Genel Tavsiye (Mevcut kodundan)
        summary_row = df_curr[df_curr['Benzersiz_Kimlik'] == 1]
        progress = summary_row.iloc[0]['Tamamlanma_Yüzdesi']*100 if not summary_row.empty else df_curr['Tamamlanma_Yüzdesi'].mean()*100
        
        html += "<h3>💡 Yönetici Özeti</h3>"
        if progress < 50:
            html += "<p>Proje henüz ilk yarıdadır. Kritik hat üzerindeki kaynak planlamasını sıkı tutarak ileriki aşamalardaki sapmaları önleyebilirsiniz.</p>"
        elif progress >= 50 and not crit_active.empty:
            html += "<p>Proje yarıyı geçmiştir ancak kritik aktiviteler devam etmektedir. Odaklanılması gereken nokta, yukarıda listelenen kritik işlerin günlük takibidir.</p>"
        else:
            html += "<p>Proje son aşamalara yaklaşmaktadır ve kritik riskler minimize edilmiştir.</p>"

        # --- BÖLÜM 2: KIYAS RAPORU (Sadece Baseline Varsa Eklenir) ---
        if df_base is not None:
            merged = pd.merge(df_curr, df_base, on="Benzersiz_Kimlik", how="inner", suffixes=('_cur', '_base'))
            
            # Fark Hesapları
            merged['Dur_Diff'] = merged['Süre_Num_cur'] - merged['Süre_Num_base']
            merged['Slack_Diff'] = merged['Bolluk_Num_cur'] - merged['Bolluk_Num_base']
            merged['Start_Delay'] = (merged['Başlangıç_Date_cur'] - merged['Başlangıç_Date_base']).dt.days
            merged['Finish_Delay'] = (merged['Bitiş_Date_cur'] - merged['Bitiş_Date_base']).dt.days

            html += "<br><hr>"
            html += "<h2>⚖️ Baseline Karşılaştırma Raporu</h2>"
            
            # Gecikme Özet
            delayed_starts = len(merged[merged['Start_Delay'] > 0])
            delayed_finishes = len(merged[merged['Finish_Delay'] > 0])
            html += f"<p>Baseline programa göre <b>{delayed_starts}</b> aktivitenin başlangıcı, <b>{delayed_finishes}</b> aktivitenin bitişi ötelenmiştir.</p>"
            
            # 1. Süresi Kısılanlar
            compressed = merged[merged['Dur_Diff'] < 0]
            if not compressed.empty:
                html += "<h3>⚡ Hızlandırılan (Süresi Kısılan) İşler</h3>"
                html += "<p>Aşağıdaki aktivitelerin süreleri Baseline'a göre kısaltılmıştır:</p><ul>"
                for _, r in compressed.sort_values('Dur_Diff').head(5).iterrows():
                    html += f"<li><b>{r['Ad_cur']}</b>: {abs(r['Dur_Diff'])} gün kısıldı.</li>"
                html += "</ul>"
            
            # 2. Kritikliği Artanlar (Riskli Olanlar)
            # Bolluk <= 30 olanlar arasından bolluk kaybı yaşayanlar
            risky_worsening = merged[(merged['Slack_Diff'] < 0) & (merged['Bolluk_Num_cur'] <= 30)]
            if not risky_worsening.empty:
                html += "<h3>🔥 Kritikliği Artan (Riskli) İşler</h3>"
                html += "<p>Aşağıdaki işlerin bolluk süreleri Baseline'a göre azalmıştır ve şu an 30 günün altındadır:</p><ul>"
                for _, r in risky_worsening.sort_values('Slack_Diff').head(5).iterrows():
                    html += f"<li><b>{r['Ad_cur']}</b>: Bolluk {abs(r['Slack_Diff'])} gün azaldı. (Mevcut Bolluk: {r['Bolluk_Num_cur']})</li>"
                html += "</ul>"

        html += "</body></html>"
        self.insights_text.setHtml(html)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ProjectApp()
    window.show()
    sys.exit(app.exec())
