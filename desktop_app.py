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
                             QGridLayout, QFrame, QTextEdit, QHBoxLayout, QScrollArea)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import Qt

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

# --- STİL KARTLARI (KPI KUTULARI İÇİN) ---
class KPICard(QFrame):
    def __init__(self, title, value, color="#0078D7"):
        super().__init__()
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border-radius: 10px;
                border: 1px solid #e0e0e0;
            }}
        """)
        layout = QVBoxLayout()
        
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("color: #666; font-size: 14px; border: none;")
        layout.addWidget(lbl_title)
        
        lbl_value = QLabel(value)
        lbl_value.setStyleSheet(f"color: {color}; font-size: 24px; font-weight: bold; border: none;")
        layout.addWidget(lbl_value)
        
        self.setLayout(layout)

# --- ANA PENCERE ---
class ProjectApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Proje Yönetim Paneli - Dashboard v2.0")
        self.setGeometry(100, 100, 1400, 900)
        self.setStyleSheet("background-color: #f5f7fa;")

        # Ana Widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        self.main_layout = QVBoxLayout()
        main_widget.setLayout(self.main_layout)

        # Üst Bar (Dosya Yükleme)
        top_bar = QHBoxLayout()
        self.status_label = QLabel("Lütfen Veri Yükleyin")
        self.status_label.setStyleSheet("font-size: 14px; color: #333;")
        
        btn_load = QPushButton("📂 Proje Dosyası Yükle")
        btn_load.clicked.connect(self.load_file)
        btn_load.setStyleSheet("""
            QPushButton {
                background-color: #2c3e50; color: white; padding: 8px 15px; 
                border-radius: 5px; font-weight: bold;
            }
            QPushButton:hover { background-color: #34495e; }
        """)
        
        top_bar.addWidget(self.status_label)
        top_bar.addStretch()
        top_bar.addWidget(btn_load)
        self.main_layout.addLayout(top_bar)

        # Sekmeler
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #ccc; background: white; }
            QTabBar::tab { background: #e0e0e0; padding: 10px; margin-right: 2px; }
            QTabBar::tab:selected { background: #fff; border-bottom: 2px solid #0078D7; font-weight: bold; }
        """)
        self.main_layout.addWidget(self.tabs)

        # Sekme İçeriklerini Hazırla (Boş Olarak)
        self.setup_dashboard_tab()
        self.setup_summary_gantt_tab()
        self.setup_timeline_tab()
        self.setup_insights_tab()

    def setup_dashboard_tab(self):
        self.dash_tab = QWidget()
        self.dash_layout = QVBoxLayout()
        self.dash_tab.setLayout(self.dash_layout)
        
        # KPI Alanı (Dinamik eklenecek)
        self.kpi_layout = QHBoxLayout()
        self.dash_layout.addLayout(self.kpi_layout)
        
        # Grafik Alanı
        self.dash_webview = QWebEngineView()
        self.dash_layout.addWidget(self.dash_webview)
        
        self.tabs.addTab(self.dash_tab, "🚀 Dashboard")

    def setup_summary_gantt_tab(self):
        self.gantt_view = QWebEngineView()
        self.tabs.addTab(self.gantt_view, "📅 Kritik Özet Gantt")

    def setup_timeline_tab(self):
        self.timeline_view = QWebEngineView()
        self.tabs.addTab(self.timeline_view, "⏳ Kritik Timeline")

    def setup_insights_tab(self):
        self.insights_text = QTextEdit()
        self.insights_text.setReadOnly(True)
        self.insights_text.setStyleSheet("font-size: 16px; padding: 20px; line-height: 1.5;")
        self.tabs.addTab(self.insights_text, "🤖 Otomatik Analiz & Notlar")

    def load_file(self):
        file_filter = "Data Files (*.csv *.xlsx);; CSV (*.csv);; Excel (*.xlsx)"
        file_path, _ = QFileDialog.getOpenFileName(self, "Proje Dosyasını Seç", "", file_filter)

        if file_path:
            try:
                self.process_data(file_path)
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Veri işlenirken hata oluştu:\n{str(e)}")

    def process_data(self, file_path):
        # 1. Veri Okuma
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)

        # 2. Veri Temizleme
        if 'Başlangıç' not in df.columns:
            QMessageBox.warning(self, "Uyarı", "'Başlangıç' sütunu bulunamadı!")
            return

        df['Başlangıç_Date'] = df['Başlangıç'].apply(parse_turkish_date)
        df['Bitiş_Date'] = df['Bitiş'].apply(parse_turkish_date)
        df['Süre_Num'] = df['Süre'].apply(clean_duration)
        df['Bolluk_Num'] = df['Toplam_Bolluk'].apply(clean_duration)
        df['Kritik'] = df['Bolluk_Num'] <= 0
        df['Durum'] = df.apply(lambda x: 'Kritik' if x['Kritik'] else 'Normal', axis=1)

        self.status_label.setText(f"Aktif Dosya: {os.path.basename(file_path)}")
        
        # --- SEKME 1: DASHBOARD OLUŞTURMA ---
        self.create_dashboard(df)
        
        # --- SEKME 2: KRİTİK ÖZET GANTT ---
        self.create_summary_gantt(df)
        
        # --- SEKME 3: TİMELINE ---
        self.create_timeline(df)
        
        # --- SEKME 4: NOTLAR ---
        self.generate_insights(df)

    def create_dashboard(self, df):
        # A. KPI Hesaplamaları
        today = pd.Timestamp.now()
        start_date = df['Başlangıç_Date'].min()
        finish_date = df['Bitiş_Date'].max()
        
        total_days = (finish_date - start_date).days
        elapsed_days = (today - start_date).days
        remaining_days = (finish_date - today).days
        
        if elapsed_days < 0: elapsed_days = 0
        if remaining_days < 0: remaining_days = 0
        
        # Ortalama tamamlanma yüzdesi
        avg_progress = df['Tamamlanma_Yüzdesi'].mean() * 100
        
        # Süresel ilerleme yüzdesi
        time_progress = 0
        if total_days > 0:
            time_progress = (elapsed_days / total_days) * 100
            if time_progress > 100: time_progress = 100

        # KPI Widgetlarını Temizle ve Ekle
        for i in reversed(range(self.kpi_layout.count())): 
            self.kpi_layout.itemAt(i).widget().setParent(None)

        self.kpi_layout.addWidget(KPICard("Toplam Süre", f"{total_days} Gün"))
        self.kpi_layout.addWidget(KPICard("Geçen Süre", f"{elapsed_days} Gün", "#FF9800"))
        self.kpi_layout.addWidget(KPICard("Kalan Süre", f"{remaining_days} Gün", "#4CAF50"))
        self.kpi_layout.addWidget(KPICard("Fiziksel İlerleme", f"%{avg_progress:.1f}", "#9C27B0"))
        self.kpi_layout.addWidget(KPICard("Süresel İlerleme", f"%{time_progress:.1f}", "#E91E63"))

        # B. Dashboard Grafikleri (Subplots ile Birleşik Görünüm)
        fig = make_subplots(
            rows=2, cols=2,
            column_widths=[0.4, 0.6],
            row_heights=[0.5, 0.5],
            specs=[[{"type": "indicator"}, {"type": "table", "rowspan": 2}],
                   [{"type": "domain"},     None]], # 2. sütun tablo olduğu için birleştirildi
            subplot_titles=("İlerleme Durumu (Gauge)", "Kritik Aktivite Takip Listesi", "Aktivite Durum Dağılımı")
        )

        # 1. Gauge Chart (Hız Göstergesi)
        fig.add_trace(go.Indicator(
            mode = "gauge+number",
            value = avg_progress,
            title = {'text': "Genel İlerleme %"},
            gauge = {
                'axis': {'range': [None, 100]},
                'bar': {'color': "#0078D7"},
                'steps': [
                    {'range': [0, 50], 'color': "lightgray"},
                    {'range': [50, 85], 'color': "gray"}],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': time_progress} # Hedef çizgi (Süresel ilerleme)
            }
        ), row=1, col=1)

        # 2. Pie Chart (Kritik vs Normal)
        crit_counts = df['Durum'].value_counts()
        fig.add_trace(go.Pie(
            labels=crit_counts.index, 
            values=crit_counts.values,
            hole=.4,
            marker_colors=["#FF4B4B", "#1C83E1"]
        ), row=2, col=1)

        # 3. Tabloları Hazırla
        # Tablo 1: Şu an Devam Eden Kritikler (Start <= Today <= Finish)
        current_crit = df[
            (df['Kritik'] == True) & 
            (df['Başlangıç_Date'] <= today) & 
            (df['Bitiş_Date'] >= today)
        ].head(8)

        # Tablo 2: Gelecek Hafta Kritikler (Start <= Today+7) ve Henüz Bitmemiş
        next_week = today + timedelta(days=7)
        future_crit = df[
            (df['Kritik'] == True) & 
            (df['Başlangıç_Date'] <= next_week) & 
            (df['Bitiş_Date'] >= today)
        ].head(8)

        # Tablo verilerini birleştirip HTML formatında gösterelim
        # Plotly table yerine daha temiz bir HTML tablo stringi oluşturmak daha esnek olabilir
        # Ancak subplot içinde table kullanmak istedik.
        
        # İki tabloyu alt alta birleştirip tek tabloda gösterelim (Tip sütunu ekleyerek)
        current_crit['Liste_Tipi'] = "🔴 ŞU AN AKTİF"
        future_crit['Liste_Tipi'] = "📅 GELECEK HAFTA"
        
        combined_table = pd.concat([current_crit, future_crit])
        
        if combined_table.empty:
            table_header = ["Bilgi"]
            table_cells = [["Kritik aktivite bulunamadı"]]
        else:
            table_header = ["Durum", "Aktivite Adı", "Bitiş", "% Tam."]
            table_cells = [
                combined_table['Liste_Tipi'],
                combined_table['Ad'].str.slice(0, 30), # İsimleri kısalt
                combined_table['Bitiş_Date'].dt.strftime('%d-%m-%Y'),
                (combined_table['Tamamlanma_Yüzdesi']*100).map('{:.0f}%'.format)
            ]

        fig.add_trace(go.Table(
            header=dict(values=table_header, fill_color='#2c3e50', font=dict(color='white', size=12)),
            cells=dict(values=table_cells, fill_color='#ecf0f1', font=dict(color='black', size=11), height=30)
        ), row=1, col=2)

        fig.update_layout(height=650, margin=dict(l=10, r=10, t=40, b=10))
        self.dash_webview.setHtml(fig.to_html(include_plotlyjs='cdn'))

    def create_summary_gantt(self, df):
        # Sadece Özet (Summary) VE İçinde Kritik iş olanları (Genelde MS Project özeti de kritik işaretler)
        # Özet sütunu 'Evet' olanlar ve Kritik olanlar
        summary_crit = df[(df['Özet'] == 'Evet') & (df['Kritik'] == True)].copy()
        
        if summary_crit.empty:
            self.gantt_view.setHtml("<h3>Görüntülenecek Kritik Özet Aktivite Bulunamadı.</h3>")
            return

        fig = px.timeline(
            summary_crit, 
            x_start="Başlangıç_Date", 
            x_end="Bitiş_Date", 
            y="Ad",
            color="Tamamlanma_Yüzdesi",
            title="Kritik Özet Aktiviteler Gantt Şeması",
            color_continuous_scale="RdBu"
        )
        fig.update_yaxes(autorange="reversed")
        fig.update_layout(height=700)
        self.gantt_view.setHtml(fig.to_html(include_plotlyjs='cdn'))

    def create_timeline(self, df):
        summary_crit = df[(df['Özet'] == 'Evet') & (df['Kritik'] == True)].copy()
        
        if summary_crit.empty:
            self.timeline_view.setHtml("<h3>Veri yok.</h3>")
            return

        # Timeline görünümü için scatter plot kullanımı daha şık olabilir
        fig = px.scatter(
            summary_crit,
            x="Bitiş_Date",
            y="Ad",
            color="Tamamlanma_Yüzdesi",
            size="Süre_Num",
            title="Kritik Kilometre Taşları (Timeline)",
            labels={"Bitiş_Date": "Hedef Tarih"}
        )
        # Çizgiler ekleyelim
        for i, row in summary_crit.iterrows():
            fig.add_shape(
                type="line",
                x0=row['Başlangıç_Date'], y0=row['Ad'],
                x1=row['Bitiş_Date'], y1=row['Ad'],
                line=dict(color="gray", width=1)
            )

        fig.update_yaxes(autorange="reversed")
        fig.update_layout(height=700)
        self.timeline_view.setHtml(fig.to_html(include_plotlyjs='cdn'))

    def generate_insights(self, df):
        notes = []
        notes.append("<h2>🤖 Proje Otomatik Analiz Raporu</h2>")
        notes.append("<ul>")

        # 1. Genel Durum
        total = len(df)
        completed = len(df[df['Tamamlanma_Yüzdesi'] == 1.0])
        notes.append(f"<li>Projede toplam <b>{total}</b> aktivite bulunmaktadır. Bunların <b>{completed}</b> tanesi (%{(completed/total*100):.1f}) tamamlanmıştır.</li>")

        # 2. Kritik Yol Analizi
        crit_count = len(df[df['Kritik'] == True])
        notes.append(f"<li>Projenin kaderini belirleyen <b>{crit_count}</b> adet Kritik Aktivite tespit edilmiştir. Bu aktivitelerdeki 1 günlük gecikme, proje bitişini 1 gün öteleyecektir.</li>")

        # 3. En Uzun Süreli Kritik İş
        crit_df = df[df['Kritik'] == True]
        if not crit_df.empty:
            longest_crit = crit_df.loc[crit_df['Süre_Num'].idxmax()]
            notes.append(f"<li>Kritik yol üzerindeki en uzun süreli iş: <b>'{longest_crit['Ad']}'</b> ({longest_crit['Süre']}). Bu aktiviteye ekstra kaynak atanması süreyi kısaltabilir.</li>")

            # 4. Proje Bitişini Belirleyen İş
            last_task = crit_df.loc[crit_df['Bitiş_Date'].idxmax()]
            notes.append(f"<li>Projenin bitiş tarihini belirleyen son aktivite: <b>'{last_task['Ad']}'</b> (Bitiş: {last_task['Bitiş_Date'].strftime('%d-%m-%Y')}).</li>")

        # 5. Gecikme Riski (Basit bir mantık: Geçmişte başlayıp bitmemiş işler)
        today = pd.Timestamp.now()
        delayed = df[(df['Bitiş_Date'] < today) & (df['Tamamlanma_Yüzdesi'] < 1.0)]
        if not delayed.empty:
            notes.append(f"<li>⚠️ <b>DİKKAT:</b> Planlanan bitiş tarihi geçmiş olmasına rağmen tamamlanmamış <b>{len(delayed)}</b> aktivite bulunmaktadır. Acil müdahale gerektirir.</li>")
        else:
            notes.append(f"<li>✅ Şu an itibariyle planlanan tarihe göre gecikmiş (tamamlanmamış) aktivite görünmemektedir.</li>")

        # 6. Önümüzdeki Yoğunluk
        next_week = today + timedelta(days=7)
        upcoming = df[(df['Başlangıç_Date'] > today) & (df['Başlangıç_Date'] <= next_week)]
        notes.append(f"<li>Önümüzdeki 7 gün içinde başlaması gereken <b>{len(upcoming)}</b> yeni aktivite bulunmaktadır. Kaynak planlamasını kontrol ediniz.</li>")

        notes.append("</ul>")
        notes.append("<p><i>*Bu rapor yüklenen veriler üzerinden algoritmik olarak oluşturulmuştur.</i></p>")

        self.insights_text.setHtml("".join(notes))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ProjectApp()
    window.show()
    sys.exit(app.exec())
