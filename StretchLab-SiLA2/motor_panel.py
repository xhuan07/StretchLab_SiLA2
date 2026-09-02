# -*- coding: utf-8 -*-
"""
Self-contained control panel for a second motor.

Drop-in additive widget. It owns its own StageController, widgets and
worker threads, and touches none of the main window's self.stage logic,
so the existing motor 1 panel, automation and camera logging keep working
unchanged.

Reuses HomeThread and MoveThread from motor_threads (they already take a
stage object as an argument). Connect uses the same ConnectThread, which
now accepts host/port (see the small edit in motor_threads.py).
"""

from PyQt5.QtWidgets import (QGroupBox, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QDoubleSpinBox, QMessageBox)
from motor_threads import ConnectThread, HomeThread, MoveThread


class MotorPanel(QGroupBox):
    def __init__(self, title, host="192.168.10.2", port=50052, parent=None):
        super().__init__(title, parent)
        self.host = host
        self.port = port
        self.stage = None
        self._build_ui()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        layout = QVBoxLayout()

        self.status_display = QLabel("Status: Disconnected")
        self.status_display.setStyleSheet("font-size: 14px; font-weight: bold; color: gray;")
        layout.addWidget(self.status_display)

        self.pos_display = QLabel("Current Position: -- mm")
        self.pos_display.setStyleSheet("font-size: 14px; font-weight: bold; color: gray;")
        layout.addWidget(self.pos_display)

        self.vel_display = QLabel("Current Velocity: -- mm/s")
        self.vel_display.setStyleSheet("font-size: 14px; font-weight: bold; color: gray;")
        layout.addWidget(self.vel_display)

        # Velocity
        vel_layout = QHBoxLayout()
        vel_layout.addWidget(QLabel("Velocity (mm/s):"))
        self.vel_input = QDoubleSpinBox()
        self.vel_input.setRange(0.001, 2.400)
        self.vel_input.setDecimals(3)
        self.vel_input.setSingleStep(0.1)
        self.vel_input.setValue(1.0)
        vel_layout.addWidget(self.vel_input)
        self.btn_set_vel = QPushButton("Set Velocity")
        self.btn_set_vel.setEnabled(False)
        self.btn_set_vel.clicked.connect(self._set_velocity)
        vel_layout.addWidget(self.btn_set_vel)
        layout.addLayout(vel_layout)

        # Absolute move
        abs_layout = QHBoxLayout()
        abs_layout.addWidget(QLabel("Target (mm):"))
        self.target_input = QDoubleSpinBox()
        self.target_input.setRange(0.0, 50.0)
        self.target_input.setDecimals(3)
        self.target_input.setSingleStep(1.0)
        self.target_input.setValue(10.0)
        abs_layout.addWidget(self.target_input)
        self.btn_move = QPushButton("Move to Target")
        self.btn_move.setEnabled(False)
        self.btn_move.clicked.connect(lambda: self._execute_movement(self.target_input.value(), 'abs'))
        abs_layout.addWidget(self.btn_move)
        layout.addLayout(abs_layout)

        # Relative move
        rel_layout = QHBoxLayout()
        rel_layout.addWidget(QLabel("Relative (mm):"))
        self.rel_input = QDoubleSpinBox()
        self.rel_input.setRange(-50.0, 50.0)   # negative = reverse direction
        self.rel_input.setDecimals(3)
        self.rel_input.setSingleStep(0.1)
        self.rel_input.setValue(1.0)
        rel_layout.addWidget(self.rel_input)
        self.btn_move_rel = QPushButton("Move By Dist")
        self.btn_move_rel.setEnabled(False)
        self.btn_move_rel.clicked.connect(lambda: self._execute_movement(self.rel_input.value(), 'rel'))
        rel_layout.addWidget(self.btn_move_rel)
        layout.addLayout(rel_layout)

        # Connect / Home / Stop
        self.btn_toggle_conn = QPushButton("Connect Motor")
        self.btn_toggle_conn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.btn_toggle_conn.clicked.connect(self._toggle_connection)
        layout.addWidget(self.btn_toggle_conn)

        self.btn_home = QPushButton("Home Device")
        self.btn_home.setEnabled(False)
        self.btn_home.clicked.connect(self._start_homing)
        layout.addWidget(self.btn_home)

        self.btn_stop = QPushButton("STOP")
        self.btn_stop.setStyleSheet("background-color: red; color: white; font-weight: bold; padding: 6px;")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_now)
        layout.addWidget(self.btn_stop)

        layout.addStretch()
        self.setLayout(layout)

    def _set_buttons_connected(self, connected):
        self.btn_move.setEnabled(connected)
        self.btn_move_rel.setEnabled(connected)
        self.btn_home.setEnabled(connected)
        self.btn_stop.setEnabled(connected)
        self.btn_set_vel.setEnabled(connected)

    # -------------------------------------------------------------- Connect
    def _toggle_connection(self):
        if self.stage is None:
            self.status_display.setText("Status: Connecting...")
            self.status_display.setStyleSheet("font-size: 14px; font-weight: bold; color: orange;")
            self.conn_thread = ConnectThread(host=self.host, port=self.port)
            self.conn_thread.finished.connect(self._on_connection_result)
            self.conn_thread.start()
        else:
            self._disconnect()

    def _on_connection_result(self, success, message, stage_obj):
        if success:
            self.stage = stage_obj
            self.status_display.setText("Status: Idle")
            self.status_display.setStyleSheet("font-size: 14px; font-weight: bold; color: green;")
            self.pos_display.setText(f"Current Position: {self.stage.get_position():.3f} mm")
            self.pos_display.setStyleSheet("font-size: 14px; font-weight: bold; color: blue;")
            actual_vel = self.stage.get_current_velocity()
            self.vel_display.setText(f"Current Velocity: {actual_vel:.3f} mm/s")
            self.vel_display.setStyleSheet("font-size: 14px; font-weight: bold; color: blue;")
            self.vel_input.setValue(actual_vel)
            self._set_buttons_connected(True)
            self.btn_toggle_conn.setText("Disconnect")
            self.btn_toggle_conn.setStyleSheet("background-color: #ff9800; color: white; font-weight: bold;")
        else:
            QMessageBox.critical(self, "Connection Error",
                                 f"Failed to connect to {self.title()} at "
                                 f"{self.host}:{self.port}\n{message}")
            self.status_display.setText("Status: Connection Failed")
            self.status_display.setStyleSheet("font-size: 14px; font-weight: bold; color: red;")

    def _disconnect(self):
        if self.stage is not None:
            self.stage.disconnect()
            self.stage = None
        self.status_display.setText("Status: Disconnected")
        self.status_display.setStyleSheet("font-size: 14px; font-weight: bold; color: gray;")
        self.pos_display.setText("Current Position: -- mm")
        self.pos_display.setStyleSheet("font-size: 14px; font-weight: bold; color: gray;")
        self.vel_display.setText("Current Velocity: -- mm/s")
        self.vel_display.setStyleSheet("font-size: 14px; font-weight: bold; color: gray;")
        self._set_buttons_connected(False)
        self.btn_toggle_conn.setText("Connect Motor")
        self.btn_toggle_conn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")

    # ------------------------------------------------------------- Velocity
    def _set_velocity(self):
        if not self.stage:
            return
        if self.stage.set_velocity(self.vel_input.value()):
            actual_vel = self.stage.get_current_velocity()
            self.vel_display.setText(f"Current Velocity: {actual_vel:.3f} mm/s")
            self.vel_display.setStyleSheet("font-size: 14px; font-weight: bold; color: green;")
        else:
            QMessageBox.critical(self, "Error", "Failed to set velocity in hardware.")

    # ----------------------------------------------------------------- Home
    def _start_homing(self):
        if not self.stage:
            return
        self.btn_home.setEnabled(False)
        self.btn_move.setEnabled(False)
        self.btn_move_rel.setEnabled(False)
        self.status_display.setText("Status: Homing...")
        self.status_display.setStyleSheet("font-size: 14px; font-weight: bold; color: orange;")
        self.home_worker = HomeThread(self.stage)
        self.home_worker.finished.connect(self._on_homing_finished)
        self.home_worker.status_update.connect(lambda s: self.pos_display.setText(s))
        self.home_worker.start()

    def _on_homing_finished(self, success, message):
        if success:
            self.pos_display.setText("Current Position: 0.000 mm")
            self.pos_display.setStyleSheet("font-size: 14px; font-weight: bold; color: blue;")
            self.status_display.setText("Status: Idle")
            self.status_display.setStyleSheet("font-size: 14px; font-weight: bold; color: green;")
        else:
            QMessageBox.critical(self, "Homing Error", f"Homing failed:\n{message}")
            self.status_display.setText("Status: Home Failed")
            self.status_display.setStyleSheet("font-size: 14px; font-weight: bold; color: red;")
        self._set_buttons_connected(True)

    # ----------------------------------------------------------------- Move
    def _execute_movement(self, value, mode):
        if not self.stage:
            return
        self.status_display.setText("Status: Moving...")
        self.status_display.setStyleSheet("font-size: 14px; font-weight: bold; color: orange;")
        self.btn_move.setEnabled(False)
        self.btn_move_rel.setEnabled(False)
        self.btn_home.setEnabled(False)
        self.btn_set_vel.setEnabled(False)
        self.move_worker = MoveThread(self.stage, value, mode)
        self.move_worker.pos_update.connect(self._update_pos)
        self.move_worker.finished.connect(self._on_move_finished)
        self.move_worker.start()

    def _update_pos(self, pos):
        self.pos_display.setText(f"Current Position: {pos:.3f} mm")

    def _on_move_finished(self, success, message):
        self._set_buttons_connected(True)
        if success:
            self.status_display.setText("Status: Idle")
            self.status_display.setStyleSheet("font-size: 14px; font-weight: bold; color: green;")
            self.pos_display.setStyleSheet("font-size: 14px; font-weight: bold; color: blue;")
        else:
            self.status_display.setText("Status: Interrupted")
            self.status_display.setStyleSheet("font-size: 14px; font-weight: bold; color: red;")
            self.pos_display.setStyleSheet("font-size: 14px; font-weight: bold; color: red;")

    # ----------------------------------------------------------------- Stop
    def stop_now(self):
        """Stop this motor immediately. Called by the panel's STOP button
        and by the main window's global EMERGENCY STOP."""
        if self.stage is not None:
            self.stage.stop_immediate()
        if hasattr(self, 'move_worker') and self.move_worker.isRunning():
            self.move_worker.request_stop()
        if hasattr(self, 'home_worker') and self.home_worker.isRunning():
            self.home_worker.request_stop()
        self.status_display.setText("Status: STOPPED")
        self.status_display.setStyleSheet("background-color: red; color: white; font-weight: bold; padding: 2px;")
