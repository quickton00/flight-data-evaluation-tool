"""
Global configuration module for the Flight Data Evaluation Tool.

This module contains global variables and paths used throughout the application,
including icon paths for different execution environments (PyInstaller vs development)
and authentication-related variables.

:var icon_path: Path to the application icon file, adjusted based on execution environment.
:vartype icon_path: str
:var password: SHA-256 hash of the password for unlocking grading functionality.
:vartype password: str
:var grading_unlocked: Flag indicating whether grading features have been unlocked.
:vartype grading_unlocked: bool
"""

import sys
import os

if getattr(sys, "frozen", False):
    icon_path = sys._MEIPASS  # Check if running in a PyInstaller bundle
    icon_path = os.path.join(icon_path, "icon.ico")
else:
    icon_path = r"src\flight_data_evaluation_tool\icon.ico"

password = "e2f1be635b488b29721fb33157b33f3762433a8b7db220fa8db9750749c53c03"
grading_unlocked = False
