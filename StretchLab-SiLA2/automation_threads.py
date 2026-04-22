# -*- coding: utf-8 -*-
"""
Created on Tue Feb 24 13:48:22 2026

@author: xhuan
"""

# automation_threads.py
import time
import os
from PyQt5.QtCore import QThread, pyqtSignal
from threading import Event

class AutomationThread(QThread):
    """
    Background worker for the Step-and-Shoot automated strain mapping.
    Handles the sequence: Move -> Settle -> Request Camera Frame -> Repeat.
    """
    # Signals to communicate with the GUI safely
    progress_update = pyqtSignal(int, str)  # (Percentage 0-100, Status Text)
    capture_requested = pyqtSignal(str)     # (Full file path to save)
    finished = pyqtSignal(bool, str)        # (Success boolean, Final message)

    def __init__(self, stage, params):
        super().__init__()
        self.stage = stage
        self.params = params
        self._is_running = False
        # Event to synchronize with GUI's image saving speed
        self.capture_done_event = Event()

    def run(self):
        self._is_running = True
        start = self.params['start_pos']
        end = self.params['end_pos']
        step_val = self.params['step_size']
        delay = self.params['settle_time']
        prefix = self.params['prefix']
        directory = self.params['directory']

        # 1. Calculate trajectory (handles both stretching and compressing)
        direction = 1 if end > start else -1
        actual_step = abs(step_val) * direction
        
        # Generate target positions
        steps_count = int(abs(end - start) / abs(actual_step)) + 1
        positions = [start + i * actual_step for i in range(steps_count)]
        
        # Ensure the exact end position is reached despite floating point errors
        if abs(positions[-1] - end) > 1e-4:
            positions.append(end)

        total_steps = len(positions)

        # 2. Execute the Step-and-Shoot loop
        try:
            for i, pos in enumerate(positions):
                if not self._is_running:
                    self.finished.emit(False, "Scan aborted by user.")
                    return

                # Calculate percentage so the final step gracefully rests at 100%
                if total_steps > 1:
                    percent = int((i / (total_steps - 1)) * 100)
                else:
                    percent = 100

                # --- STEP A: Move Motor ---
                self.progress_update.emit(percent, f"Moving to {pos:.3f} mm...")
                self.stage.move_to_position(pos)
                
                # Robust polling to ensure motor physically reached the target
                while self._is_running:
                    curr_pos = self.stage.get_position()
                    if abs(curr_pos - pos) < 0.005: # Tolerance of 5um
                        break
                    time.sleep(0.05)

                if not self._is_running: 
                    self.finished.emit(False, "Scan aborted during motor movement.")
                    return

                # --- STEP B: Settle Delay ---
                self.progress_update.emit(percent, f"Settling at {pos:.3f} mm for {delay}s...")
                # Sleep in small 0.1s chunks so the Abort button stays responsive
                elapsed = 0.0
                while elapsed < delay:
                    if not self._is_running:
                        self.finished.emit(False, "Scan aborted during settling.")
                        return
                    time.sleep(0.1)
                    elapsed += 0.1

                # --- STEP C: Request Image Capture ---
                self.progress_update.emit(percent, f"Capturing image {i+1}/{total_steps}...")
                filename = f"{prefix}_pos_{pos:.3f}mm.tiff"
                filepath = os.path.join(directory, filename)

                # Clear the event flag and tell GUI to save the frame
                self.capture_done_event.clear()
                self.capture_requested.emit(filepath)

                # Block this thread until the GUI signals that saving is complete (Max 5s timeout)
                self.capture_done_event.wait(timeout=5.0)

            # Sequence complete
            if self._is_running:
                self.progress_update.emit(100, "Scan completed successfully!")
                self.finished.emit(True, "Automation sequence finished.")

        except Exception as e:
            self.finished.emit(False, f"Hardware Error during scan: {str(e)}")
        finally:
            self._is_running = False

    def stop(self):
        """ Gracefully interrupts the running sequence. """
        self._is_running = False
        # Unblock the thread immediately if it was waiting for the camera
        self.capture_done_event.set()
        
        # Send emergency stop to motor to halt any active movement
        try:
            self.stage.stop_immediate()
        except:
            pass