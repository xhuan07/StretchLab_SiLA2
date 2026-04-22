# -*- coding: utf-8 -*-
"""
Created on Tue Mar 10 16:15:34 2026

@author: xhuan
"""

# -*- coding: utf-8 -*-
"""
Background worker thread for continuously polling the Keithley 2450.
"""
from PyQt5.QtCore import QThread, pyqtSignal
import time

class SMUThread(QThread):
    # Signal to send the float value to the GUI safely
    data_ready = pyqtSignal(float)
    error_occurred = pyqtSignal(str)

    def __init__(self, smu_controller):
        super().__init__()
        self.smu = smu_controller
        self._is_running = False

    def run(self):
        self._is_running = True
        while self._is_running:
            try:
                # Trigger measurement and read
                val = self.smu.read_value()
                self.data_ready.emit(val)
                
                # Sleep to prevent overloading the SMU and CPU (update ~5 times a second)
                time.sleep(0.2) 
            except Exception as e:
                self.error_occurred.emit(f"SMU Polling Error: {str(e)}")
                self._is_running = False
                break

    def stop(self):
        """ Safely stops the polling loop. """
        self._is_running = False
        self.wait()