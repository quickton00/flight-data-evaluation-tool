import sys
import os

if getattr(sys, "frozen", False):
    icon_path = sys._MEIPASS  # Check if running in a PyInstaller bundle
    icon_path = os.path.join(icon_path, "icon.ico")
else:
    icon_path = r"src\flight_data_evaluation_tool\icon.ico"

password = "e2f1be635b488b29721fb33157b33f3762433a8b7db220fa8db9750749c53c03"
grading_unlocked = False
