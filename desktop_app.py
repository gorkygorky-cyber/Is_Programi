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
                             QTextEdit, QHBoxLayout, QFrame, QSplitter)
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

# --- KPI KART CLASS ---
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

        self.setWindowTitle("Proje Yönetim Paneli - Dashboard v4.0 (Baseline Destekli)")
        self.setGeometry(100, 100, 1400, 900)
        self.setStyleSheet("background-color: #f4f6f9; font-family: Segoe UI, sans-serif;")

        # Veri Saklama Alanları
        self.df_current = None
        self.df_baseline = None

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        self.main_layout = QVBoxLayout()
        main_widget.setLayout(self.main_layout)

        # --- ÜST BAR (ÇİFT DOSYA YÜKLEME) ---
        top_bar_layout = QHBoxLayout()
        
        # Sol Taraf: Güncel Dosya
        self.btn_load_current = QPushButton("📂 1. Güncel Programı Yükle")
        self.btn_load_current.clicked.connect(lambda: self.load_file(is_baseline=False))
        self.apply_button_style(self.btn_load_current, "#0078D7")
        
        self.lbl_status_current = QLabel("Yüklü Değil")
        self.lbl_status_current.setStyleSheet("color: #666; margin-right: 20px;")

        # Sağ Taraf: Baseline Dosyası
        self.btn_load_baseline = QPushButton("📂 2. Baseline / Önceki Program (Opsiyonel)")
        self.btn_load_baseline.clicked.connect(lambda: self.load_file(is_baseline=True))
        self.apply_button_style(self.btn_load_baseline, "#7f8c8d") # Gri renk

        self.lbl_status_baseline = QLabel("Yüklü Değil")
        self.lbl_status_baseline.setStyleSheet("color: #666;")

        top_bar_layout.addWidget(self.btn_load_current)
        top_bar_layout.addWidget(self.lbl_status_current)
        top_bar_layout.addStretch()
        top_bar_layout.addWidget(self.btn_load_baseline)
        top_bar_layout.addWidget(self.lbl_status_baseline)

        self.main_layout.addLayout(top_bar_layout)

        # --- SEKMELER ---
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #ccc; background: white; }
            QTabBar::tab { background: #e0e0e0; padding: 8px 15px; margin-right: 2px; border-top-left-radius: 4px; border-top-right-radius: 4px;}
            QTabBar::tab:selected { background: #fff; border-bottom: 2px solid #0078D7; font-weight: bold; color: #0078D7; }
        """)
        self.main_layout.addWidget(self.tabs)

        self.setup_dashboard_tab()
        self.setup_comparison_tab() # YENİ SEKME
        self.setup_summary_gantt_tab()
        self.setup_timeline_tab()
        self.setup_insights_tab()

    def apply_button_style(self, button, color):
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {color}; color: white; padding: 8px 15px; 
                border-radius: 5px; font-weight: bold; border: none;
            }}
            QPushButton:hover {{ background-color: {color}AA; }}
        """)

    def setup_dashboard_tab(self):
        self.dash_tab = QWidget()
        self.dash_layout = QVBoxLayout()
        self.dash_tab.setLayout(self.dash_layout)
        
        self.kpi_layout = QHBoxLayout()
        self.dash_layout.addLayout(self.kpi_layout)
        
        self.dash_webview = QWebEngineView()
        self.dash_layout.addWidget(self.dash_webview)
        self.tabs.addTab(self.dash_tab, "🚀 Yönetici Özeti")

    def setup_comparison_tab(self):
        self.comp_tab = QWidget()
        self.comp_layout = QVBoxLayout()
        self.comp_tab.setLayout(self.comp_layout)
        
        self.comp_webview = QWebEngineView()
        self.comp_layout.addWidget(self.comp_webview)
        self.comp_webview.setHtml("<h3 style='padding:20px; font-family:Segoe UI'>Kıyaslama yapmak için lütfen hem Güncel hem de Baseline dosyasını yükleyin.</h3>")
        
        self.tabs.addTab(self.comp_tab, "⚖️ Kıyas Tablosu")

    def setup_summary_gantt_tab(self):
        self.gantt_view = QWebEngineView()
        self.tabs.addTab(self.gantt_view, "📅 Kritik Hat (Gantt)")

    def setup_timeline_tab(self):
        self.timeline_view = QWebEngineView()
        self.tabs.addTab(self.timeline_view, "⏳ Kritik Zaman Çizelgesi")

    def setup_insights_tab(self):
        self.insights_text = QTextEdit()
        self.insights_text.setReadOnly(True)
        self.insights_text.setStyleSheet("""
            QTextEdit {
                background-color: white; color: black; font-size: 15px; 
                padding: 15px; border: none;
            }
        """)
        self.tabs.addTab(self.insights_text, "🤖 Akıllı Notlar & Rapor")

    # --- DOSYA YÜKLEME ---
    def load_file(self, is_baseline=False):
        file_filter = "Data Files (*.csv *.xlsx);; CSV (*.csv);; Excel (*.xlsx)"
        title = "Baseline Dosyası Seç" if is_baseline else "Güncel Proje Dosyası Seç"
        file_path, _ = QFileDialog.getOpenFileName(self, title, "", file_filter)
        
        if file_path:
            try:
                df = self.read_and_clean_data(file_path)
                
                if is_baseline:
                    self.df_baseline = df
                    self.lbl_status_baseline.setText(f"✅ {os.path.basename(file_path)}")
                    self.lbl_status_baseline.setStyleSheet("color: green; font-weight: bold;")
                else:
                    self.df_current = df
                    self.lbl_status_current.setText(f"✅ {os.path.basename(file_path)}")
                    self.lbl_status_current.setStyleSheet("color: green; font-weight: bold;")
                
                # Her yüklemede ekranları tazele
                self.refresh_ui()
                
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Veri işlenirken hata oluştu:\n{str(e)}")

    def read_and_clean_data(self, file_path):
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)

        if 'Başlangıç' not in df.columns:
            raise ValueError("'Başlangıç' sütunu bulunamadı!")

        df['Başlangıç_Date'] = df['Başlangıç'].apply(parse_turkish_date)
        df['Bitiş_Date'] = df['Bitiş'].apply(parse_turkish_date)
        df['Süre_Num'] = df['Süre'].apply(clean_duration)
        df['Bolluk_Num'] = df['Toplam_Bolluk'].apply(clean_duration)
        df['Kritik'] = (df['Bolluk_Num'] <= 0) & (df['Tamamlanma_Yüzdesi'] < 1.0)
        df['Durum'] = df.apply(lambda x: 'Kritik' if x['Kritik'] else ('Tamamlandı' if x['Tamamlanma_Yüzdesi'] == 1.0 else 'Normal'), axis=1)
        return df

    def refresh_ui(self):
        # Eğer Güncel dosya yoksa işlem yapma
        if self.df_current is None:
            return

        # 1. Dashboard, Gantt, Timeline ve Notları Güncelle (Güncel veri ile)
        self.create_dashboard(self.df_current)
        self.create_summary_gantt(self.df_current)
        self.create_timeline(self.df_current)
        self.generate_insights(self.df_current, self.df_baseline) # Notlara baseline da gönderiliyor

        # 2. Eğer Baseline da varsa Kıyas Tablosunu Güncelle
        if self.df_baseline is not None:
            self.create_comparison_report(self.df_current, self.df_baseline)
            self.apply_button_style(self.btn_load_baseline, "#27ae60") # Baseline yüklenince buton yeşil olsun
        else:
            self.comp_webview.setHtml("<h3 style='padding:20px; font-family:Segoe UI; color:#666'>⚠️ Kıyaslama sekmesini görmek için Baseline dosyasını yükleyiniz.</h3>")

    # --- EKRAN OLUŞTURUCULAR ---

    def create_comparison_report(self, df_curr, df_base):
        # Verileri ID (Benzersiz_Kimlik) üzerinden birleştir
        merged = pd.merge(
            df_curr, 
            df_base, 
            on="Benzersiz_Kimlik", 
            how="inner", 
            suffixes=('_cur', '_base')
        )
        
        # Farkları Hesapla
        # Başlangıç Gecikmesi (Gün)
        merged['Start_Delay'] = (merged['Başlangıç_Date_cur'] - merged['Başlangıç_Date_base']).dt.days
        # Bitiş Gecikmesi (Gün)
        merged['Finish_Delay'] = (merged['Bitiş_Date_cur'] - merged['Bitiş_Date_base']).dt.days
        # Süre Değişimi (Gün) -> Negatifse süre kısalmış demektir
        merged['Duration_Diff'] = merged['Süre_Num_cur'] - merged['Süre_Num_base']
        # Bolluk Değişimi -> Negatifse daha kritik hale gelmiş demektir
        merged['Slack_Diff'] = merged['Bolluk_Num_cur'] - merged['Bolluk_Num_base']

        # --- GRAFİK ALANI ---
        fig = make_subplots(
            rows=3, cols=2,
            specs=[[{"type": "domain", "colspan": 2}, None],
                   [{"type": "table"}, {"type": "table"}],
                   [{"type": "table"}, {"type": "table"}]],
            subplot_titles=("", "🚀 Başlaması Gecikenler (Top 10)", "🏁 Bitmesi Gecikenler (Top 10)", 
                            "📉 Kritikliği Artanlar (Top 10)", "⚡ Süresi Kısaltılanlar (Top 10)"),
            vertical_spacing=0.08
        )

        # 1. Üst Kısım: Genel İlerleme Karşılaştırması (Bar Chart)
        # Ana özet aktivitesini (ID 1) veya ortalamayı al
        prog_cur = df_curr[df_curr['Benzersiz_Kimlik']==1]['Tamamlanma_Yüzdesi'].values[0] * 100 if 1 in df_curr['Benzersiz_Kimlik'].values else df_curr['Tamamlanma_Yüzdesi'].mean()*100
        prog_base = df_base[df_base['Benzersiz_Kimlik']==1]['Tamamlanma_Yüzdesi'].values[0] * 100 if 1 in df_base['Benzersiz_Kimlik'].values else df_base['Tamamlanma_Yüzdesi'].mean()*100
        
        fig.add_trace(go.Indicator(
            mode = "number+gauge+delta", value = prog_cur,
            delta = {'reference': prog_base, 'relative': False, 'valueformat': '.1f'},
            title = {'text': "Güncel İlerleme vs Baseline"},
            gauge = {
                'shape': "bullet", 'axis': {'range': [None, 100]},
                'threshold': {'line': {'color': "black", 'width': 2}, 'thickness': 0.75, 'value': prog_base},
                'steps': [{'range': [0, prog_base], 'color': "lightgray"}],
                'bar': {'color': "#0078D7"}
            }
        ), row=1, col=1)

        # --- TABLOLAR İÇİN FONKSİYON ---
        def add_table(dataframe, col_idx, row_idx, columns, headers):
            fig.add_trace(go.Table(
                header=dict(values=headers, fill_color='#2c3e50', font=dict(color='white', size=11)),
                cells=dict(values=[dataframe[c] for c in columns], 
                           fill_color='#ecf0f1', font=dict(color='black', size=11), height=25)
            ), row=row_idx, col=col_idx)

        # Tablo 1: Başlaması Gecikenler (Start Delay > 0)
        start_delays = merged[merged['Start_Delay'] > 0].sort_values('Start_Delay', ascending=False).head(10)
        start_delays['Ad_cur'] = start_delays['Ad_cur'].str.slice(0, 25)
        add_table(start_delays, 1, 2, ['Ad_cur', 'Start_Delay'], ['Aktivite Adı', 'Gecikme (Gün)'])

        # Tablo 2: Bitmesi Gecikenler (Finish Delay > 0)
        finish_delays = merged[merged['Finish_Delay'] > 0].sort_values('Finish_Delay', ascending=False).head(10)
        finish_delays['Ad_cur'] = finish_delays['Ad_cur'].str.slice(0, 25)
        add_table(finish_delays, 2, 2, ['Ad_cur', 'Finish_Delay'], ['Aktivite Adı', 'Öteleme (Gün)'])

        # Tablo 3: Kritikliği Artanlar (Bolluk Azalanlar: Slack Diff < 0)
        more_critical = merged[merged['Slack_Diff'] < 0].sort_values('Slack_Diff', ascending=True).head(10)
        more_critical['Ad_cur'] = more_critical['Ad_cur'].str.slice(0, 25)
        add_table(more_critical, 1, 3, ['Ad_cur', 'Slack_Diff'], ['Aktivite Adı', 'Bolluk Kaybı (Gün)'])

        # Tablo 4: Süresi Azaltılanlar (Duration Diff < 0)
        reduced_dur = merged[merged['Duration_Diff'] < 0].sort_values('Duration_Diff', ascending=True).head(10)
        reduced_dur['Ad_cur'] = reduced_dur['Ad_cur'].str.slice(0, 25)
        add_table(reduced_dur, 2, 3, ['Ad_cur', 'Duration_Diff'], ['Aktivite Adı', 'Kısalma (Gün)'])

        fig.update_layout(height=800, margin=dict(l=10, r=10, t=40, b=10), font=dict(family="Segoe UI"))
        self.comp_webview.setHtml(fig.to_html(include_plotlyjs='cdn'))

    def create_dashboard(self, df):
        # KPI ve Ana Dashboard Mantığı (Eski Kodun Aynısı - Hata düzeltmeleriyle)
        today = pd.Timestamp.now()
        start_date = df['Başlangıç_Date'].min()
        finish_date = df['Bitiş_Date'].max()
        
        total_days = (finish_date - start_date).days
        elapsed_days = (today - start_date).days
        remaining_days = (finish_date - today).days
        if elapsed_days < 0: elapsed_days = 0
        if remaining_days < 0: remaining_days = 0
        
        project_summary = df[df['Benzersiz_Kimlik'] == 1]
        avg_progress = project_summary.iloc[0]['Tamamlanma_Yüzdesi'] * 100 if not project_summary.empty else df['Tamamlanma_Yüzdesi'].mean() * 100

        time_progress = 0
        if total_days > 0:
            time_progress = (elapsed_days / total_days) * 100
            if time_progress > 100: time_progress = 100

        # KPI Kartlarını Temizle
        for i in reversed(range(self.kpi_layout.count())): 
            self.kpi_layout.itemAt(i).widget().setParent(None)

        self.kpi_layout.addWidget(KPICard("Toplam Süre", f"{total_days} Gün"))
        self.kpi_layout.addWidget(KPICard("Geçen Süre", f"{elapsed_days} Gün", "#FF9800"))
        self.kpi_layout.addWidget(KPICard("Kalan Süre", f"{remaining_days} Gün", "#4CAF50"))
        self.kpi_layout.addWidget(KPICard("Fiziksel İlerleme", f"%{avg_progress:.1f}", "#9C27B0"))
        self.kpi_layout.addWidget(KPICard("Planlanan (Süresel)", f"%{time_progress:.1f}", "#E91E63"))

        fig = make_subplots(
            rows=2, cols=2, column_widths=[0.35, 0.65], row_heights=[0.5, 0.5],
            specs=[[{"type": "indicator"}, {"type": "table", "rowspan": 2}], [{"type": "domain"}, None]],
            subplot_titles=("İlerleme Hedef Karşılaştırması", "Kritik Aktivite Takip Listesi", "Aktivite Durum Dağılımı")
        )

        fig.add_trace(go.Indicator(
            mode = "gauge+number+delta", value = avg_progress,
            delta = {'reference': time_progress, 'relative': False, "valueformat": ".1f"},
            gauge = {'axis': {'range': [None, 100]}, 'bar': {'color': "#0078D7"},
                     'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': time_progress}}
        ), row=1, col=1)

        status_counts = df['Durum'].value_counts()
        colors_map = {'Kritik': '#FF4B4B', 'Normal': '#1C83E1', 'Tamamlandı': '#2ECC71'}
        fig.add_trace(go.Pie(labels=status_counts.index, values=status_counts.values, hole=.4,
            marker_colors=[colors_map.get(x, '#999') for x in status_counts.index]), row=2, col=1)

        active_crit = df[df['Kritik'] == True].sort_values(by='Başlangıç_Date')
        urgent_crit = active_crit[active_crit['Başlangıç_Date'] <= today].head(8).copy()
        future_crit = active_crit[active_crit['Başlangıç_Date'] > today].head(8).copy()
        
        urgent_crit['Öncelik'] = "🔴 ACİL"
        future_crit['Öncelik'] = "📅 GELECEK"
        combined_table = pd.concat([urgent_crit, future_crit])

        if combined_table.empty:
            header, cells = ["Bilgi"], [["Kritik iş yok"]]
        else:
            header = ["Durum", "Aktivite Adı", "Başlangıç", "Bitiş", "%"]
            cells = [combined_table['Öncelik'], combined_table['Ad'].str.slice(0, 35),
                     combined_table['Başlangıç_Date'].dt.strftime('%d-%m'), combined_table['Bitiş_Date'].dt.strftime('%d-%m'),
                     (combined_table['Tamamlanma_Yüzdesi']*100).map('{:.0f}%'.format)]

        fig.add_trace(go.Table(
            header=dict(values=header, fill_color='#2c3e50', font=dict(color='white', size=11)),
            cells=dict(values=cells, fill_color=['#ecf0f1']*len(combined_table), font=dict(color='black', size=11), height=28)
        ), row=1, col=2)
        
        fig.update_layout(height=650, margin=dict(l=10, r=10, t=40, b=10), font=dict(family="Segoe UI"))
        self.dash_webview.setHtml(fig.to_html(include_plotlyjs='cdn'))

    def create_summary_gantt(self, df):
        summary_crit = df[(df['Özet'] == 'Evet') & (df['Kritik'] == True)].copy()
        if summary_crit.empty:
            self.gantt_view.setHtml("<h3 style='font-family:Segoe UI; padding:20px'>Kritik özet aktivite bulunamadı.</h3>")
            return
        fig = px.timeline(summary_crit, x_start="Başlangıç_Date", x_end="Bitiş_Date", y="Ad",
            color="Tamamlanma_Yüzdesi", title="Kritik Özet Aktiviteler", color_continuous_scale="Reds")
        fig.update_yaxes(autorange="reversed")
        fig.update_layout(height=700, font=dict(family="Segoe UI"))
        self.gantt_view.setHtml(fig.to_html(include_plotlyjs='cdn'))

    def create_timeline(self, df):
        summary_crit = df[(df['Özet'] == 'Evet') & (df['Kritik'] == True)].copy()
        if summary_crit.empty:
            self.timeline_view.setHtml("<h3 style='font-family:Segoe UI; padding:20px'>Veri yok.</h3>")
            return
        fig = px.scatter(summary_crit, x="Bitiş_Date", y="Ad", color="Tamamlanma_Yüzdesi",
            size="Süre_Num", title="Kritik Timeline", labels={"Bitiş_Date": "Hedef Tarih"})
        for i, row in summary_crit.iterrows():
            fig.add_shape(type="line", x0=row['Başlangıç_Date'], y0=row['Ad'], x1=row['Bitiş_Date'], y1=row['Ad'], line=dict(color="gray", width=1))
        fig.update_yaxes(autorange="reversed")
        fig.update_layout(height=700, font=dict(family="Segoe UI"))
        self.timeline_view.setHtml(fig.to_html(include_plotlyjs='cdn'))

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

        # --- MEVCUT DURUM ANALİZİ ---
        crit_active = df_curr[df_curr['Kritik'] == True]
        if crit_active.empty:
            html += "<p class='safe'>✅ MÜKEMMEL: Kritik hat üzerinde aktif riskli aktivite bulunmamaktadır.</p>"
        else:
            html += f"<p>Şu anda proje bitişini tehdit eden <b>{len(crit_active)}</b> adet aktif kritik görev bulunmaktadır.</p>"

        today = pd.Timestamp.now()
        delayed = df_curr[(df_curr['Bitiş_Date'] < today) & (df_curr['Tamamlanma_Yüzdesi'] < 1.0)]
        if not delayed.empty:
            html += "<h3>🚫 Gecikmiş İşler (Acil Müdahale)</h3>"
            html += f"<p>Bitiş tarihi geçmiş <b>{len(delayed)}</b> aktivite var.</p><ul>"
            for _, row in delayed.head(5).iterrows():
                delay_days = (today - row['Bitiş_Date']).days
                html += f"<li><b>{row['Ad']}</b> - <span class='highlight'>{delay_days} Gün Gecikmiş</span></li>"
            html += "</ul>"

        # --- KIYASLAMA ANALİZİ (Eğer Baseline Varsa) ---
        if df_base is not None:
            merged = pd.merge(df_curr, df_base, on="Benzersiz_Kimlik", how="inner", suffixes=('_cur', '_base'))
            
            # Gecikme Analizi
            merged['Start_Delay'] = (merged['Başlangıç_Date_cur'] - merged['Başlangıç_Date_base']).dt.days
            merged['Finish_Delay'] = (merged['Bitiş_Date_cur'] - merged['Bitiş_Date_base']).dt.days
            
            total_delayed_starts = len(merged[merged['Start_Delay'] > 0])
            total_delayed_finishes = len(merged[merged['Finish_Delay'] > 0])
            max_delay = merged['Finish_Delay'].max()

            html += "<br><hr>"
            html += "<h2>⚖️ Baseline Karşılaştırma Raporu</h2>"
            
            html += f"<p>Baseline programa göre <b>{total_delayed_starts}</b> aktivitenin başlangıcı, <b>{total_delayed_finishes}</b> aktivitenin bitişi ötelenmiştir.</p>"
            
            if max_delay > 0:
                most_delayed_task = merged.loc[merged['Finish_Delay'].idxmax()]
                html += f"<p>En büyük sapma <b>{most_delayed_task['Ad_cur']}</b> aktivitesinde <b>{max_delay} gün</b> olarak tespit edilmiştir.</p>"

            # İlerleme Farkı
            prog_cur = df_curr[df_curr['Benzersiz_Kimlik']==1]['Tamamlanma_Yüzdesi'].values[0] * 100 if 1 in df_curr['Benzersiz_Kimlik'].values else df_curr['Tamamlanma_Yüzdesi'].mean()*100
            prog_base = df_base[df_base['Benzersiz_Kimlik']==1]['Tamamlanma_Yüzdesi'].values[0] * 100 if 1 in df_base['Benzersiz_Kimlik'].values else df_base['Tamamlanma_Yüzdesi'].mean()*100
            
            diff = prog_cur - prog_base
            color_cls = "safe" if diff >= 0 else "danger"
            sign = "+" if diff > 0 else ""
            html += f"<h4>📈 İlerleme Değişimi</h4>"
            html += f"<p>Baseline İlerleme: %{prog_base:.1f} <br> Güncel İlerleme: %{prog_cur:.1f} <br> Fark: <span class='{color_cls}'>{sign}%{diff:.1f}</span></p>"

        html += "</body></html>"
        self.insights_text.setHtml(html)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ProjectApp()
    window.show()
    sys.exit(app.exec())
