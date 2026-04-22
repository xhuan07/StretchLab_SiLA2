# -*- coding: utf-8 -*-
"""
Created on Sat Feb 21 15:13:07 2026

@author: xhuan
"""

from pylablib.devices import Thorlabs
import time

# 1. Define your KDC101 serial number (must be a string)
# Replace this with the actual serial number printed on your device
serial_number = "27001592" 

try:
    # 2. Connect to the motor controller
    print(f"Connecting to KDC101 (SN: {serial_number})...")
    motor = Thorlabs.KinesisMotor(serial_number)
    print("Connection successful!")

    # 3. Homing (Calibration)
    # Homing is crucial. It drives the motor to a physical limit switch to establish the "Zero" position.
    # Without homing, absolute positioning will be inaccurate.
    print("Homing the motor... Please wait.")
    motor.home()
    motor.wait_move()  # Block the script until the motor physically stops
    print("Homing complete. Current position is 0.")

    # 4. Move to an Absolute Position
    # The default unit is usually millimeters (mm) or degrees, depending on the attached stage.
    target_pos = 5.0  
    print(f"Moving to absolute position: {target_pos} units...")
    motor.move_to(target_pos)
    motor.wait_move()
    print(f"Arrived. Current position: {motor.get_position()}")

    # Pause for 2 seconds to observe the motor
    time.sleep(2)

    # 5. Move by a Relative Distance (Step movement)
    step_distance = -2.5
    print(f"Moving relatively by: {step_distance} units...")
    motor.move_by(step_distance)
    motor.wait_move()
    print(f"Arrived. Final position: {motor.get_position()}")

except Exception as e:
    # Catch and print any errors (e.g., wrong serial number, USB disconnected)
    print(f"An error occurred: {e}")

finally:
    # 6. Disconnect Safely
    # This block always executes. Closing the connection releases the USB port.
    if 'motor' in locals():
        motor.close()
        print("Motor connection securely closed.")