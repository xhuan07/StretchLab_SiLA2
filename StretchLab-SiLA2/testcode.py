# verify_connection.py
# Code comments must be in English, body in Chinese.
import sys
import config
from camera_control import CameraController

def test_hardware_pipeline():
    print("--- Step 1: Initializing Controller (Starting Vimba Engine) ---")
    try:
        ctrl = CameraController()
    except Exception as e:
        print(f"[ERROR] Failed to init CameraController: {e}")
        sys.exit(1)

    print("--- Step 2: Detecting Camera ID ---")
    cam_id = ctrl.get_auto_detected_id()
    
    if not cam_id:
        print("[Warning] Auto-detect failed. Falling back to config.py ID...")
        cam_id = getattr(config, 'CAMERA_ID', None)
        
    if not cam_id:
        print("[ERROR] No Camera ID found in detection or config. Exiting.")
        sys.exit(1)
        
    print(f"    -> Target ID: {cam_id}")

    print("--- Step 3: Opening Camera Hardware ---")
    cam = ctrl.open_camera(cam_id)
    if not cam:
        print("[ERROR] Failed to open camera.")
        print("    -> If you see '<VmbError.InternalFault: -1>', the camera is still in a zombie state.")
        print("    -> Solution: Unplug camera power/ethernet cable, wait 5 seconds, replug.")
        sys.exit(1)
    
    print("    -> Camera opened successfully!")

    print("--- Step 4: Grabbing a Test Frame ---")
    try:
        # Request exactly 1 frame with a 3-second timeout
        generator = cam.get_frame_generator(limit=1, timeout_ms=3000)
        for frame in generator:
            if frame.get_status() == 0: # FrameStatus.Complete
                print("    -> [SUCCESS] Frame acquired! Pipeline is 100% operational.")
            else:
                print(f"    -> [ERROR] Frame incomplete. Status: {frame.get_status()}")
            break # Exit after one frame
    except Exception as e:
        print(f"    -> [ERROR] Frame grab failed: {e}")

    print("--- Step 5: Cleaning up ---")
    ctrl.close_camera()
    print("--- TEST FINISHED ---")

if __name__ == "__main__":
    test_hardware_pipeline()