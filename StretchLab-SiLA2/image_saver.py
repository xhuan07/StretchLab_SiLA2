# -*- coding: utf-8 -*-
"""
Created on Sun Apr 12 16:43:19 2026

@author: xhuan
"""

import cv2

def save_frame(file_path: str, frame) -> bool:
    try:
        cv2.imwrite(file_path, frame)
        print(f"[ImageSaver] Saved: {file_path}")
        return True
    except Exception as e:
        print(f"[ImageSaver Error] {e}")
        return False