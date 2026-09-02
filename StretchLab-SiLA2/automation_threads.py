# -*- coding: utf-8 -*-
"""
automation_threads.py  (two-motor version)

Step-and-Shoot retreat scan. Both motors start from their current positions
and retreat toward 0. Each step shortens the system by 'step_size', achieved
by each motor moving step_size/2. Sequence per step: Move both -> Settle ->
Capture -> Repeat, until the cumulative shortening reaches the input distance.
"""

import time
import os
from PyQt5.QtCore import QThread, pyqtSignal
from threading import Event


class AutomationThread(QThread):
    progress_update = pyqtSignal(int, str)      # (percent 0-100, status text)
    capture_requested = pyqtSignal(str, float)  # (filepath, cumulative displacement mm)
    finished = pyqtSignal(bool, str)            # (success, final message)

    def __init__(self, stage1, stage2, params):
        super().__init__()
        self.stage1 = stage1
        self.stage2 = stage2
        self.params = params
        self._is_running = False
        self.capture_done_event = Event()

    def run(self):
        self._is_running = True
        distance = abs(self.params['distance'])     # total system shortening (mm)
        step_val = abs(self.params['step_size'])    # system shortening per step (mm)
        delay = self.params['settle_time']
        prefix = self.params['prefix']
        directory = self.params['directory']

        try:
            # Read each motor's current position as its own starting point
            start1 = self.stage1.get_position()
            start2 = self.stage2.get_position()

            # Cumulative shortening targets: 0, step, 2*step, ..., distance
            cumulative = [0.0]
            c = step_val
            while c < distance - 1e-9:
                cumulative.append(c)
                c += step_val
            cumulative.append(distance)   # exact end (handles remainder)

            total_steps = len(cumulative)

            for i, cum in enumerate(cumulative):
                if not self._is_running:
                    self.finished.emit(False, "Scan aborted by user.")
                    return

                percent = int((i / (total_steps - 1)) * 100) if total_steps > 1 else 100

                # Each motor retreats half of the cumulative shortening
                half = cum / 2.0
                target1 = start1 - half
                target2 = start2 - half

                # --- STEP A: move both motors ---
                self.progress_update.emit(percent, f"Retreating {cum:.3f} mm total...")
                self.stage1.move_to_position(target1)
                self.stage2.move_to_position(target2)

                # Poll both until each reaches its target (5 um tolerance)
                while self._is_running:
                    p1 = self.stage1.get_position()
                    p2 = self.stage2.get_position()
                    if abs(p1 - target1) < 0.005 and abs(p2 - target2) < 0.005:
                        break
                    time.sleep(0.05)

                if not self._is_running:
                    self.finished.emit(False, "Scan aborted during motor movement.")
                    return

                # --- STEP B: settle ---
                self.progress_update.emit(percent, f"Settling ({cum:.3f} mm) for {delay}s...")
                elapsed = 0.0
                while elapsed < delay:
                    if not self._is_running:
                        self.finished.emit(False, "Scan aborted during settling.")
                        return
                    time.sleep(0.1)
                    elapsed += 0.1

                # --- STEP C: capture (blocks until GUI signals done) ---
                self.progress_update.emit(percent, f"Capturing image {i + 1}/{total_steps}...")
                filename = f"{prefix}_disp_{cum:.3f}mm.tiff"
                filepath = os.path.join(directory, filename)
                self.capture_done_event.clear()
                self.capture_requested.emit(filepath, cum)
                self.capture_done_event.wait(timeout=5.0)

            if self._is_running:
                self.progress_update.emit(100, "Scan completed successfully!")
                self.finished.emit(True, "Automation sequence finished.")

        except Exception as e:
            self.finished.emit(False, f"Hardware Error during scan: {str(e)}")
        finally:
            self._is_running = False

    def stop(self):
        """Gracefully interrupt and halt both motors."""
        self._is_running = False
        self.capture_done_event.set()
        for st in (getattr(self, 'stage1', None), getattr(self, 'stage2', None)):
            try:
                if st is not None:
                    st.stop_immediate()
            except Exception:
                pass
