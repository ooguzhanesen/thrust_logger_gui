import sys
import os
import re
import csv
import time
import serial
import serial.tools.list_ports
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QComboBox, 
                             QLineEdit, QGroupBox, QTextEdit, QGridLayout,
                             QFileDialog, QMessageBox, QSplashScreen)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont, QIcon, QPixmap, QColor
import pyqtgraph as pg

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class LogViewerWindow(QMainWindow):
    def __init__(self, filepath):
        super().__init__()
        filename = os.path.basename(filepath)
        self.setWindowTitle(f"Rotary Aerospace Analyzer | İncelenen Kayıt: {filename}")
        self.resize(1200, 800)
        self.setWindowIcon(QIcon(resource_path("logo.png")))
        central = QWidget()
        self.setCentralWidget(central)
        layout = QGridLayout(central)
        
        # YENİ: self.pwms listesi eklendi
        self.times, self.rpms, self.thrusts = [], [], []
        self.volts, self.currs, self.powers, self.pwms = [], [], [], [] 
        
        try:
            with open(filepath, 'r') as f:
                reader = csv.reader(f)
                header = next(reader)
                for row in reader:
                    if len(row) >= 8:
                        self.times.append(float(row[0]))
                        self.pwms.append(float(row[2])) # YENİ: PWM verisi CSV'de 3. sütunda
                        self.volts.append(float(row[3]))
                        self.currs.append(float(row[4]))
                        self.powers.append(float(row[5]))
                        self.thrusts.append(float(row[6]))
                        self.rpms.append(float(row[7]))
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Dosya okunamadı: {str(e)}")
            return
            
        p_rpm = pg.PlotWidget(title="Tüm Test: Motor Devri (eRPM)")
        p_rpm.plot(self.times, self.rpms, pen=pg.mkPen('#FFCC00', width=2))
        layout.addWidget(p_rpm, 0, 0)
        
        p_thrust = pg.PlotWidget(title="Tüm Test: İtki (Thrust - g)")
        p_thrust.plot(self.times, self.thrusts, pen=pg.mkPen('#00AAFF', width=2))
        layout.addWidget(p_thrust, 0, 1)
        
        p_volt = pg.PlotWidget(title="Tüm Test: Voltaj Çöküşü (V)")
        p_volt.plot(self.times, self.volts, pen=pg.mkPen('#FF3333', width=2))
        layout.addWidget(p_volt, 1, 0)
        
        p_curr = pg.PlotWidget(title="Tüm Test: Çekilen Akım (A)")
        p_curr.plot(self.times, self.currs, pen=pg.mkPen('#33FF33', width=2))
        layout.addWidget(p_curr, 1, 1)
        
        p_power = pg.PlotWidget(title="Tüm Test: Güç Eğrisi (W)")
        p_power.plot(self.times, self.powers, pen=pg.mkPen('#E600FF', width=2))
        layout.addWidget(p_power, 2, 0) # GÜNCELLEME: Artık sadece sol alt köşeyi kaplayacak
        
        # YENİ EKLENEN: PWM GRAFİĞİ
        p_pwm = pg.PlotWidget(title="Tüm Test: Uygulanan PWM Sinyali")
        p_pwm.plot(self.times, self.pwms, pen=pg.mkPen('#FF8C00', width=2)) # Turuncu renk
        layout.addWidget(p_pwm, 2, 1) # GÜNCELLEME: Sağ alt köşeye yerleştirildi

class RotaryTestStandGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Rotary Aerospace | Thrust Logger Control Center")
        self.resize(1350, 850) 
        self.setWindowIcon(QIcon(resource_path("logo.png")))
        self.ser = None
        self.is_recording = False
        self.csv_file = None
        self.csv_writer = None
        self.log_viewer = None
        self.rpm_data, self.thrust_data, self.volt_data = [], [], []
        self.curr_data, self.power_data, self.time_axis = [], [], []
        self.data_counter = 0
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        main_layout = QHBoxLayout(self.central_widget) 
        left_panel = QVBoxLayout()
        main_layout.addLayout(left_panel, stretch=2)

        # 1. Bağlantı Kutusu
        conn_group = QGroupBox("Bağlantı Ayarları")
        conn_layout = QHBoxLayout()
        self.combo_ports = QComboBox()
        self.refresh_ports()
        self.btn_refresh = QPushButton("Yenile")
        self.btn_refresh.clicked.connect(self.refresh_ports)
        self.btn_connect = QPushButton("Bağlan")
        self.btn_connect.clicked.connect(self.toggle_connection)
        conn_layout.addWidget(QLabel("Port:"))
        conn_layout.addWidget(self.combo_ports)
        conn_layout.addWidget(self.btn_refresh)
        conn_layout.addWidget(self.btn_connect)
        conn_group.setLayout(conn_layout)
        left_panel.addWidget(conn_group)

        # 2. Ana Kontroller
        core_group = QGroupBox("Ana Kontroller & Analiz")
        core_layout = QVBoxLayout() 
        
        row1_layout = QHBoxLayout()
        self.btn_start = QPushButton("▶ Okuma Başlat")
        self.btn_start.setStyleSheet("background-color: #28a745; color: white; font-weight: bold; padding: 5px;")
        self.btn_start.clicked.connect(lambda: self.send_command("start_reading"))
        self.btn_stop = QPushButton("⏸ Okuma Durdur")
        self.btn_stop.setStyleSheet("background-color: #ffc107; color: black; font-weight: bold; padding: 5px;")
        self.btn_stop.clicked.connect(self.stop_reading_action)
        self.btn_analyze = QPushButton("📂 Geçmiş İncele")
        self.btn_analyze.setStyleSheet("background-color: #17a2b8; color: white; font-weight: bold; padding: 5px;")
        self.btn_analyze.clicked.connect(self.open_log_viewer)
        row1_layout.addWidget(self.btn_start)
        row1_layout.addWidget(self.btn_stop)
        row1_layout.addWidget(self.btn_analyze)

        row2_layout = QHBoxLayout()
        # YENİ: TEK BUTONLU (TOGGLE) KAYIT MEKANİZMASI
        self.btn_toggle_record = QPushButton("⏺ Kaydı Başlat")
        self.btn_toggle_record.setStyleSheet("background-color: #007bff; color: white; font-weight: bold; padding: 5px;")
        self.btn_toggle_record.clicked.connect(self.toggle_record_action)
        row2_layout.addWidget(self.btn_toggle_record)

        core_layout.addLayout(row1_layout)
        core_layout.addLayout(row2_layout)
        core_group.setLayout(core_layout)
        left_panel.addWidget(core_group)

        # 3. Parametreler
        param_group = QGroupBox("Sistem Limitleri")
        param_grid = QGridLayout()
        self.input_poles = QLineEdit("28")
        self.btn_set_poles = QPushButton("Set Et")
        self.btn_set_poles.clicked.connect(lambda: self.send_command(f"set_pol_{self.input_poles.text()}"))
        param_grid.addWidget(QLabel("Motor Kutup:"), 0, 0)
        param_grid.addWidget(self.input_poles, 0, 1)
        param_grid.addWidget(self.btn_set_poles, 0, 2)
        self.input_max_curr = QLineEdit("30")
        self.btn_set_curr = QPushButton("Limit Koy")
        self.btn_set_curr.clicked.connect(lambda: self.send_command(f"set_max_current_{self.input_max_curr.text()}"))
        param_grid.addWidget(QLabel("Max Akım (A):"), 1, 0)
        param_grid.addWidget(self.input_max_curr, 1, 1)
        param_grid.addWidget(self.btn_set_curr, 1, 2)
        self.input_min_volt = QLineEdit("22.5")
        self.btn_set_volt = QPushButton("Limit Koy")
        self.btn_set_volt.clicked.connect(lambda: self.send_command(f"set_min_voltage_{self.input_min_volt.text()}"))
        param_grid.addWidget(QLabel("Min Voltaj (V):"), 2, 0)
        param_grid.addWidget(self.input_min_volt, 2, 1)
        param_grid.addWidget(self.btn_set_volt, 2, 2)
        param_group.setLayout(param_grid)
        left_panel.addWidget(param_group)

        # 4. Loadcell
        lc_group = QGroupBox("Loadcell Kalibrasyon")
        lc_layout = QHBoxLayout()
        self.btn_tare = QPushButton("Sıfırla (Dara Al)")
        self.btn_tare.clicked.connect(lambda: self.send_command("tare"))
        self.input_cal_weight = QLineEdit("1000")
        self.input_cal_weight.setMaximumWidth(50)
        self.btn_calibrate = QPushButton("Kalibre Et")
        self.btn_calibrate.clicked.connect(lambda: self.send_command(f"calibrate_{self.input_cal_weight.text()}"))
        lc_layout.addWidget(self.btn_tare)
        lc_layout.addWidget(QLabel(" Ağırlık(g):"))
        lc_layout.addWidget(self.input_cal_weight)
        lc_layout.addWidget(self.btn_calibrate)
        lc_group.setLayout(lc_layout)
        left_panel.addWidget(lc_group)

        # 5. Sürüş Modları & ESC Kalibrasyon
        test_group = QGroupBox("Sürüş Modları & Donanım")
        test_grid = QGridLayout()
        self.input_pwm = QLineEdit("1100")
        self.btn_set_pwm = QPushButton("PWM Gönder")
        self.btn_set_pwm.clicked.connect(lambda: self.send_command(f"set_pwm_{self.input_pwm.text()}"))
        test_grid.addWidget(QLabel("Manuel PWM:"), 0, 0)
        test_grid.addWidget(self.input_pwm, 0, 1)
        test_grid.addWidget(self.btn_set_pwm, 0, 2)
        self.input_test_time = QLineEdit("10")
        self.input_test_step = QLineEdit("100")
        self.btn_start_test = QPushButton("Testi Başlat")
        self.btn_start_test.clicked.connect(lambda: self.send_command(f"test_{self.input_test_time.text()}_{self.input_test_step.text()}"))
        test_grid.addWidget(QLabel("Süre(sn) & Adım:"), 1, 0)
        step_layout = QHBoxLayout()
        step_layout.addWidget(self.input_test_time)
        step_layout.addWidget(self.input_test_step)
        step_layout.setContentsMargins(0,0,0,0)
        step_widget = QWidget()
        step_widget.setLayout(step_layout)
        test_grid.addWidget(step_widget, 1, 1)
        test_grid.addWidget(self.btn_start_test, 1, 2)
        
        self.btn_cal_esc = QPushButton("🔧 ESC Kalibrasyonu Başlat")
        self.btn_cal_esc.setStyleSheet("background-color: #6f42c1; color: white; font-weight: bold; padding: 5px;")
        self.btn_cal_esc.clicked.connect(self.trigger_esc_calibration)
        test_grid.addWidget(self.btn_cal_esc, 2, 0, 1, 3) 
        
        test_group.setLayout(test_grid)
        left_panel.addWidget(test_group)

        # 6. Terminal
        log_group = QGroupBox("Terminal Günlüğü")
        log_layout = QVBoxLayout()
        self.btn_status = QPushButton("Durum Çek (status)")
        self.btn_status.clicked.connect(lambda: self.send_command("status"))
        self.terminal = QTextEdit()
        self.terminal.setReadOnly(True)
        self.terminal.setStyleSheet("background-color: black; color: #00FF00; font-family: Consolas;")
        self.terminal.setMinimumHeight(120)
        log_layout.addWidget(self.btn_status)
        log_layout.addWidget(self.terminal)
        log_group.setLayout(log_layout)
        left_panel.addWidget(log_group, stretch=1) 

        self.btn_emergency = QPushButton("!!! ACİL DURDURMA !!!")
        self.btn_emergency.setStyleSheet("background-color: red; color: white; font-weight: bold; font-size: 16px; padding: 15px;")
        self.btn_emergency.clicked.connect(self.emergency_stop_action)
        left_panel.addWidget(self.btn_emergency)

        right_panel = QVBoxLayout()
        main_layout.addLayout(right_panel, stretch=4) 
        disp_group = QGroupBox("Sensör Göstergeleri")
        disp_layout = QHBoxLayout()
        font_num = QFont("Helvetica", 20, QFont.Weight.Bold)
        font_lbl = QFont("Helvetica", 10)
        self.lbl_pwm = QLabel("1000"); self.lbl_pwm.setFont(font_num); self.lbl_pwm.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_volt = QLabel("0.00 V"); self.lbl_volt.setFont(font_num); self.lbl_volt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_curr = QLabel("0.00 A"); self.lbl_curr.setFont(font_num); self.lbl_curr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_power = QLabel("0.0 W"); self.lbl_power.setFont(font_num); self.lbl_power.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_thrust = QLabel("0.0 g"); self.lbl_thrust.setFont(font_num); self.lbl_thrust.setStyleSheet("color: #00AAFF;"); self.lbl_thrust.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_rpm = QLabel("0"); self.lbl_rpm.setFont(font_num); self.lbl_rpm.setStyleSheet("color: #FFCC00;"); self.lbl_rpm.setAlignment(Qt.AlignmentFlag.AlignCenter)

        def create_disp_block(lbl, txt):
            box = QVBoxLayout()
            title = QLabel(txt); title.setFont(font_lbl); title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            box.addWidget(title); box.addWidget(lbl)
            return box

        disp_layout.addLayout(create_disp_block(self.lbl_pwm, "ÇIKIŞ PWM"))
        disp_layout.addLayout(create_disp_block(self.lbl_volt, "VOLTAJ (V)"))
        disp_layout.addLayout(create_disp_block(self.lbl_curr, "AKIM (A)"))
        disp_layout.addLayout(create_disp_block(self.lbl_power, "GÜÇ (W)"))
        disp_layout.addLayout(create_disp_block(self.lbl_thrust, "İTKİ (GR)"))
        disp_layout.addLayout(create_disp_block(self.lbl_rpm, "MOTOR DEVİR"))
        disp_group.setLayout(disp_layout)
        right_panel.addWidget(disp_group)

        graph_group = QGroupBox("Canlı Grafikler")
        graph_grid = QGridLayout()
        self.plot_rpm = pg.PlotWidget(title="Devir (eRPM)")
        self.plot_rpm.setBackground('k')
        self.curve_rpm = self.plot_rpm.plot(pen=pg.mkPen('#FFCC00', width=2))
        graph_grid.addWidget(self.plot_rpm, 0, 0)
        self.plot_thrust = pg.PlotWidget(title="İtki (Thrust - gram)")
        self.plot_thrust.setBackground('k')
        self.curve_thrust = self.plot_thrust.plot(pen=pg.mkPen('#00AAFF', width=2))
        graph_grid.addWidget(self.plot_thrust, 0, 1)
        self.plot_volt = pg.PlotWidget(title="Batarya Voltajı (V)")
        self.plot_volt.setBackground('k')
        self.curve_volt = self.plot_volt.plot(pen=pg.mkPen('#FF3333', width=2))
        graph_grid.addWidget(self.plot_volt, 1, 0)
        self.plot_curr = pg.PlotWidget(title="Çekilen Akım (A)")
        self.plot_curr.setBackground('k')
        self.curve_curr = self.plot_curr.plot(pen=pg.mkPen('#33FF33', width=2))
        graph_grid.addWidget(self.plot_curr, 1, 1)
        self.plot_power = pg.PlotWidget(title="Güç Tüketimi (Watt)")
        self.plot_power.setBackground('k')
        self.curve_power = self.plot_power.plot(pen=pg.mkPen('#E600FF', width=2))
        graph_grid.addWidget(self.plot_power, 2, 0, 1, 2) 
        graph_group.setLayout(graph_grid)
        right_panel.addWidget(graph_group)

        self.read_timer = QTimer()
        self.read_timer.timeout.connect(self.read_serial_data)

    def trigger_esc_calibration(self):
        reply = QMessageBox.warning(
            self, 
            "⚠️ KRİTİK GÜVENLİK UYARISI", 
            "ESC Kalibrasyonuna başlamadan önce PERVANENİN SÖKÜLMÜŞ olduğundan emin olun!\n\n"
            "İşlemi başlatmak için ANA BATARYAYI (GÜCÜ) SÖKÜN ve 'Evet' butonuna basın.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            QMessageBox.information(
                self,
                "ℹ️ KALİBRASYON ADIMLARI",
                "Komut karta gönderilecek.\n"
                "Kattan uzun bir bip sesi duyduğunuz an, 10 saniye içinde BATARYAYI GERİ TAKIN.\n\n"
                "Hazırsanız 'Tamam' tuşuna basın ve komutu gönderin.",
                QMessageBox.StandardButton.Ok
            )
            self.send_command("calibrate_esc")

    def stop_reading_action(self):
        self.send_command("stop_reading")
        self.reset_displays()

    def emergency_stop_action(self):
        self.send_command("emergency_stop")
        self.reset_displays()

    def reset_displays(self):
        self.lbl_pwm.setText("1000")
        self.lbl_volt.setText("0.00 V")
        self.lbl_curr.setText("0.00 A")
        self.lbl_power.setText("0.0 W")
        self.lbl_thrust.setText("0.0 g")
        self.lbl_rpm.setText("0")

    def open_log_viewer(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "İncelenecek CSV Dosyasını Seç", "", "CSV Dosyaları (*.csv)")
        if filepath:
            self.log_viewer = LogViewerWindow(filepath)
            self.log_viewer.show()

    # --- YENİ EKLENEN AKILLI TOGGLE KAYIT SİSTEMİ ---
    def toggle_record_action(self):
        if not self.is_recording:
            # KAYIT BAŞLATMA DURUMU
            default_filename = f"thrust_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            filepath, _ = QFileDialog.getSaveFileName(self, "Veri Dosyasını Nereye Kaydedelim?", default_filename, "CSV Dosyaları (*.csv)")
            if not filepath: return
            
            try:
                self.csv_file = open(filepath, mode='w', newline='')
                self.csv_writer = csv.writer(self.csv_file)
                self.csv_writer.writerow(["Zaman_Noktasi", "Sistem_Saati", "PWM", "Voltaj(V)", "Akim(A)", "Guc(W)", "Itki(g)", "eRPM"])
                self.is_recording = True
                
                # Butonu "Durdur" kırmızısına çevir
                self.btn_toggle_record.setText("⏹ Kaydı Bitir")
                self.btn_toggle_record.setStyleSheet("background-color: #dc3545; color: white; font-weight: bold; padding: 5px;")
                self.terminal.append(f"[BİLGİ]: Veri kaydı başladı -> {filepath}")
                self.terminal.ensureCursorVisible()
            except Exception as e:
                self.terminal.append(f"[HATA]: Kayıt dosyası oluşturulamadı: {str(e)}")
        else:
            # KAYIT DURDURMA DURUMU
            self.is_recording = False
            if self.csv_file: 
                self.csv_file.close()
                self.csv_file = None
            
            # Butonu tekrar "Başlat" mavisine çevir
            self.btn_toggle_record.setText("⏺ Excel Kaydını Başlat")
            self.btn_toggle_record.setStyleSheet("background-color: #007bff; color: white; font-weight: bold; padding: 5px;")
            self.terminal.append("[BİLGİ]: Veri kaydı başarıyla durduruldu ve kaydedildi.")
            self.terminal.ensureCursorVisible()

    def closeEvent(self, event):
        # Uygulama kapanırken arkada açık dosya kalmasın
        if self.is_recording: 
            self.is_recording = False
            if self.csv_file: self.csv_file.close()
        
        if self.ser and self.ser.is_open: 
            self.ser.close()
        event.accept()

    def refresh_ports(self):
        self.combo_ports.clear()
        for port in serial.tools.list_ports.comports():
            self.combo_ports.addItem(port.device)

    def toggle_connection(self):
        if self.ser is None or not self.ser.is_open:
            selected_port = self.combo_ports.currentText()
            if not selected_port: return
            try:
                self.ser = serial.Serial(selected_port, 115200, timeout=0.05)
                self.btn_connect.setText("Bağlantıyı Kes")
                self.btn_connect.setStyleSheet("background-color: green; color: white;")
                self.terminal.append(f"-> {selected_port} hattına başarıyla bağlanıldı.\n")
                self.read_timer.start(20)
            except Exception as e:
                self.terminal.append(f"Bağlantı Hatası: {str(e)}\n")
        else:
            self.read_timer.stop()
            if self.ser and self.ser.is_open: self.ser.close()
            self.ser = None
            self.btn_connect.setText("Bağlan")
            self.btn_connect.setStyleSheet("")

    def send_command(self, cmd_string):
        if self.ser and self.ser.is_open:
            self.ser.write(f"{cmd_string}\n".encode('utf-8'))
            self.terminal.append(f"[KONTROL]: {cmd_string}")
        else:
            self.terminal.append("Hata: Önce karta bağlanmanız gerekiyor!")

    def read_serial_data(self):
        if self.ser and self.ser.is_open:
            while self.ser.in_waiting > 0:
                try:
                    raw_line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                    if not raw_line: continue
                    if "PWM:" in raw_line and "V:" in raw_line: self.parse_sensor_string(raw_line)
                    else: self.terminal.append(raw_line)
                except Exception: pass

    def parse_sensor_string(self, data_str):
        try:
            pwm = int(re.search(r"PWM:(\d+)", data_str).group(1))
            volt = float(re.search(r"V:([\d\.]+)", data_str).group(1))
            curr = float(re.search(r"I:([\d\.]+)", data_str).group(1))
            power = float(re.search(r"P:([\d\.]+)", data_str).group(1))
            thrust = float(re.search(r"T:([\d\.-]+)", data_str).group(1))
            rpm = int(re.search(r"eRPM:(\d+)", data_str).group(1))

            self.lbl_pwm.setText(str(pwm))
            self.lbl_volt.setText(f"{volt:.2f} V")
            self.lbl_curr.setText(f"{curr:.2f} A")
            self.lbl_power.setText(f"{power:.1f} W")
            self.lbl_thrust.setText(f"{thrust:.1f} g")
            self.lbl_rpm.setText(str(rpm))

            self.data_counter += 1
            self.time_axis.append(self.data_counter)
            self.rpm_data.append(rpm); self.thrust_data.append(thrust)
            self.volt_data.append(volt); self.curr_data.append(curr); self.power_data.append(power)
            
            if self.is_recording and self.csv_writer:
                self.csv_writer.writerow([self.data_counter, datetime.now().strftime('%H:%M:%S.%f')[:-3], pwm, volt, curr, power, thrust, rpm])
            
            if len(self.time_axis) > 100:
                self.time_axis.pop(0); self.rpm_data.pop(0); self.thrust_data.pop(0)
                self.volt_data.pop(0); self.curr_data.pop(0); self.power_data.pop(0)
                
            self.curve_rpm.setData(self.time_axis, self.rpm_data)
            self.curve_thrust.setData(self.time_axis, self.thrust_data)
            self.curve_volt.setData(self.time_axis, self.volt_data)
            self.curve_curr.setData(self.time_axis, self.curr_data)
            self.curve_power.setData(self.time_axis, self.power_data)
        except Exception: pass

# ========================================================
# ANA UYGULAMA BAŞLATICISI
# ========================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 1. Aşama: Dosya yolunu garantile ve görseli yükle
    logo_path = resource_path("logo.png")
    splash_pix = QPixmap(logo_path)
    
     # Eğer logon çok büyükse ekranı kaplamaması için ufaltıyoruz (Tercihe bağlı)

    splash_pix = splash_pix.scaled(800, 800, Qt.AspectRatioMode.KeepAspectRatio)

    # Görsel dosyasının varlığını kontrol et
    if splash_pix.isNull():
        print(f"Hata: Logo dosyası bulunamadı! Yol: {logo_path}")
    
    # 2. Aşama: Splash Ekranı oluştur
    splash = QSplashScreen(splash_pix, Qt.WindowType.WindowStaysOnTopHint)
    
    # 3. Aşama: TAM ORTALAMA
    screen_geometry = app.primaryScreen().geometry()
    x = (screen_geometry.width() - splash_pix.width()) // 2
    y = (screen_geometry.height() - splash_pix.height()) // 2
    splash.move(x, y)
    
    splash.show()
    splash.showMessage("Rotary Aerospace Analyzer Başlatılıyor...\nSistem Modülleri Yükleniyor...", 
                       Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter, 
                       QColor("white"))
    app.processEvents()
    
    # Yükleniyor hissi için 2 saniye bekle
    time.sleep(2)
    
    # Ana Pencereyi Tam Ekran Yükle
    window = RotaryTestStandGUI()
    window.showMaximized()
    
    # Splash ekranını kapat
    splash.finish(window)
    
    sys.exit(app.exec())