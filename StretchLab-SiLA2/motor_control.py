# -*- coding: utf-8 -*-
"""
Motor control via SiLA 2 client.
Drop-in replacement for the original motor_control.py.
All method signatures are identical so motor_threads.py and GUI need no changes.
"""

import json
import os
import sys
from sila2.client import SilaClient

def _get_config_path():
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(__file__)
    return os.path.join(base, 'sila_config.json')

def _load_config():
    try:
        with open(_get_config_path(), 'r') as f:
            return json.load(f)
    except:
        return {}

_config = _load_config()
SILA_HOST = _config.get("motor_host", "192.168.10.2")
SILA_PORT = _config.get("motor_port", 50052)

class StageController:
    def __init__(self, serial_number, host=SILA_HOST, port=SILA_PORT):
        self.sn = serial_number
        self.host = host
        self.port = port
        self.client = None

    def connect(self, stage_model="MTS50-Z8"):
        """Connect to the SiLA server on the Raspberry Pi."""
        try:
            self.client = SilaClient(self.host, self.port, insecure=True)
            print(f"[Client] Connected to SiLA server at {self.host}:{self.port}")
            return True, f"Connected to {stage_model} via SiLA"
        except Exception as e:
            return False, str(e)

    def disconnect(self):
        """Close the SiLA client connection."""
        if self.client is not None:
            try:
                self.client = None
                print("[Client] Disconnected from SiLA server.")
            except:
                pass

    def home_device(self):
        """Run homing sequence via SiLA."""
        if self.client:
            try:
                self.client.MotorController.Home()
                return True
            except Exception as e:
                print(f"[Error] Home failed: {e}")
        return False

    def is_moving(self):
        """
        SiLA commands are blocking, so by the time they return the motor has stopped.
        Always returns False so motor_threads.py polling loop exits immediately.
        """
        return False

    def move_to_position(self, target_mm):
        """Move to absolute position in mm via SiLA (blocking)."""
        if self.client:
            try:
                self.client.MotorController.MoveToPosition(TargetPosition=target_mm)
            except Exception as e:
                print(f"[Error] MoveToPosition failed: {e}")

    def move_by_distance(self, distance_mm):
        """Move by relative distance in mm via SiLA (blocking)."""
        if self.client:
            try:
                self.client.MotorController.MoveByDistance(Distance=distance_mm)
            except Exception as e:
                print(f"[Error] MoveByDistance failed: {e}")

    def get_position(self) -> float:
        if self.client:
          try:
              return self.client.MotorController.CurrentPosition.get()
          except Exception as e:
            print(f"[Error] GetPosition failed: {e}")
        return 0.0

    def stop_immediate(self):
        """Emergency stop via SiLA."""
        if self.client:
            try:
                self.client.MotorController.Stop()
                print("[Client] Emergency stop sent.")
            except Exception as e:
                print(f"[Error] Stop failed: {e}")

    def set_velocity(self, speed_mms):
        """Set velocity in mm/s via SiLA."""
        if self.client:
            try:
                self.client.VelocityControl.SetVelocity(Velocity=speed_mms)
                print(f"[Client] Velocity set to {speed_mms} mm/s")
                return True
            except Exception as e:
                print(f"[Error] SetVelocity failed: {e}")
                return False
        return False

    def get_current_velocity(self) -> float:
        if self.client:
            try:
                   return self.client.VelocityControl.CurrentVelocity.get()
            except Exception as e:
                    print(f"[Error] GetVelocity failed: {e}")
        return 0.0