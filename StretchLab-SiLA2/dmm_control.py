# -*- coding: utf-8 -*-
"""
DMM control via SiLA 2 client.
Drop-in replacement for the original dmm_control.py.
All method signatures are identical so dmm_threads.py and GUI need no changes.
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
SILA_HOST = _config.get("dmm_host", "192.168.10.2")
SILA_PORT = _config.get("dmm_port", 50053)

class DMMController:
    def __init__(self, resource_name=None):
        self.resource_name = resource_name
        self.client = None
        self.dmm = None  # GUI checks `if self.dmm_controller.dmm is not None`

    def connect(self):
        """Connect to the SiLA DMM server on the Raspberry Pi."""
        try:
            self.client = SilaClient(SILA_HOST, SILA_PORT, insecure=True)
            self.dmm = True  # 连接成功才设为 True
            return True, "Connected to Keysight 34465A via SiLA"
        except Exception as e:
            self.dmm = None
            self.client = None
            return False, str(e)

    def disconnect(self):
        """Disconnect from the SiLA server."""
        if self.client is not None:
            self.client = None
            self.dmm = None
            print("[DMM Client] Disconnected from SiLA server.")

    def setup_measure_resistance(self):
        """Configure DMM to measure resistance via SiLA."""
        if self.client:
            try:
                self.client.DMMController.SetModeResistance()
                return True
            except Exception as e:
                print(f"[DMM Error] SetModeResistance failed: {e}")
        return False

    def setup_measure_dc_voltage(self):
        """Configure DMM to measure DC voltage via SiLA."""
        if self.client:
            try:
                self.client.DMMController.SetModeDcVoltage()
                return True
            except Exception as e:
                print(f"[DMM Error] SetModeDcVoltage failed: {e}")
        return False

    def setup_measure_dc_current(self):
        """Configure DMM to measure DC current via SiLA."""
        if self.client:
            try:
                self.client.DMMController.SetModeDcCurrent()
                return True
            except Exception as e:
                print(f"[DMM Error] SetModeDcCurrent failed: {e}")
        return False

    def read_value(self) -> float:
        """Get a single measurement reading via SiLA."""
        if self.client:
            try:
                return self.client.DMMController.Reading.get()
            except Exception as e:
                print(f"[DMM Error] Read failed: {e}")
        return 0.0

    def format_resistance(self, value: float) -> str:
        """Format resistance value for display."""
        if value >= 9.0e37:
            return "OL"
        elif value >= 1e6:
            return f"{value/1e6:.4f} MΩ"
        elif value >= 1e3:
            return f"{value/1e3:.4f} kΩ"
        else:
            return f"{value:.4f} Ω"

    def read_single_blocking(self, dmm_thread=None) -> tuple:
        """Read a single value, pausing the polling thread if needed."""
        if dmm_thread and dmm_thread.isRunning():
            dmm_thread.pause()

        raw = self.read_value()
        display = self.format_resistance(raw)

        if dmm_thread and dmm_thread.isRunning():
            dmm_thread.resume()

        return raw, display
    def subscribe_resistance(self):
        """返回一个可迭代的订阅流"""
        if self.client:
            return self.client.DMMController.Resistance.subscribe()
        return iter([])