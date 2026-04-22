# -*- coding: utf-8 -*-
"""
Created on Sat Feb 21 16:09:38 2026

@author: xhuan
"""

# config.py

# ==========================================
# MOTOR HARDWARE CONFIGURATION
# ==========================================
SERIAL_NUMBER = "27001592" 
STAGE_MODEL = "MTS50-Z8"    

# Default velocity parameters (Units: mm/s)
DEFAULT_MAX_VELOCITY = 1.5  
DEFAULT_ACCELERATION = 1.5  
DEFAULT_VELOCITY = 0.500

# Safety limits
MAX_POSITION_MM = 50.0
MIN_POSITION_MM = 0.0

# ==========================================
# CAMERA HARDWARE CONFIGURATION
# ==========================================

# 1. Identity and Connection Settings
CAMERA_ID = "CV_0"
CAMERA_FPS = 30

# Optimization for Jumbo Frames. 
# 9000 is the standard for Gigabit Ethernet with Jumbo Frames enabled.
GEV_PACKET_SIZE = 9000 

# 2. Hardware GenICam Feature Names
# Based on your previous diagnostic results
FEAT_EXPOSURE = "ExposureTimeAbs"  
FEAT_GAIN = "Gain"               

# 3. Default Values
DEFAULT_EXPOSURE_US = 10000.0 
DEFAULT_GAIN_DB = 0.0

# 4. Hardware Ranges (For GUI Slider limits)
EXP_RANGE = (12.0, 1000000.0) 
GAIN_RANGE = (0.0, 24.0)