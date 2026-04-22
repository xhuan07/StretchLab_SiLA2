# -*- coding: utf-8 -*-
"""
Created on Mon Feb 23 15:22:44 2026

@author: xhuan
"""
from PyQt5.QtCore import QThread, pyqtSignal
import time
from motor_control import StageController

class ConnectThread(QThread):
    """Background thread for connecting hardware to prevent GUI freezing."""
    finished = pyqtSignal(bool, str, object)

    def __init__(self, sn, stage_model="MTS50-Z8"):
        super().__init__()

    def run(self):
        try:
            stage = StageController()
            success, msg = stage.connect()  
            if success:
                self.finished.emit(True, msg, stage)
            else:
                self.finished.emit(False, msg, None)
        except Exception as e:
            self.finished.emit(False, str(e), None)

class HomeThread(QThread):
    """Worker thread to handle the homing sequence."""
    finished = pyqtSignal(bool, str)
    status_update = pyqtSignal(str) 

    def __init__(self, stage_obj):
        super().__init__()
        self.stage = stage_obj
        self._is_running = True

    def run(self):
        try:
            self.status_update.emit("Homing...")
            if self.stage.home_device():
                
                while self.stage.is_moving() and self._is_running:
                    time.sleep(0.1) 
                if self._is_running:
                    self.finished.emit(True, "Homing complete.")
                else:
                    self.finished.emit(False, "Homing aborted by E-STOP.")
            else:
                self.finished.emit(False, "Homing failed: Device not connected.")
        except Exception as e:
            self.finished.emit(False, str(e))
            
    def request_stop(self):
        self._is_running = False

class MoveThread(QThread):
    """Background thread for moving the motor and updating UI."""
    finished = pyqtSignal(bool, str)
    pos_update = pyqtSignal(float) 

    def __init__(self, stage_obj, target_val, mode='abs'):
        super().__init__()
        self.stage = stage_obj
        self.target_val = target_val
        self.mode = mode
        self._is_running = True 

    def run(self):
        # 2. Print immediately upon entering the thread
        #print(f"[DEBUG-THREAD] Inside run(), commanding hardware to move to {self.target_pos} mm")
        
        try:
            if self.mode == 'abs':
                self.stage.move_to_position(self.target_val)
            elif self.mode == 'rel':
                self.stage.move_by_distance(self.target_val)

            # 4. Monitoring loop
            while self._is_running and self.stage.is_moving():
                current_pos = self.stage.get_position()
                self.pos_update.emit(current_pos) 
                time.sleep(0.05) 

            # 5. Loop finished, read the final position
            #print("[DEBUG-THREAD] Motor stopped moving. Reading final position...")
            final_pos = self.stage.get_position()
            self.pos_update.emit(final_pos)

            if self._is_running:
                self.finished.emit(True, "Reached target.")
            else:
                self.finished.emit(False, "Aborted by E-STOP.")

        except Exception as e:
            # 6. Catch any silent crash and send it back to the main GUI
            #print(f"[DEBUG-THREAD] CRASH DETECTED: {e}")
            self.finished.emit(False, str(e))

    def request_stop(self):
        """Sets the flag to break the monitoring loop safely."""
        self._is_running = False