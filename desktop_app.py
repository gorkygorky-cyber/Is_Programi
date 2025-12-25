import sys
import pandas as pd
import plotly.express as px
import re
import os

from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget, 
                             QPushButton, QFileDialog, QLabel, QTabWidget, QMessageBox)
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

# --- ANA PENCERE SINIFI ---
class ProjectApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Proje Yönetim Paneli v1.0")
        self.setGeometry(100, 100, 1200, 800)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout()
        main_widget.setLayout(layout)

        self.label = QLabel("Lütfen bir MS Project Excel/CSV dosyası yükleyin.")
        layout.addWidget(self.label)

        btn_load = QPushButton("Dosya Yükle")
        btn_load.clicked.connect(self.load_file)
        btn_load.setStyleSheet("font-size: 14px; padding: 10px; background-color: #0078D7; color: white; font-weight: bold;")
        layout.addWidget(btn_load)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self.gantt_view = QWebEngineView()
        self.tabs.addTab(self.gantt_view, "Gantt Şeması")

        self.progress_view = QWebEngineView()
        self.tabs.addTab(self.progress_view, "İlerleme Analizi")

    def load_file(self):
        file_filter = "Data Files (*.csv *.xlsx);; CSV (*.csv);; Excel (*.xlsx)"
        file_path, _ = QFileDialog.getOpenFileName(self, "Proje Dosyasını Seç", "", file_filter)

        if file_path:
            try:
                self.process_data(file_path)
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Dosya işlenirken hata oluştu:\n{str(e)}")

    def process_data(self, file_path):
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)

        if 'Başlangıç' not in df.columns:
            QMessageBox.warning(self, "Uyarı", "Dosyada 'Başlangıç' sütunu bulunamadı.")
            return

        df['Başlangıç_Date'] = df['Başlangıç'].apply(parse_turkish_date)
        df['Bitiş_Date'] = df['Bitiş'].apply(parse_turkish_date)
        df['Bolluk_Num'] = df['Toplam_Bolluk'].apply(clean_duration)
        df['Kritik'] = df['Bolluk_Num'] <= 0
        df['Durum'] = df.apply(lambda x: 'Kritik' if x['Kritik'] else 'Normal', axis=1)

        self.label.setText(f"Yüklenen Dosya: {os.path.basename(file_path)} | Toplam Aktivite: {len(df)}")

        fig_gantt = px.timeline(
            df, x_start="Başlangıç_Date", x_end="Bitiş_Date", y="Ad",
            color="Durum", color_discrete_map={"Kritik": "#FF4B4B", "Normal": "#1C83E1"},
            title="Proje Zaman Çizelgesi"
        )
        fig_gantt.update_yaxes(autorange="reversed")
        
        raw_html_gantt = fig_gantt.to_html(include_plotlyjs='cdn')
        self.gantt_view.setHtml(raw_html_gantt)

        fig_prog = px.histogram(df, x="Bitiş_Date", title="Aylık İş Yükü Dağılımı")
        raw_html_prog = fig_prog.to_html(include_plotlyjs='cdn')
        self.progress_view.setHtml(raw_html_prog)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ProjectApp()
    window.show()
    sys.exit(app.exec())
