# -*- coding: utf-8 -*-
"""
Created on Sun Apr 12 16:32:47 2026

@author: xhuan
"""

# scan_logger.py
import csv
import os
from datetime import datetime

def append_scan_log(csv_path: str, position: float, resistance_raw: float,
                    resistance_str: str, image_filename: str):
    """将一条扫描记录追加写入 CSV 文件"""
    file_exists = os.path.exists(csv_path)
    try:
        with open(csv_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["Timestamp", "Position_mm", "Resistance_raw_Ohm",
                                  "Resistance_display", "Image_file"])
            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                f"{position:.4f}",
                f"{resistance_raw:.6e}",
                resistance_str,
                image_filename
            ])
    except Exception as e:
        print(f"[Logger Error] Failed to write scan log: {e}")