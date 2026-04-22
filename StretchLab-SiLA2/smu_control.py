# -*- coding: utf-8 -*-
"""
Created on Tue Mar 10 16:03:41 2026

@author: xhuan
"""

# -*- coding: utf-8 -*-
"""
Hardware abstraction layer for Keithley 2450 SourceMeter.
Requires: pyvisa (pip install pyvisa)
"""

import pyvisa
import time

class SMUController:
    def __init__(self, resource_name=None):
        """
        Initializes the SMU controller.
        If resource_name is not provided, connect() will attempt to 
        auto-detect the first available instrument.
        """
        self.rm = pyvisa.ResourceManager()
        self.resource_name = resource_name
        self.smu = None

    def connect(self):
        """
        Connects to the Keithley 2450 and performs an initialization reset.
        """
        try:
            # If no address is specified, automatically find the first available USB/GPIB/LAN instrument
            if not self.resource_name:
                resources = self.rm.list_resources()
                if not resources:
                    return False, "No VISA instruments found."
                self.resource_name = resources[0]

            print(f"[SMU] Attempting to connect to {self.resource_name}...")
            self.smu = self.rm.open_resource(self.resource_name)
            
            # Set timeout (in milliseconds) to prevent freezing during high-impedance measurements
            self.smu.timeout = 5000 
            
            # Handshake validation: Query the instrument model
            idn = self.smu.query("*IDN?")
            if "2450" not in idn and "KEITHLEY" not in idn:
                self.disconnect()
                return False, f"Connected device is not a recognized Keithley SMU: {idn}"

            # Initialization: Restore factory defaults and clear the error queue
            self.smu.write("*RST")
            time.sleep(0.5) # Give the instrument a short delay to process
            
            return True, f"Connected to {idn.strip()}"

        except Exception as e:
            return False, f"SMU Connection Error: {str(e)}"

    def disconnect(self):
        """ Safely disconnects the instrument and ensures the output is turned off. """
        if self.smu:
            try:
                # Always turn off the output before disconnecting to protect the sample
                self.output_off() 
                self.smu.close()
                print(f"[SMU] Disconnected from {self.resource_name}.")
            except:
                pass
            finally:
                self.smu = None

    # ==========================================
    # Core Configuration Commands (SCPI)
    # ==========================================
    def setup_voltage_source_measure_current(self, voltage_level=1.0, current_limit=0.01):
        """
        Most common mode: Source constant voltage, measure current.
        :param voltage_level: Sourced voltage level (V)
        :param current_limit: Current compliance/limit (A), default is 10mA
        """
        if not self.smu: return False
        
        try:
            self.smu.write(":SOUR:FUNC VOLT")                 # Set source mode to voltage
            self.smu.write(f":SOUR:VOLT {voltage_level}")     # Set the voltage level
            self.smu.write(f":SOUR:VOLT:ILIM {current_limit}")# Set the current compliance limit
            
            self.smu.write(":SENS:FUNC 'CURR'")               # Set measurement function to current
            self.smu.write(":SENS:CURR:RSEN OFF")             # Turn off 4-wire sense (defaults to 2-wire)
            return True
        except Exception as e:
            print(f"[SMU Error] Setup failed: {e}")
            return False

    def setup_measure_resistance(self):
        """
        Pure resistance measurement mode (e.g., for strain gauges, flexible sensors).
        The 2450 will automatically source a small test current to calculate resistance.
        """
        if not self.smu: return False
        try:
            self.smu.write(":SENS:FUNC 'RES'")  # Set measurement function to resistance
            self.smu.write(":SENS:RES:OCOM ON") # Enable offset compensation (improves accuracy for low resistance)
            return True
        except Exception as e:
            print(f"[SMU Error] Resistance setup failed: {e}")
            return False

    def output_on(self):
        """ Turns on the output (OUTPUT indicator on the front panel will light up). """
        if self.smu:
            self.smu.write(":OUTP ON")

    def output_off(self):
        """ Turns off the output (OUTPUT indicator on the front panel will turn off). """
        if self.smu:
            self.smu.write(":OUTP OFF")

    # ==========================================
    # Data Acquisition Commands
    # ==========================================
    def read_value(self):
        """
        Triggers a single measurement and reads the result.
        Returns a float (Current in Amps or Resistance in Ohms, depending on the setup).
        """
        if not self.smu: return 0.0
        try:
            # :READ? triggers a completely new measurement and returns the data
            raw_data = self.smu.query(":READ?")
            # The 2450 typically returns a scientific notation string, e.g., "+1.034E-03"
            return float(raw_data)
        except Exception as e:
            print(f"[SMU Error] Read failed: {e}")
            return 0.0