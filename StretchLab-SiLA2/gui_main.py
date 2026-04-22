# -*- coding: utf-8 -*-
"""
Created on Sat Feb 21 15:59:20 2026

@author: xhuan
"""

import sys
import os
import cv2
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
from automation_threads import AutomationThread
from camera_control import CameraController, CameraThread
#from smu_control import SMUController
#from smu_threads import SMUThread
from dmm_control import DMMController
from dmm_threads import DMMThread
from image_saver import save_frame
from scan_logger import append_scan_log


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
        self.hw_combo.addItems(["Thorlabs Motor (KDC101)", "Live Camera (OpenCV/Vimba)"])
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
            self.hw_combo.setCurrentText("Live Camera (OpenCV/Vimba)")
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
    Dialog for configuring the Step-and-Shoot automated scan.
    Collects parameters for motion, delays, and image saving paths.
    """
    def __init__(self, parent=None, current_pos=0.0):
        super().__init__(parent)
        self.setWindowTitle("Automated Strain Mapping Setup")
        self.setFixedSize(550, 400)
        self.current_pos = current_pos
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout()
        self.setLocale(QLocale(QLocale.C))
        
        # --- 1. Motion Parameters Group ---
        motion_group = QGroupBox("Motion Parameters")
        motion_layout = QFormLayout()
        start_layout = QHBoxLayout()
        self.start_pos = QDoubleSpinBox()
        self.start_pos.setRange(0.0, 50.0)
        self.start_pos.setDecimals(3)
        self.start_pos.setSingleStep(0.1)
        self.start_pos.setValue(self.current_pos) # Default to current hardware position
        
        self.btn_read_current = QPushButton("Read Current")
        self.btn_read_current.setToolTip("Fetch the real-time position from the motor hardware")
        self.btn_read_current.clicked.connect(self._fetch_hardware_position)

        start_layout.addWidget(self.start_pos)
        start_layout.addWidget(self.btn_read_current)
        
        
        self.end_pos = QDoubleSpinBox()
        self.end_pos.setRange(0.0, 50.0)
        self.end_pos.setDecimals(3)
        self.end_pos.setSingleStep(0.1)
        self.end_pos.setValue(self.current_pos + 5.0) # Suggest a 5mm stretch

        self.step_size = QDoubleSpinBox()
        self.step_size.setRange(0.001, 10.0)
        self.step_size.setDecimals(3)
        self.step_size.setSingleStep(0.05)
        self.step_size.setValue(0.5)

        self.settle_time = QDoubleSpinBox()
        self.settle_time.setRange(0.0, 60.0)
        self.settle_time.setSingleStep(0.5)
        self.settle_time.setValue(2.0)
        self.settle_time.setSuffix(" sec") # Add unit suffix for clarity

        motion_layout.addRow("Start Position (mm):", start_layout)
        motion_layout.addRow("End Position (mm):", self.end_pos)
        motion_layout.addRow("Step Size (mm):", self.step_size)
        motion_layout.addRow("Settling Delay:", self.settle_time)
        motion_group.setLayout(motion_layout)
        layout.addWidget(motion_group)

        # --- 2. Storage Settings Group ---
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

        # --- 3. Action Buttons ---
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
        """ Opens a dialog to select the output directory for images. """
        directory = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if directory:
            self.dir_input.setText(directory)

    def _validate_and_accept(self):
        """ Validates user input before closing and accepting the dialog. """
        if not self.dir_input.text():
            QMessageBox.warning(self, "Validation Error", "Please select a directory to save images.")
            return
        if self.step_size.value() <= 0:
            QMessageBox.warning(self, "Validation Error", "Step size must be greater than zero.")
            return
        if self.start_pos.value() == self.end_pos.value():
            QMessageBox.warning(self, "Validation Error", "Start and End positions cannot be the same.")
            return

        self.accept()

    def get_parameters(self):
        """ Returns a dictionary of the configured parameters for the thread. """
        return {
            "start_pos": self.start_pos.value(),
            "end_pos": self.end_pos.value(),
            "step_size": self.step_size.value(),
            "settle_time": self.settle_time.value(),
            "prefix": self.prefix_input.text(),
            "directory": self.dir_input.text()
        }
    def _fetch_hardware_position(self):
        """
        Dynamically queries the motor for its exact current position
        and updates the Start Position spinbox.
        """
        # Access the parent GUI's stage object safely
        parent_gui = self.parent()
        if parent_gui and hasattr(parent_gui, 'stage') and parent_gui.stage:
            try:
                # Query the hardware
                real_time_pos = parent_gui.stage.get_position()
                self.start_pos.setValue(real_time_pos)
                
                # Optional: Auto-shift the End Position to maintain the stretch distance
                # (e.g., if you read a new start, end automatically becomes start + 5mm)
                self.end_pos.setValue(real_time_pos + 5.0) 
            except Exception as e:
                QMessageBox.warning(self, "Hardware Error", f"Failed to read position: {e}")
    
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
    def initUI(self):


        
        icon_path = os.path.join(os.path.dirname(__file__), 'assets', 'logo.png')
        
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            print(f"[Warning] Icon not found at: {icon_path}")


        # Setup Main Window
        self.setWindowTitle("StretchLab Control Station")
        self.setGeometry(100, 100, 1000, 600) 
        self.stage = None
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
        right_layout.addWidget(self._create_control_panel())
        #right_layout.addWidget(self._create_smu_panel())
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
        if self.stage is None or not getattr(self, 'camera_thread', None) or not self.camera_thread.isRunning():
            QMessageBox.warning(self, "Hardware Not Ready", "Please connect BOTH the Motor and the Camera before starting an automated scan.")
            return

        current_pos = self.stage.get_position() if self.stage else 0.0
        dialog = AutomatedScanDialog(self, current_pos=current_pos)
        
        if dialog.exec_() == QDialog.Accepted:
            params = dialog.get_parameters()
            
            # 1. Lock UI to prevent interference
            self.scan_action.setEnabled(False)
            self.btn_toggle_conn.setEnabled(False)
            
            # 2. Create the Progress Dialog (Modal)
            self.progress_dialog = ScanProgressDialog(self)
            
            # 3. Initialize the Automation Thread
            self.auto_thread = AutomationThread(self.stage, params)
            
            # Connect Signals
            self.auto_thread.progress_update.connect(self.progress_dialog.update_progress)
            self.auto_thread.capture_requested.connect(self._execute_automated_capture)
            self.auto_thread.finished.connect(self._on_scan_finished)
            
            # Connect the red Abort button directly to the thread's stop method
            self.progress_dialog.btn_abort.clicked.connect(self.auto_thread.stop)
            
            # 4. Start the engine!
            self.auto_thread.start()
            self.progress_dialog.exec_() # Block main window while scanning


    def _execute_automated_capture(self, file_path):
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
        if resistance_raw is not None and self.stage is not None:
            append_scan_log(
                os.path.join(os.path.dirname(file_path), "scan_log.csv"),
                self.stage.get_position(),
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
        self.btn_toggle_conn.setEnabled(True)

        # Show final result
        if success:
            QMessageBox.information(self, "Scan Complete", message)
        else:
            QMessageBox.warning(self, "Scan Aborted", message)
            # Sync the UI display position in case of an abrupt stop
            if self.stage:
                self._update_pos_ui(self.stage.get_position())
            
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

    def _create_control_panel(self):
        group_box = QGroupBox("MTS50-Z8 Motor Control")
        layout = QVBoxLayout()

        # 1. Status Display
        self.status_display = QLabel("Status: Disconnected")
        self.status_display.setStyleSheet("font-size: 16px; font-weight: bold; color: gray;")
        layout.addWidget(self.status_display)

        # 2. Position Display
        self.pos_display = QLabel("Current Position: -- mm")
        self.pos_display.setStyleSheet("font-size: 16px; font-weight: bold; color: gray;")
        layout.addWidget(self.pos_display)

        # 3. Velocity Display
        self.vel_display = QLabel("Current Velocity: -- mm/s")
        self.vel_display.setStyleSheet("font-size: 16px; font-weight: bold; color: gray;")
        layout.addWidget(self.vel_display)
        
        layout.addSpacing(15) # Add a little gap before the input boxes

        # ==========================================
        # GROUP 1: Velocity Control 
        # ==========================================
        vel_layout = QHBoxLayout()
        vel_layout.addWidget(QLabel("Stretch Velocity (mm/s):"))
        
        self.vel_input = QDoubleSpinBox()
        self.vel_input.setRange(0.001, 2.400) 
        self.vel_input.setDecimals(3)
        self.vel_input.setValue(config.DEFAULT_VELOCITY) 
        self.vel_input.setSingleStep(0.1)
        vel_layout.addWidget(self.vel_input)

        # --- NEW: Dedicated Set Velocity Button ---
        self.btn_set_vel = QPushButton("Set Velocity")
        self.btn_set_vel.setEnabled(False) # Disabled until connected
        self.btn_set_vel.clicked.connect(self._set_velocity_clicked)
        vel_layout.addWidget(self.btn_set_vel)
        
        layout.addLayout(vel_layout)
        
        layout.addSpacing(10) # Add a visual gap between the two groups

        # ==========================================
        # GROUP 2: Position Control
        # ==========================================
        pos_layout = QHBoxLayout()
        pos_layout.addWidget(QLabel("Target Position (mm):"))
        
        self.target_input = QDoubleSpinBox()
        self.target_input.setRange(0.0, 50.0) 
        self.target_input.setDecimals(3)
        self.target_input.setSingleStep(0.1)
        self.target_input.setValue(10.0)
        self.target_input.setSingleStep(1.0)
        pos_layout.addWidget(self.target_input)

        # Move Button (Added ONLY to the horizontal layout)
        self.btn_move = QPushButton("Move to Target")
        self.btn_move.setEnabled(False) 
        self.btn_move.clicked.connect(self._start_moving_absolute)
        pos_layout.addWidget(self.btn_move)
        
        layout.addLayout(pos_layout)
        layout.addSpacing(10)
        rel_layout = QHBoxLayout()
        rel_layout.addWidget(QLabel("Relative Dist (mm):"))
        
        self.rel_input = QDoubleSpinBox()
        self.rel_input.setRange(-50.0, 50.0) # 注意：这里必须允许负数！
        self.rel_input.setDecimals(3)
        self.rel_input.setSingleStep(0.1)
        self.rel_input.setValue(1.0) # 默认相对移动 1mm
        rel_layout.addWidget(self.rel_input)

        self.btn_move_rel = QPushButton("Move By Dist")
        self.btn_move_rel.setEnabled(False) 
        self.btn_move_rel.clicked.connect(self._start_moving_relative) # 绑定相对移动函数
        rel_layout.addWidget(self.btn_move_rel)
        
        layout.addLayout(rel_layout)
        
        # Add a visual separator spacing before global actions
        layout.addSpacing(15)

        # ==========================================
        # GROUP 3: Global Action Buttons
        # ==========================================
        
        # 1. Smart Toggle Connection Button
        self.btn_toggle_conn = QPushButton("Connect Hardware")
        self.btn_toggle_conn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.btn_toggle_conn.clicked.connect(self._toggle_connection)
        layout.addWidget(self.btn_toggle_conn)

        # 2. Home Device Button
        self.btn_home = QPushButton("Home Device")    
        self.btn_home.setEnabled(False)
        self.btn_home.clicked.connect(self._start_homing)
        layout.addWidget(self.btn_home)
        
        # Add extra spacing to isolate the Emergency Stop button
        layout.addSpacing(25) 
        
        # 3. Emergency Stop Button
        self.btn_stop = QPushButton("EMERGENCY STOP")
        self.btn_stop.setStyleSheet("background-color: red; color: white; font-weight: bold; padding: 10px;")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._emergency_stop)
        layout.addWidget(self.btn_stop)

        # Push everything upwards
        layout.addStretch()
        
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

    def _toggle_connection(self):
        """Right Button: Jumps directly to Motor dialog."""
        if self.stage is None:
            self._open_connection_dialog(lock_mode="Motor")
        else:
            self._disconnect_device()
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
        """Opens dialog. Menu uses None, UI buttons use locked modes."""
        if lock_mode == "Motor" and self.stage is not None:
            print("[System] Closing existing motor connection before re-connecting...")
            self.stage.disconnect() 
            self.stage = None 
            
        dialog = HardwareConnectDialog(self, lock_mode=lock_mode)
        
        if dialog.exec_() == QDialog.Accepted:
            hw_type = dialog.selected_hardware
            
            if "Motor" in hw_type:
                sn_to_use = dialog.entered_sn
                model_to_use = dialog.selected_model 
                
                self.pos_display.setText(f"Status: Connecting to {model_to_use}...")
                self.pos_display.setStyleSheet("font-size: 16px; font-weight: bold; color: orange;")
                
                self.conn_thread = ConnectThread(sn_to_use, model_to_use)
                self.conn_thread.finished.connect(self._on_connection_result)
                self.conn_thread.start()
                
            elif "Camera" in hw_type:
                # Ensure the new ID is passed to config memory before thread starts
                config.CAMERA_ID = dialog.entered_cam_id
                print(f"[System] Initiating camera connection with ID: {config.CAMERA_ID}...")
                self._connect_camera()

    def _disconnect_device(self):
        """Safely disconnects the MOTOR hardware and resets the UI state."""
        if self.stage is not None:
            print("[System] Disconnecting motor...")
            self.stage.disconnect() 
            self.stage = None
            
            # 1. Reset Status
            self.status_display.setText("Status: Disconnected")
            self.status_display.setStyleSheet("font-size: 16px; font-weight: bold; color: gray;")
            
            # 2. Reset Position
            self.pos_display.setText("Current Position: -- mm")
            self.pos_display.setStyleSheet("font-size: 16px; font-weight: bold; color: gray;")
            
            # 3. Reset Velocity
            self.vel_display.setText("Current Velocity: -- mm/s")
            self.vel_display.setStyleSheet("font-size: 16px; font-weight: bold; color: gray;")
            
            # Disable hardware buttons
            self.btn_move.setEnabled(False)
            self.btn_home.setEnabled(False)
            self.btn_stop.setEnabled(False)
            self.btn_set_vel.setEnabled(False)
            
            # Revert the toggle button back to Connect mode (Green)
            self.btn_toggle_conn.setText("Connect Hardware")
            self.btn_toggle_conn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
            
            if hasattr(self, 'disconnect_action'):
                self.disconnect_action.setEnabled(False)
            
            QMessageBox.information(self, "Disconnected", "Motor has been safely disconnected.")
    
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
        """
        # 1. THE GATEKEEPER: Stop updating the UI if the stream is paused
        if getattr(self, 'is_frozen', False):
            return 
            
        # 2. THE RAW BUFFER: Save the original, unscaled numpy array for high-res saving
        self._current_raw_frame = cv_img.copy()

        # 3. UI RENDERING: Convert the numpy array to a QPixmap safely
        try:
            shape = cv_img.shape
            
            if len(shape) == 3:
                h, w, ch = shape
                if ch == 1:
                    # Grayscale image with shape (H, W, 1)
                    bytes_per_line = w
                    q_img = QImage(cv_img.data, w, h, bytes_per_line, QImage.Format_Grayscale8)
                else:
                    # Color image with shape (H, W, 3)
                    bytes_per_line = ch * w
                    # Convert BGR (OpenCV default) to RGB (Qt default)
                    cv_img_rgb = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
                    q_img = QImage(cv_img_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
            elif len(shape) == 2:
                # Pure 2D Grayscale image with shape (H, W)
                h, w = shape
                bytes_per_line = w
                q_img = QImage(cv_img.data, w, h, bytes_per_line, QImage.Format_Grayscale8)
            else:
                # Unrecognized format, ignore to prevent crashes
                return 

            # 4. SCALE AND DISPLAY: Fit the image perfectly into the UI label
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

    def _on_gain_changed(self, value):
        """Updates UI label and sends new gain to hardware."""
        # Calculate actual gain value based on the current camera type
        if self.camera_controller.camera_type == 'CV':
            actual_gain = float(value)
            self.gain_val_label.setText(f"{int(actual_gain)}")
        else:
            actual_gain = value / 10.0
            self.gain_val_label.setText(f"{actual_gain:.1f}")
            
        self.camera_controller.set_gain(actual_gain)

    def _on_connection_result(self, success, message, stage_obj):
        """
        Slot function to handle the outcome of the motor connection thread.
        Updates the 3 separate display lines: Status, Position, and Velocity.
        """
        if success:
            # Transfer the connected stage object to the main GUI instance
            self.stage = stage_obj
            
            # Fetch actual hardware status right after connecting
            actual_pos = self.stage.get_position()
            actual_vel = self.stage.get_current_velocity()
            
            # 1. Status
            #self.status_display.setText(f"Status: Connected (SN: {self.stage.sn})")
            self.status_display.setText("Status: Connected")
            self.status_display.setStyleSheet("font-size: 16px; font-weight: bold; color: green;")
            
            # 2. Position
            self.pos_display.setText(f"Current Position: {actual_pos:.3f} mm")
            self.pos_display.setStyleSheet("font-size: 16px; font-weight: bold; color: blue;")
            
            # 3. Velocity
            self.vel_display.setText(f"Current Velocity: {actual_vel:.3f} mm/s")
            self.vel_display.setStyleSheet("font-size: 16px; font-weight: bold; color: blue;")
            
            # Sync the UI input SpinBox with the actual hardware velocity
            # so the user sees the real value in the input box too
            self.vel_input.setValue(actual_vel)
            
            # Show popup
            QMessageBox.information(self, "Connection Success", f"Successfully connected to Motor SN: {self.stage.sn}")
            
            # Enable hardware interaction buttons
            self.btn_move.setEnabled(True)
            self.btn_home.setEnabled(True)
            self.btn_stop.setEnabled(True)
            self.btn_set_vel.setEnabled(True)
            
            # Update the Toggle Button to 'Disconnect' mode
            self.btn_toggle_conn.setText("Disconnect")
            self.btn_toggle_conn.setStyleSheet("background-color: #ff9800; color: white; font-weight: bold;")
            
            if hasattr(self, 'disconnect_action'):
                self.disconnect_action.setEnabled(True)
                
        else:
            # Handle failure: Update all 3 lines to show error state
            QMessageBox.critical(self, "Connection Error", f"Failed to connect to Motor:\n{message}")
            
            self.status_display.setText("Status: Connection Failed")
            self.status_display.setStyleSheet("font-size: 16px; font-weight: bold; color: red;")
            
            self.pos_display.setText("Current Position: -- mm")
            self.vel_display.setText("Current Velocity: -- mm/s")
    def _set_velocity_clicked(self):
        """
        Slot function triggered when the 'Set Velocity' button is clicked.
        Applies the velocity to the hardware and reads it back for verification.
        """
        if not self.stage:
            return
            
        target_vel = self.vel_input.value()
        
        # 1. Send the velocity command to the hardware
        success = self.stage.set_velocity(target_vel)
        
        if success:
            # 2. Read back the actual velocity from hardware registers
            actual_vel = self.stage.get_current_velocity()
            
            # 3. Update the Velocity Display to show the verified value
            self.vel_display.setText(f"Current Velocity: {actual_vel:.3f} mm/s")
            self.vel_display.setStyleSheet("font-size: 14px; font-weight: bold; color: green;")
            
            # 4. Save the new default velocity to config.py
            import utils
            import config
            utils.update_config_file(config.SERIAL_NUMBER, config.STAGE_MODEL, new_velocity=actual_vel)
            
            QMessageBox.information(self, "Velocity Set", f"Velocity successfully set to {actual_vel:.3f} mm/s")
        else:
            QMessageBox.critical(self, "Error", "Failed to set velocity in hardware.")
        
    def _start_homing(self):
        """Initiates the homing process in a background thread."""
        if not self.stage:
            return

        self.btn_home.setEnabled(False)
        self.btn_move.setEnabled(False)
        self.status_display.setText("Status: Homing...")
        self.pos_display.setStyleSheet("font-size: 16px; font-weight: bold; color: orange;")
        
        self.home_worker = HomeThread(self.stage)
        self.home_worker.finished.connect(self._on_homing_finished)

        self.home_worker.status_update.connect(lambda s: self.pos_display.setText(s))
        
        self.home_worker.start()

    def _on_homing_finished(self, success, message):
        """Called when the homing thread finishes."""
        if success:
            QMessageBox.information(self, "Homing", "Device successfully homed at 0.000 mm!")
            self.pos_display.setText("Current Position: 0.000 mm")
            self.pos_display.setStyleSheet("font-size: 16px; font-weight: bold; color: blue;")
        else:
            QMessageBox.critical(self, "Homing Error", f"Homing failed:\n{message}")
            self.pos_display.setText("Status: Home Failed")
            self.pos_display.setStyleSheet("font-size: 16px; font-weight: bold; color: red;")


        self.btn_home.setEnabled(True)
        self.btn_move.setEnabled(True)
        self.btn_stop.setEnabled(True)
        
    def _start_moving_absolute(self):
        self._execute_movement(self.target_input.value(), 'abs')

    def _start_moving_relative(self):       
        self._execute_movement(self.rel_input.value(), 'rel')

    def _execute_movement(self, value, mode):
        if not self.stage:
            return


        # 2. Update the Status Display to indicate movement
        self.status_display.setText("Status: Moving...")
        self.status_display.setStyleSheet("font-size: 14px; font-weight: bold; color: orange;")

        # 3. Lock UI buttons to prevent user interference during motion
        self.btn_move.setEnabled(False)
        self.btn_home.setEnabled(False)
        self.btn_set_vel.setEnabled(False) # Prevent setting velocity while moving
        self.btn_set_vel.setEnabled(False)

        # 4. Start the background thread for movement
        self.move_worker = MoveThread(self.stage, value, mode)
        self.move_worker.pos_update.connect(self._update_pos_ui)
        self.move_worker.finished.connect(self._on_move_finished)
        self.move_worker.start()


    def _update_pos_ui(self, pos):
        """Updates the position display on the UI in real-time."""
        self.pos_display.setText(f"Current Position: {pos:.3f} mm")

    def _on_move_finished(self, success, message):
        """Cleanup and UI reset after movement finishes."""
        self.btn_move.setEnabled(True)
        self.btn_home.setEnabled(True)
        self.btn_set_vel.setEnabled(True)
        
        if success:
            
            #self.status_display.setText(f"Status: Idle (SN: {self.stage.sn})")
            self.status_display.setText("Status: Idle")
            self.status_display.setStyleSheet("font-size: 16px; font-weight: bold; color: green;")

            self.pos_display.setStyleSheet("font-size: 16px; font-weight: bold; color: blue;")
        else:
            # Execution reaches here only if stopped or an error occurred
            self.status_display.setText("Status: Movement Interrupted")
            self.status_display.setStyleSheet("font-size: 16px; font-weight: bold; color: red;")
            self.pos_display.setStyleSheet("font-size: 16px; font-weight: bold; color: red;")

    # --- Emergency Stop Logic ---
    def _emergency_stop(self):
        """The ultimate stop command (Dual-layer protection)."""
        print("!!! EMERGENCY STOP TRIGGERED !!!")
        
        # Layer 1: Send electrical stop command directly to hardware (Highest priority)
        if hasattr(self, 'stage') and self.stage is not None:
            self.stage.stop_immediate()

        # Layer 2: Forcefully break the monitoring loops of any running background threads
        if hasattr(self, 'move_worker') and self.move_worker.isRunning():
            self.move_worker.request_stop()
            
        if hasattr(self, 'home_worker') and self.home_worker.isRunning():
            # A blunt but effective way to kill a thread if it doesn't have a request_stop method
            self.home_worker.request_stop()
        if self.stage:
            self._update_pos_ui(self.stage.get_position())
        # Update UI warnings
        self.status_display.setText("Status: ABORTED BY E-STOP")
        self.status_display.setStyleSheet("background-color: red; color: white; font-size: 16px; font-weight: bold; padding: 2px;")
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