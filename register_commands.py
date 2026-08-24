import os
import sys

base_dir = os.path.dirname(os.path.abspath(__file__))
python_exe = sys.executable
main_py = os.path.join(base_dir, "main.py")
cmd_content = f'@echo off\r\n"{python_exe}" "{main_py}" %*\r\n'

local_app_data = os.environ.get("LOCALAPPDATA", "")
windows_apps_dir = os.path.join(local_app_data, "Microsoft", "WindowsApps") if local_app_data else None

if windows_apps_dir and os.path.exists(windows_apps_dir):
    for alias in ["agent.cmd", "desktop-agent.cmd", "agent.bat", "desktop-agent.bat"]:
        target_file = os.path.join(windows_apps_dir, alias)
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(cmd_content)
    print(f"Global 'agent' and 'desktop-agent' commands installed to: {windows_apps_dir}")

# Also create in local directory
for alias in ["agent.cmd", "desktop-agent.cmd", "agent.bat", "desktop-agent.bat"]:
    target_file = os.path.join(base_dir, alias)
    with open(target_file, "w", encoding="utf-8") as f:
        f.write(cmd_content)
print("Local command wrappers created.")
