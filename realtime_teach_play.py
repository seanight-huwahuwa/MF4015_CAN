import sys
import time
import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QHBoxLayout
from PyQt6.QtCore import QThread, pyqtSignal
from myactuator_motor import MyActuatorMotor

class MotorControlThread(QThread):
    update_plot_signal = pyqtSignal(float, float, float)
    status_msg_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.motor = None
        self.running = True
        self.state = "IDLE"
        self.trajectory = []
        self.start_time = 0
        self.play_start_time = 0
        
        self.D_GAIN_TEACH = 0.002
        self.P_GAIN_PLAY = 0.02   
        self.D_GAIN_PLAY = 0.002  
        self.MAX_TORQUE = 2.0     
        
        self.last_angle = 0
        self.last_time = 0
        self.filtered_speed = 0.0

    def run(self):
        try:
            self.motor = MyActuatorMotor(channel='/dev/cu.usbmodem2089337D36301')
            if not self.motor.bus:
                self.status_msg_signal.emit("모터 연결 실패. USB 포트를 확인하세요.")
                return
            self.status_msg_signal.emit("모터 연결 성공. 대기 중...")
            
            while self.running:
                current_time = time.time()
                dt = current_time - self.last_time
                if dt < 0.01:
                    time.sleep(0.001)
                    continue
                    
                current_angle = self.motor.read_multi_turn_angle()
                current_speed = (current_angle - self.last_angle) / dt if dt > 0 else 0
                
                # Low-Pass Filter (LPF) 추가 - 고주파 노이즈 제거 및 진동 억제
                ALPHA = 0.5 # 0.0 ~ 1.0 (값이 작을수록 부드러워짐. 이전 0.15는 지연(Delay)을 유발해 통통 튀는 현상 발생)
                self.filtered_speed = (ALPHA * current_speed) + ((1.0 - ALPHA) * self.filtered_speed)
                
                if self.state == "TEACH":
                    t = current_time - self.start_time
                    self.trajectory.append((t, current_angle))
                    
                    damping_torque = -self.D_GAIN_TEACH * self.filtered_speed
                    damping_torque = max(-self.MAX_TORQUE, min(self.MAX_TORQUE, damping_torque))
                    self.motor.set_torque(damping_torque)
                    self.update_plot_signal.emit(t, current_angle, current_angle)
                    
                elif self.state == "PLAY":
                    if not self.trajectory:
                        self.state = "IDLE"
                        continue
                        
                    t = current_time - self.play_start_time
                    target_angle = current_angle
                    
                    if t >= self.trajectory[-1][0]:
                        target_angle = self.trajectory[-1][1]
                    else:
                        for i in range(len(self.trajectory) - 1):
                            if self.trajectory[i][0] <= t < self.trajectory[i+1][0]:
                                t0, a0 = self.trajectory[i]
                                t1, a1 = self.trajectory[i+1]
                                ratio = (t - t0) / (t1 - t0)
                                target_angle = a0 + ratio * (a1 - a0)
                                break
                    
                    # 소프트웨어 토크 제어(Impedance Control) 대신 모터의 하드웨어 위치 제어(0xA4) 사용
                    # 모터 드라이버 내부의 10kHz+ 고속 PID 루프를 타게 되므로 훨씬 부드럽고 정확합니다.
                    MAX_PLAY_SPEED = 1440 # 재생 시 최대 속도 제한 (dps)
                    self.motor.set_absolute_position(target_angle, MAX_PLAY_SPEED)
                    self.update_plot_signal.emit(t, target_angle, current_angle)
                    
                elif self.state == "IDLE":
                    self.motor.set_torque(0)
                    self.update_plot_signal.emit(0, current_angle, current_angle)
                
                self.last_angle = current_angle
                self.last_time = current_time
        except Exception as e:
            print(f"Loop 오류: {e}")
        finally:
            if self.motor:
                self.motor.shutdown()

    def start_teach(self):
        self.trajectory = []
        self.start_time = time.time()
        self.state = "TEACH"
        self.status_msg_signal.emit("TEACH 모드: 손으로 모터를 움직여주세요... (녹화 중)")

    def start_play(self):
        if not self.trajectory:
            self.status_msg_signal.emit("저장된 궤적이 없습니다.")
            return
        
        current_actual_angle = self.last_angle
        trajectory_start_angle = self.trajectory[0][1]
        offset = current_actual_angle - trajectory_start_angle
        for i in range(len(self.trajectory)):
            t, a = self.trajectory[i]
            self.trajectory[i] = (t, a + offset)
            
        self.play_start_time = time.time()
        self.state = "PLAY"
        self.status_msg_signal.emit(f"PLAY 모드: 재생 중 (오프셋 보정 완료)")

    def stop(self):
        self.state = "IDLE"
        self.status_msg_signal.emit("IDLE: 정지 (모터 자유 상태)")

    def quit_thread(self):
        self.running = False
        self.wait()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Real-Time Teach & Play")
        self.resize(800, 600)
        
        main_widget = QWidget()
        layout = QVBoxLayout()
        main_widget.setLayout(layout)
        self.setCentralWidget(main_widget)
        
        self.plot_widget = pg.PlotWidget(title="Target vs Actual Angle")
        self.plot_widget.setLabel('left', 'Angle (deg)')
        self.plot_widget.addLegend()
        layout.addWidget(self.plot_widget)
        
        self.target_line = self.plot_widget.plot(pen=pg.mkPen('r', width=2, style=pg.QtCore.Qt.PenStyle.DashLine), name='Target')
        self.actual_line = self.plot_widget.plot(pen=pg.mkPen('g', width=2), name='Actual')
        
        self.time_data = []
        self.target_data = []
        self.actual_data = []
        self.max_pts = 500
        
        btn_layout = QHBoxLayout()
        
        self.btn_teach = QPushButton("⚫ TEACH")
        self.btn_teach.clicked.connect(self.on_teach)
        
        self.btn_play = QPushButton("▶ PLAY")
        self.btn_play.clicked.connect(self.on_play)
        
        self.btn_stop = QPushButton("⏹ STOP")
        self.btn_stop.clicked.connect(self.on_stop)
        
        btn_layout.addWidget(self.btn_teach)
        btn_layout.addWidget(self.btn_play)
        btn_layout.addWidget(self.btn_stop)
        layout.addLayout(btn_layout)
        
        self.status_label = QPushButton("상태: 초기화 중...")
        self.status_label.setFlat(True)
        self.status_label.setStyleSheet("text-align: left; padding: 10px; font-size: 14px;")
        layout.addWidget(self.status_label)
        
        self.motor_thread = MotorControlThread()
        self.motor_thread.update_plot_signal.connect(self.update_plot)
        self.motor_thread.status_msg_signal.connect(self.update_status)
        self.motor_thread.start()

    def on_teach(self):
        self.clear_data()
        self.motor_thread.start_teach()
        
    def on_play(self):
        self.clear_data()
        self.motor_thread.start_play()
        
    def on_stop(self):
        self.motor_thread.stop()
        
    def clear_data(self):
        self.time_data.clear()
        self.target_data.clear()
        self.actual_data.clear()
        self.target_line.setData([], [])
        self.actual_line.setData([], [])

    def update_status(self, msg):
        self.status_label.setText(f"상태: {msg}")
        
    def update_plot(self, t, target, actual):
        if self.motor_thread.state == "IDLE" and len(self.time_data) > 0: return
        self.time_data.append(t)
        self.target_data.append(target)
        self.actual_data.append(actual)
        if len(self.time_data) > self.max_pts:
            self.time_data = self.time_data[-self.max_pts:]
            self.target_data = self.target_data[-self.max_pts:]
            self.actual_data = self.actual_data[-self.max_pts:]
        self.target_line.setData(self.time_data, self.target_data)
        self.actual_line.setData(self.time_data, self.actual_data)
        
    def closeEvent(self, event):
        self.motor_thread.quit_thread()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
