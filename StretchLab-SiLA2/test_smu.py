# -*- coding: utf-8 -*-
"""
Created on Tue Mar 10 16:14:51 2026

@author: xhuan
"""

from smu_control import SMUController
import time

print("Starting Keithley 2450 test sequence...")
smu = SMUController()

# 1. Test the physical connection
success, msg = smu.connect()
print(f"Connection Status: {success} -> {msg}")

if success:
    # 2. Configure for resistance measurement mode (suitable for flexible sensors)
    print("Configuring resistance measurement mode...")
    smu.setup_measure_resistance()
    
    # 3. Turn on the output
    smu.output_on()
    print("Output turned ON. Starting 5 continuous readings:")
    
    # 4. Continuous reading test loop
    for i in range(5):
        val = smu.read_value()
        print(f"Reading {i+1}: {val:.6e} Ohms")
        time.sleep(0.5)
        
    # 5. Safe shutdown sequence
    smu.output_off()
    smu.disconnect()
    print("Test completed. Device successfully disconnected.")