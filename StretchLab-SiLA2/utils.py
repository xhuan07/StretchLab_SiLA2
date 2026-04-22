# -*- coding: utf-8 -*-
"""
Created on Sat Feb 21 16:16:29 2026

@author: xhuan
"""

import json
import os
import config

SETTINGS_FILE = "settings.json"

def load_settings():
    
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                if "SERIAL_NUMBER" in data: config.SERIAL_NUMBER = data["SERIAL_NUMBER"]
                if "STAGE_MODEL" in data: config.STAGE_MODEL = data["STAGE_MODEL"]
                if "DEFAULT_VELOCITY" in data: config.DEFAULT_VELOCITY = data["DEFAULT_VELOCITY"]
                if "CAMERA_ID" in data: config.CAMERA_ID = data["CAMERA_ID"]
            print("[Utils] User settings loaded successfully.")
        except Exception as e:
            print(f"[Error] Failed to load settings: {e}")

def save_settings():
    
    data = {
        "SERIAL_NUMBER": getattr(config, 'SERIAL_NUMBER', ""),
        "STAGE_MODEL": getattr(config, 'STAGE_MODEL', ""),
        "DEFAULT_VELOCITY": getattr(config, 'DEFAULT_VELOCITY', 0.5),
        "CAMERA_ID": getattr(config, 'CAMERA_ID', "")
    }
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"[Error] Failed to save settings: {e}")

def update_config_file(new_serial_number, new_model, new_velocity=None):
    
    config.SERIAL_NUMBER = new_serial_number
    config.STAGE_MODEL = new_model
    if new_velocity is not None:
        config.DEFAULT_VELOCITY = new_velocity
    save_settings()
    print(f"[Utils] Configuration updated: SN={new_serial_number}, Model={new_model}, Velocity={new_velocity}")

def update_camera_config(new_camera_id):
    
    config.CAMERA_ID = new_camera_id
    save_settings()
    print(f"[Utils] Camera config updated: ID={new_camera_id}")