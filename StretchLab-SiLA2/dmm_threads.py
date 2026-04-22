# -*- coding: utf-8 -*-
"""
Created on Tue Mar 31 15:12:44 2026
@author: xhuan
"""
"""
Background worker thread for continuously polling the Keysight 34465A DMM.
Requires PyQt5.
"""
from PyQt5.QtCore import QThread, pyqtSignal
import time

class DMMThread(QThread):
    data_ready = pyqtSignal(float)
    error_occurred = pyqtSignal(str)

    def __init__(self, dmm_controller):
        super().__init__()
        self.dmm = dmm_controller
        self._is_running = False
        self._paused = False

    def pause(self):
        
        self._paused = True

    def resume(self):
        
        self._paused = False

    # def run(self):
    #     self._is_running = True
    #     while self._is_running:
    #         try:
    #             if not self._paused:
    #                 val = self.dmm.read_value()
    #                 self.data_ready.emit(val)
    #             time.sleep(0.2)
    #         except Exception as e:
    #             self.error_occurred.emit(f"DMM Polling Error: {str(e)}")
    #             self._is_running = False
    #             break

    def stop(self):
        self._is_running = False
        self.wait()
    
    def run(self):
        self._is_running = True
        try:
            for val in self.dmm.subscribe_resistance():
                if not self._is_running:
                    break
                if not self._paused:
                    self.data_ready.emit(float(val))
        except Exception as e:
            self.error_occurred.emit(f"DMM Error: {str(e)}")

    def _on_value(self, value):
        if self._is_running and not self._paused:
            self.data_ready.emit(float(value)) 

