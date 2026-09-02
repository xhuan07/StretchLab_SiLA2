# -*- coding: utf-8 -*-
"""
Created on Sat Feb 21 15:59:20 2026

@author: xhuan
"""

import sys
import os
import cv2
import numpy as np
#import locale
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QDoubleSpinBox, 
                             QGroupBox, QAction, QMessageBox, QDialog, QComboBox, 
                             QLineEdit, QFileDialog, QFormLayout, QProgressBar)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QLocale
import config 
import utils 
utils.load_settings()
from PyQt5.QtGui import QIcon, QImage, QPixmap

from motor_threads import ConnectThread, MoveThread, HomeThread
from motor_panel import MotorPanel
from automation_threads import AutomationThread
from camera_control import CameraController, CameraThread
#from smu_control import SMUController
#from smu_threads import SMUThread
from dmm_control import DMMController
from dmm_threads import DMMThread
from image_saver import save_frame
from scan_logger import append_scan_log

# --- Motor endpoints (each motor = one SiLA server on the Pi) ---
MOTOR_HOST = "192.168.10.2"
MOTOR1_PORT = 50051   # automation and camera logging follow Motor 1
MOTOR2_PORT = 50052


# =============================================================================
# [SECTION 1: SECONDARY WINDOWS / DIALOGS]
# Pop-up windows for settings and hardware setup.
# =============================================================================
class HardwareConnectDialog(QDialog):
    """
    A pop-up dialog for selecting and configuring hardware connections.
    Supports 'lock_mode' to force a specific hardware tab based on the caller.
    """
    def __init__(self, parent=None, lock_mode=None):
        super().__init__(parent)
        self.lock_mode = lock_mode  # Can be "Motor", "Camera", or None
        self.setWindowTitle("Hardware Setup")
        self.setFixedSize(360, 260) 

        self.selected_hardware = None
        self.entered_sn = None
        self.selected_model = None 
        self.entered_cam_id = None  # Stores the auto-detected Camera ID

        self._setup_ui()

    def _setup_ui(self):
        """Builds the dialog interface dynamically."""
        layout = QVBoxLayout()

        # 1. Hardware Selection Dropdown (Hidden if lock_mode is active)
        self.combo_label = QLabel("Select Hardware to Connect:")
        layout.addWidget(self.combo_label)
        
        self.hw_combo = QComboBox()
        # Updated to reflect multi-protocol support
        self.hw_combo.addItems(["Thorlabs Motor (KDC101)", "Live Camera (OpenCV/Vimba/Lumenera)"])
        self.hw_combo.currentIndexChanged.connect(self._toggle_inputs)
        layout.addWidget(self.hw_combo)

        # 2. Motor Specific UI ---
        # self.model_label = QLabel("Select Motor Model:")
        # self.model_combo = QComboBox()
        # models = ["MTS50-Z8", "MTS25-Z8", "Z825B", "Z812B"]
        # self.model_combo.addItems(models)
        
        # if hasattr(config, 'STAGE_MODEL') and config.STAGE_MODEL in models:
        #     self.model_combo.setCurrentText(config.STAGE_MODEL)
            
        # layout.addWidget(self.model_label)
        # layout.addWidget(self.model_combo)

        # self.sn_label = QLabel("Motor Serial Number (SN):")
        # self.sn_input = QLineEdit()
        # self.sn_input.setText(getattr(config, 'SERIAL_NUMBER', '')) 
        # layout.addWidget(self.sn_label)
        # layout.addWidget(self.sn_input)
        self.motor_info_label = QLabel("Connects to Thorlabs KDC101 via SiLA server\nat 192.168.10.2:50052")
        self.motor_info_label.setStyleSheet("color: gray;")
        layout.addWidget(self.motor_info_label)


        # 3. Camera Specific UI (Auto-detection Dropdown) ---
        self.cam_label = QLabel("Select Camera:")
        self.cam_combo = QComboBox()
        
        # Dynamically fetch and populate the available camera list
        available_cams = self.parent().camera_controller.get_available_cameras()
        if available_cams:
            for cam_id, cam_name in available_cams.items():
                # addItem can store both the display name (cam_name) and the hidden underlying ID (cam_id)
                self.cam_combo.addItem(cam_name, cam_id)
        else:
            self.cam_combo.addItem("No Camera Detected", "")
            self.cam_combo.setEnabled(False)

        # If there is a previously connected record in config, attempt to set it as the default option
        stored_id = getattr(config, 'CAMERA_ID', '')
        if stored_id:
            index = self.cam_combo.findData(stored_id)
            if index >= 0:
                self.cam_combo.setCurrentIndex(index)
        
        layout.addWidget(self.cam_label)
        layout.addWidget(self.cam_combo)

        # 4. Buttons (Connect & Cancel)
        btn_layout = QHBoxLayout()
        self.btn_connect = QPushButton("Connect")
        self.btn_cancel = QPushButton("Cancel")
        self.btn_connect.clicked.connect(self._on_connect_clicked)
        self.btn_cancel.clicked.connect(self.reject) 
        btn_layout.addWidget(self.btn_connect)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

        self.setLayout(layout)
        
        # --- Apply Lock Mode Logic ---
        if self.lock_mode == "Motor":
            self.hw_combo.setCurrentText("Thorlabs Motor (KDC101)")
            self.combo_label.setVisible(False)
            self.hw_combo.setVisible(False)
        elif self.lock_mode == "Camera":
            # Updated to match the string in the dropdown
            self.hw_combo.setCurrentText("Live Camera (OpenCV/Vimba/Lumenera)")
            self.combo_label.setVisible(False)
            self.hw_combo.setVisible(False)

        self._toggle_inputs() # Initialize UI visibility


    def _toggle_inputs(self):
        """Shows or hides specific inputs based on hardware selection."""
        is_motor = "Motor" in self.hw_combo.currentText()
        
        # self.model_label.setVisible(is_motor)
        # self.model_combo.setVisible(is_motor)
        # self.sn_label.setVisible(is_motor)
        # self.sn_input.setVisible(is_motor)
        self.motor_info_label.setVisible(is_motor)
        # Replaced with cam_combo for camera selection
        self.cam_label.setVisible(not is_motor)
        self.cam_combo.setVisible(not is_motor)

    def _on_connect_clicked(self):
        """Validates input, saves config, and closes dialog."""
        self.selected_hardware = self.hw_combo.currentText()
        
        if "Motor" in self.selected_hardware:

            # self.entered_sn = self.sn_input.text()
            # self.selected_model = self.model_combo.currentText()
        
            # config.SERIAL_NUMBER = self.entered_sn
            # config.STAGE_MODEL = self.selected_model
            pass
            
        elif "Camera" in self.selected_hardware:
            # Extract the hidden ID bound to the dropdown menu (e.g., "CV_1" or "VMB_DEV1")
            cam_id = self.cam_combo.currentData() 
            if not cam_id:
                QMessageBox.warning(self, "Camera Error", "No valid camera selected!")
                return
                
            self.entered_cam_id = cam_id
            config.CAMERA_ID = cam_id
            if hasattr(utils, 'update_camera_config'):
                utils.update_camera_config(cam_id)

        self.accept()

class AutomatedScanDialog(QDialog):
    """
    Two-motor Step-and-Shoot retreat scan setup.
    Both motors retreat toward 0. Each step shortens the system by the step
    size, with each motor moving half of it. Input is checked so no motor is
    driven below 0.
    """
    def __init__(self, parent=None, pos1=0.0, pos2=0.0):
        super().__init__(parent)
        self.setWindowTitle("Automated Strain Mapping Setup")
        self.setFixedSize(560, 380)
        self.pos1 = pos1
        self.pos2 = pos2
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout()
        self.setLocale(QLocale(QLocale.C))

        motion_group = QGroupBox("Motion Parameters (both motors retreat toward 0)")
        motion_layout = QFormLayout()

        self.distance = QDoubleSpinBox()
        self.distance.setRange(0.001, 50.0)
        self.distance.setDecimals(3)
        self.distance.setSingleStep(0.1)
        self.distance.setValue(5.0)

        self.step_size = QDoubleSpinBox()
        self.step_size.setRange(0.001, 10.0)
        self.step_size.setDecimals(3)
        self.step_size.setSingleStep(0.05)
        self.step_size.setValue(0.5)

        self.settle_time = QDoubleSpinBox()
        self.settle_time.setRange(0.0, 60.0)
        self.settle_time.setSingleStep(0.5)
        self.settle_time.setValue(2.0)
        self.settle_time.setSuffix(" sec")

        cur_label = QLabel(f"Motor 1: {self.pos1:.3f} mm     Motor 2: {self.pos2:.3f} mm")
        cur_label.setStyleSheet("color: gray;")

        motion_layout.addRow("Relative Distance (mm):", self.distance)
        motion_layout.addRow("Step Size (mm):", self.step_size)
        motion_layout.addRow("Settling Delay:", self.settle_time)
        motion_layout.addRow("Current positions:", cur_label)
        motion_group.setLayout(motion_layout)
        layout.addWidget(motion_group)

        storage_group = QGroupBox("Storage Settings")
        storage_layout = QFormLayout()
        self.prefix_input = QLineEdit("Sample_Test")
        dir_layout = QHBoxLayout()
        self.dir_input = QLineEdit()
        self.dir_input.setReadOnly(True)
        self.btn_browse = QPushButton("Browse...")
        self.btn_browse.clicked.connect(self._browse_dir)
        dir_layout.addWidget(self.dir_input)
        dir_layout.addWidget(self.btn_browse)
        storage_layout.addRow("File Prefix:", self.prefix_input)
        storage_layout.addRow("Save To:", dir_layout)
        storage_group.setLayout(storage_layout)
        layout.addWidget(storage_group)

        btn_layout = QHBoxLayout()
        self.btn_start = QPushButton("Start Scan")
        self.btn_start.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px;")
        self.btn_start.clicked.connect(self._validate_and_accept)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setStyleSheet("padding: 8px;")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def _browse_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if directory:
            self.dir_input.setText(directory)

    def _validate_and_accept(self):
        if not self.dir_input.text():
            QMessageBox.warning(self, "Validation Error", "Please select a directory to save images.")
            return
        if self.step_size.value() <= 0:
            QMessageBox.warning(self, "Validation Error", "Step size must be greater than zero.")
            return
        dist = self.distance.value()
        if dist <= 0:
            QMessageBox.warning(self, "Validation Error", "Relative distance must be greater than zero.")
            return
        # Each motor retreats dist/2 toward 0; neither may go below 0.
        half = dist / 2.0
        min_pos = min(self.pos1, self.pos2)
        if min_pos - half < 0:
            max_dist = 2.0 * min_pos
            QMessageBox.warning(
                self, "Validation Error",
                f"Distance too large. Each motor would retreat {half:.3f} mm and pass 0.\n"
                f"Maximum distance from the current positions is {max_dist:.3f} mm.")
            return
        self.accept()

    def get_parameters(self):
        return {
            "distance": self.distance.value(),
            "step_size": self.step_size.value(),
            "settle_time": self.settle_time.value(),
            "prefix": self.prefix_input.text(),
            "directory": self.dir_input.text()
        }

class ScanProgressDialog(QDialog):
    """
    A blocking modal dialog that shows real-time progress of the automated scan.
    Prevents user from clicking other buttons while hardware is busy.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Automated Scan in Progress")
        self.setFixedSize(400, 150)
        # Prevent user from closing it using the 'X' button in the corner
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowCloseButtonHint)
        
        layout = QVBoxLayout()
        
        self.status_label = QLabel("Initializing scan...")
        self.status_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        self.btn_abort = QPushButton("ABORT SCAN")
        self.btn_abort.setStyleSheet("background-color: red; color: white; font-weight: bold; padding: 10px;")
        layout.addWidget(self.btn_abort)
        
        self.setLayout(layout)

    def update_progress(self, percent, text):
        """ Slot to update UI from the background thread """
        self.progress_bar.setValue(percent)
        self.status_label.setText(text)
        
# =============================================================================
# [SECTION 2: MAIN APPLICATION WINDOW]
# The primary interface for StretchLab.
# =============================================================================
class StretchLabGUI(QMainWindow):
    """
    Main Graphical User Interface for Thorlabs Motor and Camera Control.
    """
    def __init__(self):
        super().__init__()
        self.camera_controller = CameraController() 
        self.camera_thread = None
        self.initUI()

    @property
    def stage(self):
        """Compatibility shim: automation and camera logging read
        Motor 1's controller through self.stage."""
        return self.motor1.stage if hasattr(self, 'motor1') else None

    def initUI(self):


        
        icon_path = os.path.join(os.path.dirname(__file__), 'assets', 'logo.png')
        
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            print(f"[Warning] Icon not found at: {icon_path}")


        # Setup Main Window
        self.setWindowTitle("StretchLab Control Station")
        self.setGeometry(100, 100, 1000, 600) 
        #self.smu_controller = SMUController() 
        #self.smu_thread = None
        self.dmm_controller = DMMController() 
        self.dmm_thread = None        

        self._create_menu_bar()

        # Layout Setup
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)

        main_layout.addWidget(self._create_camera_panel(), stretch=2) 
        right_layout = QVBoxLayout()

        # --- Two independent motor panels ---
        motors_row = QHBoxLayout()
        self.motor1 = MotorPanel("Motor 1", host=MOTOR_HOST, port=MOTOR1_PORT)
        self.motor2 = MotorPanel("Motor 2", host=MOTOR_HOST, port=MOTOR2_PORT)
        motors_row.addWidget(self.motor1)
        motors_row.addWidget(self.motor2)
        right_layout.addLayout(motors_row)

        # --- Global emergency stop (both motors) ---
        self.btn_estop_all = QPushButton("EMERGENCY STOP (ALL)")
        self.btn_estop_all.setStyleSheet("background-color: red; color: white; font-weight: bold; padding: 10px;")
        self.btn_estop_all.clicked.connect(self._emergency_stop)
        right_layout.addWidget(self.btn_estop_all)

        right_layout.addWidget(self._create_dmm_panel())
        main_layout.addLayout(right_layout, stretch=1)

    def _create_menu_bar(self):
        menubar = self.menuBar()

        # File Menu
        file_menu = menubar.addMenu("File")
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Hardware Menu
        hw_menu = menubar.addMenu("Hardware")
        # --- CHANGED: Now connects to the dialog opening function ---
        connect_action = QAction("Connection Setup...", self)
        connect_action.triggered.connect(lambda checked=False: self._open_connection_dialog(lock_mode=None)) 
        hw_menu.addAction(connect_action)
        
        # Disconnect Action
        self.disconnect_action = QAction("Disconnect Device", self)
        self.disconnect_action.setEnabled(False) # Default disabled until connected
        hw_menu.addAction(self.disconnect_action)

        # Automation Menu
        auto_menu = menubar.addMenu("Automation")
        self.scan_action = QAction("Start Time-Lapse Scan...", self)
        # Connect the menu button to our new dialog logic
        self.scan_action.triggered.connect(self._open_scan_dialog)
        auto_menu.addAction(self.scan_action)

    def _open_scan_dialog(self):
        """ Opens the config dialog, and if accepted, launches the automated thread. """
        cam_ok = getattr(self, 'camera_thread', None) and self.camera_thread.isRunning()
        if self.motor1.stage is None or self.motor2.stage is None or not cam_ok:
            QMessageBox.warning(self, "Hardware Not Ready", "Please connect BOTH motors and the camera before starting an automated scan.")
            return

        pos1 = self.motor1.stage.get_position()
        pos2 = self.motor2.stage.get_position()
        dialog = AutomatedScanDialog(self, pos1=pos1, pos2=pos2)
        
        if dialog.exec_() == QDialog.Accepted:
            params = dialog.get_parameters()
            
            # 1. Lock UI to prevent interference
            self.scan_action.setEnabled(False)
            self.motor1.btn_toggle_conn.setEnabled(False)
            self.motor2.btn_toggle_conn.setEnabled(False)
            
            # 2. Create the Progress Dialog (Modal)
            self.progress_dialog = ScanProgressDialog(self)
            
            # 3. Initialize the Automation Thread
            self.auto_thread = AutomationThread(self.motor1.stage, self.motor2.stage, params)
            
            # Connect Signals
            self.auto_thread.progress_update.connect(self.progress_dialog.update_progress)
            self.auto_thread.capture_requested.connect(self._execute_automated_capture)
            self.auto_thread.finished.connect(self._on_scan_finished)
            
            # Connect the red Abort button directly to the thread's stop method
            self.progress_dialog.btn_abort.clicked.connect(self.auto_thread.stop)
            
            # 4. Start the engine!
            self.auto_thread.start()
            self.progress_dialog.exec_() # Block main window while scanning


    def _execute_automated_capture(self, file_path, cumulative):
        # 1. 测电阻
        resistance_raw, resistance_str = None, "N/A"
        if self.dmm_controller.dmm is not None:
            resistance_raw, resistance_str = self.dmm_controller.read_single_blocking(self.dmm_thread)
            print(f"[Automation] Resistance: {resistance_str}")

        # 2. 拍照
        if hasattr(self, '_current_raw_frame') and self._current_raw_frame is not None:
            save_frame(file_path, self._current_raw_frame)
        else:
            print("[Automation Error] Frame buffer empty!")

        # 3. 写 CSV
        if resistance_raw is not None:
            append_scan_log(
                os.path.join(os.path.dirname(file_path), "scan_log.csv"),
                cumulative,
                resistance_raw, resistance_str,
                os.path.basename(file_path)
                )

        # 4. 通知线程继续
        if hasattr(self, 'auto_thread'):
            self.auto_thread.capture_done_event.set()


    def _on_scan_finished(self, success, message):
        """ Cleans up the UI after a scan completes or is aborted. """
        # Close the progress dialog
        if hasattr(self, 'progress_dialog'):
            self.progress_dialog.accept()

        # Re-enable UI
        self.scan_action.setEnabled(True)
        self.motor1.btn_toggle_conn.setEnabled(True)
        self.motor2.btn_toggle_conn.setEnabled(True)

        # Show final result
        if success:
            QMessageBox.information(self, "Scan Complete", message)
        else:
            QMessageBox.warning(self, "Scan Aborted", message)
            # Sync the UI display position in case of an abrupt stop
            if self.motor1.stage:
                self.motor1._update_pos(self.motor1.stage.get_position())
            if self.motor2.stage:
                self.motor2._update_pos(self.motor2.stage.get_position())
            
    def _create_camera_panel(self):
        from PyQt5.QtWidgets import QSlider # 确保顶部导入了 QSlider
        
        group_box = QGroupBox("Live Camera Feed")
        layout = QVBoxLayout()
        
        self.camera_label = QLabel("Camera Offline\n(Placeholder for OpenCV Feed)")
        self.camera_label.setAlignment(Qt.AlignCenter)
        self.camera_label.setStyleSheet("background-color: black; color: white; font-size: 20px;")
        self.camera_label.setMinimumSize(640, 480)
        layout.addWidget(self.camera_label)

        # 1. Base Controls (Connect & Pause)
        cam_ctrl_layout = QHBoxLayout()
        self.btn_toggle_cam = QPushButton("Connect Camera")
        self.btn_toggle_cam.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px;")
        self.btn_toggle_cam.clicked.connect(self._toggle_camera_connection)
        cam_ctrl_layout.addWidget(self.btn_toggle_cam)
        
        self.btn_freeze = QPushButton("Pause Stream")
        self.btn_freeze.setCheckable(True)
        self.btn_freeze.setEnabled(False) 
        self.btn_freeze.setStyleSheet("padding: 8px;")
        self.btn_freeze.clicked.connect(self._toggle_freeze)
        cam_ctrl_layout.addWidget(self.btn_freeze)
        layout.addLayout(cam_ctrl_layout)
        
        # ==========================================
        # --- NEW: Exposure & Gain Sliders ---
        # ==========================================
        sliders_layout = QVBoxLayout()
        
        # Exposure Slider (Microseconds)
        exp_layout = QHBoxLayout()
        exp_layout.addWidget(QLabel("Exposure (µs):"))
        self.exp_slider = QSlider(Qt.Horizontal)
        self.exp_slider.setRange(100, 50000) # Range: 100µs to 50ms
        self.exp_slider.setValue(10000) # Default 10ms
        self.exp_slider.setEnabled(False)
        self.exp_slider.valueChanged.connect(self._on_exposure_changed)
        self.exp_val_label = QLabel("10000")
        self.exp_val_label.setFixedWidth(80)
        exp_layout.addWidget(self.exp_slider)
        exp_layout.addWidget(self.exp_val_label)
        sliders_layout.addLayout(exp_layout)
        
        # Gain Slider (Decibels)
        gain_layout = QHBoxLayout()
        gain_layout.addWidget(QLabel("Gain (dB):"))
        self.gain_slider = QSlider(Qt.Horizontal)
        self.gain_slider.setRange(0, 240) # Range: 0.0 to 24.0 dB (multiplied by 10 for int slider)
        self.gain_slider.setValue(0)
        self.gain_slider.setEnabled(False)
        self.gain_slider.valueChanged.connect(self._on_gain_changed)
        self.gain_val_label = QLabel("0.0")
        self.gain_val_label.setFixedWidth(50)
        gain_layout.addWidget(self.gain_slider)
        gain_layout.addWidget(self.gain_val_label)
        sliders_layout.addLayout(gain_layout)
        
        layout.addLayout(sliders_layout)
        group_box.setLayout(layout)
        return group_box

 #   def _create_smu_panel(self):
 #       """ Creates the UI panel for the Keithley 2450 SourceMeter. """
 #       group_box = QGroupBox("Keithley 2450 SourceMeter")
 #       layout = QVBoxLayout()
 #
 #       # 1. Connection Status
 #       self.smu_status_display = QLabel("Status: Disconnected")
 #       self.smu_status_display.setStyleSheet("font-size: 14px; font-weight: bold; color: gray;")
 #       layout.addWidget(self.smu_status_display)

        # 2. Giant LCD-style display for the measurement
 #       self.smu_value_display = QLabel("-----")
 #       self.smu_value_display.setAlignment(Qt.AlignCenter)
 #       self.smu_value_display.setStyleSheet("""
 #           background-color: black; 
 #           color: #00FF00; 
 #           font-size: 32px; 
 #           font-family: 'Courier New', monospace;
 #           font-weight: bold;
 #           padding: 10px;
 #           border-radius: 5px;
 #       """)
 #       layout.addWidget(self.smu_value_display)

        # 3. Control Buttons
 #       btn_layout = QHBoxLayout()
        
 #       self.btn_smu_conn = QPushButton("Connect SMU")
 #       self.btn_smu_conn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
 #       self.btn_smu_conn.clicked.connect(self._toggle_smu_connection)
        
 #       self.btn_smu_outp = QPushButton("Output ON")
 #       self.btn_smu_outp.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
 #       self.btn_smu_outp.setEnabled(False) # Disabled until connected
 #       self.btn_smu_outp.setCheckable(True)
 #       self.btn_smu_outp.clicked.connect(self._toggle_smu_output)
        
 #       btn_layout.addWidget(self.btn_smu_conn)
 #       btn_layout.addWidget(self.btn_smu_outp)
 #       layout.addLayout(btn_layout)

 #       group_box.setLayout(layout)
 #      return group_box

    def _create_dmm_panel(self):
        """ Creates the UI panel for the Keysight 34465A DMM. """
        group_box = QGroupBox("Keysight 34465A DMM")
        layout = QVBoxLayout()

        # 1. VISA Address Input (Crucial for DMM targeting)
        # visa_layout = QHBoxLayout()
        # visa_layout.addWidget(QLabel("VISA:"))
        #self.dmm_visa_input = QLineEdit("USB0::0x2A8D::0x0101::MY54504800::INSTR") # Replace with your default address
        self.dmm_visa_input = QLabel("Connects via SiLA server at 192.168.10.2:50053")
        self.dmm_visa_input.setStyleSheet("color: gray;")
        # visa_layout.addWidget(self.dmm_visa_input)
        # layout.addLayout(visa_layout)

        # 2. Connection Status
        self.dmm_status_display = QLabel("Status: Disconnected")
        self.dmm_status_display.setStyleSheet("font-size: 14px; font-weight: bold; color: gray;")
        layout.addWidget(self.dmm_status_display)

        # 3. Giant LCD-style display for the measurement
        self.dmm_value_display = QLabel("-----")
        self.dmm_value_display.setAlignment(Qt.AlignCenter)
        self.dmm_value_display.setStyleSheet("""
            background-color: black; 
            color: #00FFFF; 
            font-size: 32px; 
            font-family: 'Courier New', monospace;
            font-weight: bold;
            padding: 10px;
            border-radius: 5px;
        """)
        layout.addWidget(self.dmm_value_display)

        # 4. Control Buttons (Simplified: Just Connect/Disconnect)
        btn_layout = QHBoxLayout()
        
        self.btn_dmm_conn = QPushButton("Connect DMM")
        self.btn_dmm_conn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.btn_dmm_conn.clicked.connect(self._toggle_dmm_connection)
        
        btn_layout.addWidget(self.btn_dmm_conn)
        layout.addLayout(btn_layout)

        group_box.setLayout(layout)
        return group_box
    def _open_connection_dialog(self, lock_mode=None):
        """Camera connection setup. Motors connect from their own panels."""
        dialog = HardwareConnectDialog(self, lock_mode=lock_mode)

        if dialog.exec_() == QDialog.Accepted:
            hw_type = dialog.selected_hardware
            if "Motor" in hw_type:
                QMessageBox.information(self, "Motor Connection",
                                        "Connect each motor from its own panel "
                                        "using the 'Connect Motor' button.")
            elif "Camera" in hw_type:
                config.CAMERA_ID = dialog.entered_cam_id
                print(f"[System] Initiating camera connection with ID: {config.CAMERA_ID}...")
                self._connect_camera()

    # =============================================================================
    # [CAMERA CONTROL LOGIC]
    # =============================================================================
    
    def _toggle_camera_connection(self):
        """
        Acts as a smart router for the Camera: opens connection dialog if offline, 
        or completely stops the stream and releases hardware if currently running.
        """
        if self.camera_thread and self.camera_thread.isRunning():
            self._disconnect_camera()
        else:
            self._open_connection_dialog(lock_mode="Camera")


    def _connect_camera(self):
        """Initializes and starts the background camera thread."""
        cam_id = getattr(config, 'CAMERA_ID', None)
        if not cam_id:
            QMessageBox.warning(self, "Camera Error", "No Camera ID found in config.")
            return

        self.btn_toggle_cam.setEnabled(False)
        self.btn_toggle_cam.setText("Connecting...")
        QApplication.processEvents()
        
        opened_device = self.camera_controller.open_camera(cam_id)
        if opened_device:
            self.camera_thread = CameraThread(self.camera_controller)
            self.camera_thread.frame_ready.connect(self._update_camera_frame)
            self.camera_thread.error_occurred.connect(self._on_camera_error)
            self.camera_thread.start()
            
            # --- NEW: Dynamically adjust slider ranges based on camera protocol ---

            if self.camera_controller.camera_type == 'CV':
                # Measured DirectShow exposure range is -14 to -1
                self.exp_slider.setRange(-14, -1)
                self.exp_slider.setValue(-7) # Default to approx 7.8 ms
                self.gain_slider.setRange(0, 100)
                self.gain_slider.setValue(0)
            elif self.camera_controller.camera_type == 'VMB':
                # Vimba exposure is in microseconds
                self.exp_slider.setRange(100, 50000)
                self.exp_slider.setValue(10000)
                self.gain_slider.setRange(0, 240)
                self.gain_slider.setValue(0)
            elif self.camera_controller.camera_type == 'LUC':
                # Lumenera INFINITY: exposure 0.064 ~ 394.24 ms, gain 1.0 ~ 7.75x
                # Slider uses x100 for 0.01ms precision
                self.exp_slider.setRange(6, 39424)  # 0.06ms ~ 394.24ms
                self.exp_slider.setValue(400)  # Default 4ms
                
                self.gain_slider.setRange(10, 78)  # 1.0x ~ 7.8x (x10)
                self.gain_slider.setValue(10)  # Default 1.0x
            # ------------------------------------------

            self.btn_toggle_cam.setText("Disconnect Camera")
            self.btn_toggle_cam.setStyleSheet("background-color: #f44336; color: white; font-weight: bold; padding: 8px;")
            self.btn_toggle_cam.setEnabled(True)
            
            self.is_frozen = False
            self.btn_freeze.setChecked(False)
            self.btn_freeze.setText("Pause Stream")
            self.btn_freeze.setStyleSheet("padding: 8px;")
            self.btn_freeze.setEnabled(True)
            self.exp_slider.setEnabled(True)
            self.gain_slider.setEnabled(True)

            self._on_exposure_changed(self.exp_slider.value())
            self._on_gain_changed(self.gain_slider.value())
        else:
            QMessageBox.critical(self, "Hardware Error", "Could not access Camera.\nCheck cables or ID.")
            self.btn_toggle_cam.setText("Connect Camera")
            self.btn_toggle_cam.setEnabled(True)


    def _disconnect_camera(self):
        """Safely stops the camera stream and resets the UI."""
        # 1. Stop the background hardware thread completely
        if self.camera_thread and self.camera_thread.isRunning():
            self.camera_thread.stop()
        
        self.camera_controller.close_camera()
        # 2. Clear the screen
        self.camera_label.clear()
        self.camera_label.setText("Camera Offline\n(Stream Stopped)")
        
        # 3. Transform Button 1 back to 'Connect'
        self.btn_toggle_cam.setText("Connect Camera")
        self.btn_toggle_cam.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px;")
        
        # 4. Disable Button 2 (Pause)
        self.is_frozen = False
        self.btn_freeze.setChecked(False)
        self.btn_freeze.setText("Pause Stream")
        self.btn_freeze.setStyleSheet("padding: 8px;")
        self.btn_freeze.setEnabled(False)
        # Disable Sliders
        self.exp_slider.setEnabled(False)
        self.gain_slider.setEnabled(False)

    def _toggle_freeze(self, is_checked):
        """
        Toggles the 'frozen' state of the camera display.
        The underlying Vimba stream continues to run, but GUI updates are skipped.
        """
        self.is_frozen = is_checked
        
        if is_checked:
            self.btn_freeze.setText("Resume Stream")
            self.btn_freeze.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; padding: 8px;")
        else:
            self.btn_freeze.setText("Pause Stream")
            self.btn_freeze.setStyleSheet("padding: 8px;")

    def _update_camera_frame(self, cv_img):
        """
        Slot function called every time the background thread emits a new frame.
        Handles UI freezing, raw frame buffering, and dynamic format conversion.
        Supports 8-bit and 16-bit (Lumenera) inputs.
        """
        # 1. THE GATEKEEPER: Stop updating the UI if the stream is paused
        if getattr(self, 'is_frozen', False):
            return 
            
        # 2. THE RAW BUFFER: Save the original, unscaled numpy array for high-res saving
        self._current_raw_frame = cv_img.copy()

        # 3. BIT-DEPTH NORMALIZATION: Convert 16-bit to 8-bit for display only
        display_img = cv_img
        if cv_img.dtype == np.uint16:
            # Shift 12-bit sensor data (0-4095) down to 8-bit (0-255)
            display_img = (cv_img >> 4).astype(np.uint8)
        elif cv_img.dtype != np.uint8:
            display_img = cv_img.astype(np.uint8)

        # 4. UI RENDERING: Convert the numpy array to a QPixmap safely
        try:
            shape = display_img.shape
            
            if len(shape) == 3:
                h, w, ch = shape
                if ch == 1:
                    bytes_per_line = w
                    q_img = QImage(display_img.data, w, h, bytes_per_line, QImage.Format_Grayscale8)
                else:
                    bytes_per_line = ch * w
                    cv_img_rgb = cv2.cvtColor(display_img, cv2.COLOR_BGR2RGB)
                    q_img = QImage(cv_img_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
            elif len(shape) == 2:
                h, w = shape
                bytes_per_line = w
                q_img = QImage(display_img.data, w, h, bytes_per_line, QImage.Format_Grayscale8)
            else:
                return 

            # 5. SCALE AND DISPLAY: Fit the image perfectly into the UI label
            pixmap = QPixmap.fromImage(q_img)
            self.camera_label.setPixmap(pixmap.scaled(
                self.camera_label.width(), 
                self.camera_label.height(), 
                Qt.KeepAspectRatio
            ))
            
        except Exception as e:
            print(f"[GUI Error] Failed to render frame: {e}")
        
    def _on_camera_error(self, message):
        """Handles camera connection or streaming errors."""
        QMessageBox.critical(self, "Camera Error", message)
        self._disconnect_camera()
        
    def _on_exposure_changed(self, value):
        """ Updates UI label with human-readable time and sends raw log value to hardware. """
        if not hasattr(self, 'camera_controller') or not self.camera_controller.camera:
            return

        if self.camera_controller.camera_type == 'CV':
            # Calculate exposure time in milliseconds: Time = (2 ^ value) * 1000
            exposure_ms = (2 ** value) * 1000.0
            
            # Format UI text dynamically based on the length of the time
            if exposure_ms < 1.0:
                # Convert to microseconds if it's super fast
                exposure_us = exposure_ms * 1000.0
                self.exp_val_label.setText(f"{exposure_us:.0f} µs")
            else:
                self.exp_val_label.setText(f"{exposure_ms:.1f} ms")
                
            # Send the raw log value (e.g., -7) back to the hardware
            self.camera_controller.set_exposure(value)
            
        elif self.camera_controller.camera_type == 'VMB':
            # Vimba natively uses microseconds
            self.exp_val_label.setText(f"{value} µs")
            self.camera_controller.set_exposure(value)

        elif self.camera_controller.camera_type == 'LUC':
            # LuCam: slider value is ms * 100, actual exposure is in ms
            actual_ms = value / 100.0
            self.exp_val_label.setText(f"{actual_ms:.2f} ms")
            self.camera_controller.set_exposure(actual_ms)

    def _on_gain_changed(self, value):
        """Updates UI label and sends new gain to hardware."""
        if self.camera_controller.camera_type == 'CV':
            actual_gain = float(value)
            self.gain_val_label.setText(f"{int(actual_gain)}")
        elif self.camera_controller.camera_type == 'LUC':
            # LuCam gain: slider is x10, actual is a multiplier (e.g. 1.0x ~ 8.0x)
            actual_gain = value / 10.0
            self.gain_val_label.setText(f"{actual_gain:.1f}x")
        else:
            # VMB: dB scale
            actual_gain = value / 10.0
            self.gain_val_label.setText(f"{actual_gain:.1f}")
            
        self.camera_controller.set_gain(actual_gain)

    # --- Emergency Stop Logic ---
    def _emergency_stop(self):
        """Stop BOTH motors immediately."""
        print("!!! EMERGENCY STOP TRIGGERED !!!")
        if hasattr(self, 'motor1'):
            self.motor1.stop_now()
        if hasattr(self, 'motor2'):
            self.motor2.stop_now()
        QMessageBox.warning(self, "E-STOP", "All motion halted!")
        
    # =============================================================================
    # [SMU CONTROL LOGIC]
    # =============================================================================
    # def _toggle_smu_connection(self):
    #     """ Handles Connect/Disconnect button clicks for the SMU. """
    #     if self.smu_controller.smu is None: # Currently disconnected, try to connect
    #         self.smu_status_display.setText("Status: Connecting...")
    #         QApplication.processEvents() # Force UI update
            
    #         success, msg = self.smu_controller.connect()
    #         if success:
    #             # 1. Setup hardware for resistance mode by default
    #             self.smu_controller.setup_measure_resistance()
                
    #             # 2. Update UI
    #             self.smu_status_display.setText(f"Status: {msg}")
    #             self.smu_status_display.setStyleSheet("color: green; font-weight: bold;")
    #             self.btn_smu_conn.setText("Disconnect SMU")
    #             self.btn_smu_conn.setStyleSheet("background-color: #ff9800; color: white; font-weight: bold;")
    #             self.btn_smu_outp.setEnabled(True)
                
    #             # 3. Start the background polling thread
    #             self.smu_thread = SMUThread(self.smu_controller)
    #             self.smu_thread.data_ready.connect(self._update_smu_display)
    #             self.smu_thread.start()
    #         else:
    #             QMessageBox.critical(self, "SMU Connection Error", msg)
    #             self.smu_status_display.setText("Status: Disconnected")
                
    #     else: # Currently connected, disconnect
    #         # Stop thread first
    #         if self.smu_thread and self.smu_thread.isRunning():
    #             self.smu_thread.stop()
            
    #         # Reset hardware and UI
    #         self.smu_controller.disconnect()
    #         self.smu_status_display.setText("Status: Disconnected")
    #         self.smu_status_display.setStyleSheet("color: gray; font-weight: bold;")
    #         self.smu_value_display.setText("-----")
            
    #         self.btn_smu_conn.setText("Connect SMU")
    #         self.btn_smu_conn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
            
    #         self.btn_smu_outp.setChecked(False)
    #         self.btn_smu_outp.setText("Output ON")
    #         self.btn_smu_outp.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
    #         self.btn_smu_outp.setEnabled(False)

    # def _toggle_smu_output(self, is_checked):
    #     """ Turns the SMU physical output on or off. """
    #     if is_checked:
    #         self.smu_controller.output_on()
    #         self.btn_smu_outp.setText("Output OFF")
    #         self.btn_smu_outp.setStyleSheet("background-color: #f44336; color: white; font-weight: bold;")
    #     else:
    #         self.smu_controller.output_off()
    #         self.btn_smu_outp.setText("Output ON")
    #         self.btn_smu_outp.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")

    # def _update_smu_display(self, value):
    #     """ Slot function to update the LCD display with fresh SMU data. """
    #     # Only show values if the output is actually turned on, else show a standby message
    #     if self.btn_smu_outp.isChecked():
    #         # Format in scientific notation (e.g., 1.2345e+03 Ω)
    #         self.smu_value_display.setText(f"{value:.4e} Ω")
    #     else:
    #         self.smu_value_display.setText("STANDBY")
    # =============================================================================
    # [DMM CONTROL LOGIC]
    # =============================================================================
    def _toggle_dmm_connection(self):
        """ Handles Connect/Disconnect button clicks for the DMM. """
        if self.dmm_controller.dmm is None: 
            # Currently disconnected, try to connect
            self.dmm_status_display.setText("Status: Connecting...")
            QApplication.processEvents() # Force UI update
            
            # Fetch the VISA address from the UI input
            # visa_addr = self.dmm_visa_input.text().strip()
            # self.dmm_controller.resource_name = visa_addr
            
            success, msg = self.dmm_controller.connect()
            if success:
                # 1. Setup hardware for DC Voltage mode by default
                self.dmm_controller.setup_measure_resistance()
                
                # 2. Update UI
                self.dmm_status_display.setText(f"Status: {msg}")
                self.dmm_status_display.setStyleSheet("color: green; font-weight: bold;")
                self.btn_dmm_conn.setText("Disconnect DMM")
                self.btn_dmm_conn.setStyleSheet("background-color: #ff9800; color: white; font-weight: bold;")
                # self.dmm_visa_input.setEnabled(False) # Lock the VISA input
                
                # 3. Start the background polling thread immediately
                self.dmm_thread = DMMThread(self.dmm_controller)
                self.dmm_thread.data_ready.connect(self._update_dmm_display)
                self.dmm_thread.start()
            else:
                QMessageBox.critical(self, "DMM Connection Error", msg)
                self.dmm_status_display.setText("Status: Disconnected")
                
        else: 
            # Currently connected, disconnect
            # Stop thread first
            if self.dmm_thread and self.dmm_thread.isRunning():
                self.dmm_thread.stop()
            
            # Reset hardware and UI
            self.dmm_controller.disconnect()
            self.dmm_status_display.setText("Status: Disconnected")
            self.dmm_status_display.setStyleSheet("color: gray; font-weight: bold;")
            self.dmm_value_display.setText("-----")
            
            self.btn_dmm_conn.setText("Connect DMM")
            self.btn_dmm_conn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
            # self.dmm_visa_input.setEnabled(True)

    def _update_dmm_display(self, value):
        """ Slot function to update the LCD display with fresh DMM data. """
        # Format as Voltage with high precision (e.g., 5.123456 V)
        self.dmm_value_display.setText(self.dmm_controller.format_resistance(value))

if __name__ == "__main__":
    import ctypes

    myappid = 'diaolab.stretchlab.motorcontrol.v1' 
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    
    app = QApplication(sys.argv)
    window = StretchLabGUI()
    window.show()
    sys.exit(app.exec_())