import sys
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import re
import os
from datetime import datetime, timedelta

from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget, 
                             QPushButton, QFileDialog, QLabel, QTabWidget, QMessageBox, 
                             QTextEdit, QHBoxLayout, QFrame)
from PyQt6.QtWebEngineWidgets import QWebEngineView

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

# --- STİL KARTLARI ---
class KPICard(QFrame):
    def __init__(self, title, value, color="#0078D7"):
        super().__init__()
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border-radius: 8px;
                border: 1px solid #ddd;
                padding: 10px;
            }}
        """)
        layout = QVBoxLayout()
        layout.setContentsMargins(5,5,5,5)
        
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("color: #555; font-size: 13px; border: none;")
        layout.addWidget(lbl_title)
        
        lbl_value = QLabel(value)
        lbl_value.setStyleSheet(f"color: {color}; font-size: 22px; font-weight: bold; border: none;")
        layout.addWidget(lbl_value)
        
        self.setLayout(layout)

# --- ANA PENCERE ---
class ProjectApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Proje Yönetim Paneli - Dashboard v3.0")
        self.setGeometry(100, 100, 1400, 900)
        self.setStyleSheet("background-color: #f4f6f9; font-family: Segoe UI, sans-serif;")

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        self.main_layout = QVBoxLayout()
        main_widget.setLayout(self.main_layout)

        # Üst Bar
        top_bar = QHBoxLayout()
        self.status_label = QLabel("Lütfen Veri Yükleyin")
        self.status_label.setStyleSheet("font-size: 14px; color: #333; font-weight: bold;")
        
        btn_load = QPushButton("📂 Proje Dosyası Yükle")
        btn_load.clicked.connect(self.load_file)
        btn_load.setStyleSheet("""
            QPushButton {
                background-color: #0078D7; color: white; padding: 8px 15px; 
                border-radius: 5px; font-weight: bold; border: none;
            }
            QPushButton:hover { background-color: #0063b1; }
        """)
        
        top_bar.addWidget(self.status_label)
        top_bar.addStretch()
        top_bar.addWidget(btn_load)
        self.main_layout.addLayout(top_bar)

        # Sekmeler
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #ccc; background: white; }
            QTabBar::tab { background: #e0e0e0; padding: 8px 15px; margin-right: 2px; border-top-left-radius: 4px; border-top-right-radius: 4px;}
            QTabBar::tab:selected { background: #fff; border-bottom: 2px solid #0078D7; font-weight: bold; color: #0078D7; }
        """)
        self.main_layout.addWidget(self.tabs)

        self.setup_dashboard_tab()
        self.setup_summary_gantt_tab()
        self.setup_timeline_tab()
        self.setup_insights_tab()

    def setup_dashboard_tab(self):
        self.dash_tab = QWidget()
        self.dash_layout = QVBoxLayout()
        self.dash_tab.setLayout(self.dash_layout)
        
        self.kpi_layout = QHBoxLayout()
        self.dash_layout.addLayout(self.kpi_layout)
        
        self.dash_webview = QWebEngineView()
        self.dash_layout.addWidget(self.dash_webview)
        self.tabs.addTab(self.dash_tab, "🚀 Yönetici Özeti")

    def setup_summary_gantt_tab(self):
        self.gantt_view = QWebEngineView()
        self.tabs.addTab(self.gantt_view, "📅 Kritik Hat (Gantt)")

    def setup_timeline_tab(self):
        self.timeline_view = QWebEngineView()
        self.tabs.addTab(self.timeline_view, "⏳ Kritik Zaman Çizelgesi")

    def setup_insights_tab(self):
        self.insights_text = QTextEdit()
        self.insights_text.setReadOnly(True)
        # Siyah metin, beyaz arka plan zorlaması
        self.insights_text.setStyleSheet("""
            QTextEdit {
                background-color: white; 
                color: black; 
                font-size: 15px; 
                padding: 15px;
                border: none;
            }
        """)
        self.tabs.addTab(self.insights_text, "🤖 Akıllı Proje Analizi & Notlar")

    def load_file(self):
        file_filter = "Data Files (*.csv *.xlsx);; CSV (*.csv);; Excel (*.xlsx)"
        file_path, _ = QFileDialog.getOpenFileName(self, "Proje Dosyasını Seç", "", file_filter)
        if file_path:
            try:
                self.process_data(file_path)
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Veri işlenirken hata oluştu:\n{str(e)}")

    def process_data(self, file_path):
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)

        if 'Başlangıç' not in df.columns:
            QMessageBox.warning(self, "Uyarı", "'Başlangıç' sütunu bulunamadı!")
            return

        # Veri Hazırlığı
        df['Başlangıç_Date'] = df['Başlangıç'].apply(parse_turkish_date)
        df['Bitiş_Date'] = df['Bitiş'].apply(parse_turkish_date)
        df['Süre_Num'] = df['Süre'].apply(clean_duration)
        df['Bolluk_Num'] = df['Toplam_Bolluk'].apply(clean_duration)
        
        # --- KRİTİK YOL MANTIĞI GÜNCELLEMESİ ---
        # 1. Bolluk <= 0 OLMALI
        # 2. Tamamlanma Yüzdesi < %100 OLMALI (Bitmiş iş kritik değildir)
        df['Kritik'] = (df['Bolluk_Num'] <= 0) & (df['Tamamlanma_Yüzdesi'] < 1.0)
        
        df['Durum'] = df.apply(lambda x: 'Kritik' if x['Kritik'] else ('Tamamlandı' if x['Tamamlanma_Yüzdesi'] == 1.0 else 'Normal'), axis=1)

        self.status_label.setText(f"Aktif Dosya: {os.path.basename(file_path)}")
        
        self.create_dashboard(df)
        self.create_summary_gantt(df)
        self.create_timeline(df)
        self.generate_insights(df)

    def create_dashboard(self, df):
        today = pd.Timestamp.now()
        start_date = df['Başlangıç_Date'].min()
        finish_date = df['Bitiş_Date'].max()
        
        total_days = (finish_date - start_date).days
        elapsed_days = (today - start_date).days
        remaining_days = (finish_date - today).days
        if elapsed_days < 0: elapsed_days = 0
        if remaining_days < 0: remaining_days = 0
        
        # --- İLERLEME YÜZDESİ HESABI ---
        # Önce ID=1 olan ana özeti arayalım
        project_summary = df[df['Benzersiz_Kimlik'] == 1]
        if not project_summary.empty:
            avg_progress = project_summary.iloc[0]['Tamamlanma_Yüzdesi'] * 100
        else:
            # Bulamazsa ortalama al
            avg_progress = df['Tamamlanma_Yüzdesi'].mean() * 100

        time_progress = 0
        if total_days > 0:
            time_progress = (elapsed_days / total_days) * 100
            if time_progress > 100: time_progress = 100

        # KPI Kartlarını Temizle ve Ekle
        for i in reversed(range(self.kpi_layout.count())): 
            self.kpi_layout.itemAt(i).widget().setParent(None)

        self.kpi_layout.addWidget(KPICard("Toplam Proje Süresi", f"{total_days} Gün"))
        self.kpi_layout.addWidget(KPICard("Geçen Süre", f"{elapsed_days} Gün", "#FF9800"))
        self.kpi_layout.addWidget(KPICard("Kalan Süre", f"{remaining_days} Gün", "#4CAF50"))
        self.kpi_layout.addWidget(KPICard("Gerçekleşen İlerleme", f"%{avg_progress:.1f}", "#9C27B0"))
        self.kpi_layout.addWidget(KPICard("Planlanan (Süresel)", f"%{time_progress:.1f}", "#E91E63"))

        # Grafikler
        fig = make_subplots(
            rows=2, cols=2,
            column_widths=[0.35, 0.65],
            row_heights=[0.5, 0.5],
            specs=[[{"type": "indicator"}, {"type": "table", "rowspan": 2}],
                   [{"type": "domain"},     None]],
            subplot_titles=("İlerleme Hedef Karşılaştırması", "Kritik Aktivite Takip Listesi", "Aktivite Durum Dağılımı")
        )

        # Gauge Chart
        fig.add_trace(go.Indicator(
            mode = "gauge+number+delta",
            value = avg_progress,
            delta = {'reference': time_progress, 'relative': False, "valueformat": ".1f"},
            title = {'text': "Fiziksel İlerleme %"},
            gauge = {
                'axis': {'range': [None, 100]},
                'bar': {'color': "#0078D7"},
                'steps': [{'range': [0, time_progress], 'color': "rgba(255, 0, 0, 0.1)"}], # Kırmızı alan hedeftir
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': time_progress}
            }
        ), row=1, col=1)

        # Pie Chart
        status_counts = df['Durum'].value_counts()
        colors_map = {'Kritik': '#FF4B4B', 'Normal': '#1C83E1', 'Tamamlandı': '#2ECC71'}
        fig.add_trace(go.Pie(
            labels=status_counts.index, 
            values=status_counts.values,
            hole=.4,
            marker_colors=[colors_map.get(x, '#999') for x in status_counts.index]
        ), row=2, col=1)

        # Tablolar
        active_crit = df[df['Kritik'] == True].sort_values(by='Başlangıç_Date')
        
        # Şu an aktif veya geçmişte başlamış ama bitmemiş kritik işler
        urgent_crit = active_crit[active_crit['Başlangıç_Date'] <= today].head(8)
        
        # Gelecek kritik işler
        future_crit = active_crit[active_crit['Başlangıç_Date'] > today].head(8)

        urgent_crit['Öncelik'] = "🔴 ACİL / DEVAM"
        future_crit['Öncelik'] = "📅 GELECEK"
        
        combined_table = pd.concat([urgent_crit, future_crit])
        
        if combined_table.empty:
            header = ["Bilgi"]
            cells = [["Aktif kritik iş bulunamadı."]]
        else:
            header = ["Durum", "Aktivite Adı", "Başlangıç", "Bitiş", "%"]
            cells = [
                combined_table['Öncelik'],
                combined_table['Ad'].str.slice(0, 35),
                combined_table['Başlangıç_Date'].dt.strftime('%d-%m'),
                combined_table['Bitiş_Date'].dt.strftime('%d-%m'),
                (combined_table['Tamamlanma_Yüzdesi']*100).map('{:.0f}%'.format)
            ]

        fig.add_trace(go.Table(
            header=dict(values=header, fill_color='#2c3e50', font=dict(color='white', size=11)),
            cells=dict(values=cells, fill_color=['#ecf0f1']*len(combined_table), font=dict(color='black', size=11), height=28)
        ), row=1, col=2)

        fig.update_layout(height=650, margin=dict(l=10, r=10, t=40, b=10), font=dict(family="Segoe UI"))
        self.dash_webview.setHtml(fig.to_html(include_plotlyjs='cdn'))

    def create_summary_gantt(self, df):
        # Sadece Kritik olan ve Özet olanlar
        summary_crit = df[(df['Özet'] == 'Evet') & (df['Kritik'] == True)].copy()
        
        if summary_crit.empty:
            self.gantt_view.setHtml("<h3 style='font-family:Segoe UI; padding:20px'>Şu an kritik hat üzerinde aktif bir Özet Aktivite bulunmamaktadır.</h3>")
            return

        fig = px.timeline(
            summary_crit, x_start="Başlangıç_Date", x_end="Bitiş_Date", y="Ad",
            color="Tamamlanma_Yüzdesi", title="Kritik Özet Aktiviteler",
            color_continuous_scale="Reds"
        )
        fig.update_yaxes(autorange="reversed")
        fig.update_layout(height=700, font=dict(family="Segoe UI"))
        self.gantt_view.setHtml(fig.to_html(include_plotlyjs='cdn'))

    def create_timeline(self, df):
        summary_crit = df[(df['Özet'] == 'Evet') & (df['Kritik'] == True)].copy()
        if summary_crit.empty:
            self.timeline_view.setHtml("<h3 style='font-family:Segoe UI; padding:20px'>Veri yok.</h3>")
            return

        fig = px.scatter(
            summary_crit, x="Bitiş_Date", y="Ad", color="Tamamlanma_Yüzdesi",
            size="Süre_Num", title="Kritik Timeline (Bitiş Tarihine Göre)",
            labels={"Bitiş_Date": "Hedef Tarih"}
        )
        for i, row in summary_crit.iterrows():
            fig.add_shape(type="line", x0=row['Başlangıç_Date'], y0=row['Ad'], x1=row['Bitiş_Date'], y1=row['Ad'], line=dict(color="gray", width=1))

        fig.update_yaxes(autorange="reversed")
        fig.update_layout(height=700, font=dict(family="Segoe UI"))
        self.timeline_view.setHtml(fig.to_html(include_plotlyjs='cdn'))

    def generate_insights(self, df):
        # HTML İçerik (Siyah Yazı Rengi Zorunlu)
        html = """
        <html>
        <head>
            <style>
                body { font-family: 'Segoe UI', sans-serif; background-color: white; color: black; padding: 20px; }
                h2 { color: #0078D7; border-bottom: 2px solid #eee; padding-bottom: 10px; }
                h3 { color: #d32f2f; margin-top: 20px; }
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
        crit_active = df[df['Kritik'] == True]
        
        if crit_active.empty:
            html += "<p class='safe'>✅ MÜKEMMEL: Şu anda projenin bitiş tarihini tehdit eden 'Kritik' ve 'Tamamlanmamış' aktivite bulunmamaktadır.</p>"
        else:
            html += f"<p>Şu anda proje genelinde, gecikmesi proje bitişini doğrudan öteleyecek <b>{len(crit_active)}</b> adet aktif (tamamlanmamış) kritik görev bulunmaktadır.</p>"
            
            # Kritik Görev İsimleri
            html += "<h3>⚠️ Dikkat Edilmesi Gereken Kritik Aktiviteler (İlk 5)</h3><ul>"
            for _, row in crit_active.sort_values(by='Başlangıç_Date').head(5).iterrows():
                html += f"<li><b>{row['Ad']}</b> (Bitiş: {row['Bitiş_Date'].strftime('%d-%m-%Y')}) - <span class='danger'>Tamamlanma: %{int(row['Tamamlanma_Yüzdesi']*100)}</span></li>"
            html += "</ul>"

        # 2. Gecikme Analizi (Bugün itibariyle bitmesi gereken ama bitmeyenler)
        today = pd.Timestamp.now()
        delayed = df[(df['Bitiş_Date'] < today) & (df['Tamamlanma_Yüzdesi'] < 1.0)]
        
        if not delayed.empty:
            html += "<h3>🚫 Gecikmiş İşler (Acil Müdahale)</h3>"
            html += f"<p>Planlanan bitiş tarihi geçmiş olmasına rağmen henüz %100 tamamlanmamış <b>{len(delayed)}</b> aktivite tespit edilmiştir. Bu aktiviteler projeyi geriye çekmektedir.</p>"
            html += "<ul>"
            for _, row in delayed.head(5).iterrows():
                delay_days = (today - row['Bitiş_Date']).days
                html += f"<li><b>{row['Ad']}</b> - <span class='highlight'>{delay_days} Gün Gecikmiş</span></li>"
            html += "</ul>"
        
        # 3. Darboğaz Tahmini
        # En çok öncülü/ardılı olan kritik işler (bağımlılığı yüksek)
        # Bu basit veri setinde öncüller sütununu string olarak analiz edebiliriz
        if not crit_active.empty:
             # Basitçe en uzun süreli kritik işi bulalım
            longest = crit_active.loc[crit_active['Süre_Num'].idxmax()]
            html += "<h3>🔗 Potansiyel Darboğaz</h3>"
            html += f"<p>Kritik hat üzerindeki en uzun süreli aktivite: <b>{longest['Ad']}</b> ({longest['Süre']}). Bu aktivitedeki verimlilik kaybı projenin genelini en çok etkileyecek faktördür.</p>"

        # 4. Genel Tavsiye
        summary_row = df[df['Benzersiz_Kimlik'] == 1]
        progress = summary_row.iloc[0]['Tamamlanma_Yüzdesi']*100 if not summary_row.empty else df['Tamamlanma_Yüzdesi'].mean()*100
        
        html += "<h3>💡 Yönetici Özeti</h3>"
        if progress < 50:
            html += "<p>Proje henüz ilk yarıdadır. Kritik hat üzerindeki kaynak planlamasını sıkı tutarak ileriki aşamalardaki sapmaları önleyebilirsiniz.</p>"
        elif progress >= 50 and not crit_active.empty:
            html += "<p>Proje yarıyı geçmiştir ancak kritik aktiviteler devam etmektedir. Odaklanılması gereken nokta, yukarıda listelenen kritik işlerin günlük takibidir.</p>"
        else:
            html += "<p>Proje son aşamalara yaklaşmaktadır ve kritik riskler minimize edilmiştir.</p>"

        html += "</body></html>"
        self.insights_text.setHtml(html)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ProjectApp()
    window.show()
    sys.exit(app.exec())
