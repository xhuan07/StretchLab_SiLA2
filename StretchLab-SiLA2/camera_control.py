# -*- coding: utf-8 -*-
"""
Unified Camera Control Layer
Supports both Allied Vision (Vimba) and DirectShow (OpenCV/Lumenera) cameras.
"""

import cv2
import numpy as np
import time
import config
from PyQt5.QtCore import QThread, pyqtSignal

# Safely attempt to import vmbpy. 
# This prevents crashes on computers that do not have Vimba drivers installed.
try:
    import vmbpy
    VIMBA_AVAILABLE = True
except ImportError:
    VIMBA_AVAILABLE = False
    print("[Warning] vmbpy not found. Allied Vision cameras will be disabled.")


class CameraController:
    """
    Hardware Control Layer.
    Manages connections and parameters for both Vimba and OpenCV cameras.
    """
    def __init__(self):
        self.camera = None 
        self.camera_type = None  # Will be set to 'VMB' or 'CV'
        self.vmb = None
        
        # Core defense mechanism: Start the Vimba engine upon initialization and keep it alive.
        # This prevents the race conditions triggered by __enter__ and __exit__ during GUI dialogs.
        if VIMBA_AVAILABLE:
            try:
                self.vmb = vmbpy.VmbSystem.get_instance()
                self.vmb.__enter__()
                print("[Control] Vimba System Engine started globally.")
            except Exception as e:
                print(f"[Control] Warning - Vimba Engine init failed: {e}")

    def get_available_cameras(self) -> dict:
        """
        Scans for all available cameras across all supported protocols.
        Returns a dictionary mapping internal unified IDs to display names.
        Example: {"CV_0": "DirectShow Camera (Index 0)", "VMB_DEV123": "Allied Vision (Mako)"}
        """
        cams_dict = {}

        # 1. Scan DirectShow (OpenCV) cameras
        for i in range(3):  # Probe the first 3 indices
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            if cap.isOpened():
                cams_dict[f"CV_{i}"] = f"DirectShow Camera (Index {i})"
                cap.release()

        # 2. Scan Vimba cameras
        if self.vmb:
            try:
                vmb_cams = self.vmb.get_all_cameras()
                for cam in vmb_cams:
                    if "Simulator" not in cam.get_model():
                        cam_id = cam.get_id()
                        cams_dict[f"VMB_{cam_id}"] = f"Allied Vision ({cam.get_model()})"
            except Exception as e:
                print(f"[Control] Vimba discovery error: {e}")

        return cams_dict

    def open_camera(self, unified_id: str):
        """
        Initializes and opens the camera based on the unified ID prefix.
        """
        self.close_camera()  # Ensure any existing connection is safely closed

        if not unified_id:
            return None

        try:
            # ==========================================
            # DirectShow (OpenCV) Initialization
            # ==========================================
            if unified_id.startswith("CV_"):
                index = int(unified_id.split("_")[1])
                self.camera = cv2.VideoCapture(index, cv2.CAP_DSHOW)
                
                if self.camera.isOpened():
                    # Set standard high resolution (adjust to match your INFINITY1 model)
                    self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                    self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 1024)
                    
                    # 0.25 is the flag to disable auto-exposure in DirectShow
                    self.camera.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25) 
                    self.camera_type = 'CV'
                    
                    print(f"[Control] OpenCV Camera {index} opened successfully.")
                    return self.camera

            # ==========================================
            # Vimba (Allied Vision) Initialization
            # ==========================================
            elif unified_id.startswith("VMB_") and self.vmb:
                real_vmb_id = unified_id.split("_", 1)[1]
                cam = self.vmb.get_camera_by_id(real_vmb_id)
                cam.__enter__() 
                self.camera = cam
                self.camera_type = 'VMB'
                
                # Jumbo frame network optimization for GigE cameras
                try:
                    stream = self.camera.get_streams()[0]
                    stream.get_feature_by_name('GVSPPacketSize').set(config.GEV_PACKET_SIZE)
                except Exception as net_e:
                    print(f"[Control] Network optimization skipped: {net_e}")
                
                # Disable auto features for manual control
                self.camera.get_feature_by_name('ExposureAuto').set('Off')
                self.camera.get_feature_by_name('GainAuto').set('Off')
                
                print(f"[Control] Vimba Camera {real_vmb_id} opened successfully.")
                return self.camera

        except Exception as e:
            print(f"[Control] Error opening camera {unified_id}: {e}")
            self.close_camera()
            
        return None

    def close_camera(self):
        """ 
        Safely releases the active camera. 
        Crucially, keeps the VmbSystem alive if it's running.
        """
        try:
            if self.camera_type == 'CV' and self.camera:
                self.camera.release()
                
            elif self.camera_type == 'VMB' and self.camera:
                self.camera.__exit__(None, None, None)
                
            self.camera = None
            self.camera_type = None
            print("[Control] Camera hardware released (Engine still running).")
        except Exception as e:
            print(f"[Control] Error during close: {e}")

    def set_exposure(self, value):
        if not self.camera: 
            return
        try:
            if self.camera_type == 'CV':
                # DirectShow uses a logarithmic scale for exposure (e.g., -5)
                self.camera.set(cv2.CAP_PROP_EXPOSURE, float(value))
            elif self.camera_type == 'VMB':
                # Vimba uses microseconds (e.g., 10000)
                self.camera.get_feature_by_name(config.FEAT_EXPOSURE).set(float(value))
        except Exception as e:
            print(f"[Control] Exposure error: {e}")

    def set_gain(self, value):
        if not self.camera: 
            return
        try:
            if self.camera_type == 'CV':
                self.camera.set(cv2.CAP_PROP_GAIN, float(value))
            elif self.camera_type == 'VMB':
                self.camera.get_feature_by_name(config.FEAT_GAIN).set(float(value))
        except Exception as e:
            print(f"[Control] Gain error: {e}")


class CameraThread(QThread):
    """ 
    Standard Acquisition Engine for the background thread.
    Routes data acquisition based on the active hardware protocol.
    """
    frame_ready = pyqtSignal(np.ndarray)
    error_occurred = pyqtSignal(str)

    def __init__(self, controller: CameraController):
        super().__init__()
        self.controller = controller 
        self._is_running = False

    def run(self):
        self._is_running = True
        try:
            if not self.controller.camera:
                return

            if self.controller.camera_type == 'VMB':
                self._run_vimba_acquisition()
            elif self.controller.camera_type == 'CV':
                self._run_opencv_acquisition()
                
        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            self._is_running = False

    def _run_vimba_acquisition(self):
        """ Uses the optimized Vimba frame generator """
        generator = self.controller.camera.get_frame_generator(limit=None, timeout_ms=2000)
        for frame in generator:
            if not self._is_running:
                break
                
            # 0 corresponds to FrameStatus.Complete
            if frame.get_status() == 0: 
                frame.convert_pixel_format(vmbpy.PixelFormat.Mono8)
                # Always emit a copy to prevent memory corruption in the UI thread
                self.frame_ready.emit(frame.as_opencv_image().copy())

    def _run_opencv_acquisition(self):
        """ Uses a standard while loop for DirectShow hardware buffers """
        while self._is_running:
            ret, frame = self.controller.camera.read()
            if ret:
                # Convert standard BGR output to Mono8 to match Vimba's format
                gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                self.frame_ready.emit(gray_frame.copy())
            else:
                # Short sleep to prevent CPU hogging if a frame is dropped
                time.sleep(0.01) 

    def stop(self):
        """ Safely stops the thread loop. """
        self._is_running = False
        self.wait()