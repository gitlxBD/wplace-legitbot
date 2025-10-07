import os
import sys

def check():
    try:

        is_android = os.path.exists('/system/bin/app_process') or os.path.exists('/system/bin/app_process32')
        if is_android:
            return 0
        else:
            return 1
    except Exception as e:
        return f"Error: {e}"

device = check()
mode = 1

package_termux = [
    'pkg update -y && pkg upgrade -y',
    'pkg install -y git',
    'pkg install -y python',
    'pkg install -y python3',
    'pkg install -y clang make openssl-dev libffi-dev'
]

package_linux = [
    'apt-get update -y && apt-get upgrade -y',
    'apt-get install -y python3 python3-pip',
    'apt-get install -y git build-essential libssl-dev libffi-dev libx11-6 libx11-dev',
    'apt-get install -y python3-dev'
]
na_support = [
    'pyautogui',
    'keyboard',
    'mss'
]
modules = [
    'pyautogui',
    'keyboard',
    'opencv-python',
    'numpy',
    'mss'
]

def detect_os():
    if os.path.exists("/data/data/com.termux/files/usr/bin/bash"):
        return 1
    else:
        return 0

def up_package():
    os_type = detect_os()
    if os_type == 1:
        print("Detected Termux environment")
        for command in package_termux:
            print(f"Executing: {command}")
            os.system(command)
    else:
        print("Detected Linux environment")
        for command in package_linux:
            print(f"Executing: {command}")
            os.system(command)

def pip_install(module_name, break_sys=False):
    global mode
    if mode == 1:
        cmd = f"python3 -m pip install {module_name}"
    else:
        cmd = f"python -m pip install {module_name}"
    if break_sys:
        cmd += " --break-system-packages"

    print(f"Installing {module_name} {'(force)' if break_sys else ''} ...")
    result = os.system(cmd)

    if result != 0 and not break_sys:
        print(f"[!] Retrying {module_name} with --break-system-packages...")
        return pip_install(module_name, break_sys=True)
    return result

def install_modules():
    print('='*4 + ' Installing Python modules ' + '='*4)
    failed_modules = []

    for mod in modules:
        try:
            if mod in na_support and device == 0:
                print(f"[!] Skipped module: {mod} (Not supported on this device)")
                continue

            result = pip_install(mod)
            if result != 0:
                failed_modules.append(mod)
            else:
                print(f"[+] {mod} installed successfully.")

        except Exception as e:
            print(f"[!] Module {mod} cannot be installed: {e}")
            failed_modules.append(mod)

    if failed_modules:
        print(f"[!] Failed to install: {', '.join(failed_modules)}")
        print("[!] You may need to install these manually.")
        print("[!] Tips:")
        print("    - On Debian/Ubuntu: sudo apt-get install -y libx11-dev libgl1-mesa-dev libpng-dev")
        print("    - 'keyboard' may require root privileges to capture key events")
        print("    - 'pyautogui' may require an active X server (won’t work on headless servers)")
        if device == 0:
            print("    - On Android/Termux, GUI and keyboard libraries are not supported.")

def main():
    global mode
    print('='*4 + ' WPlace-LegitBot Installer ' + '='*4)

    print('='*4 + ' Updating system packages ' + '='*4)
    choice = input('[~] Update system packages? Y/N: '
                   ).strip().lower()
    if choice in ['y', 'yes']:
        up_package()
    else:
        print("[+] Skipping package update...")

    print("[+] Choose your Python version: python3 or python")
    pys = input('python3/python: ').strip().lower()
    mode = 1 if pys == 'python3' else 0

    print("[+] Installing required modules for wplace-legitbot.py ...")
    install_modules()

    print('='*4 + ' Launching wplace-legitbot.py ' + '='*4)
    target_script = 'wplace-legitbot.py'
    if os.path.exists(target_script):
        if mode == 1:
            cmd = f"python3 {target_script}"
        else:
            cmd = f"python {target_script}"
        print(f"[+] Executing: {cmd}")
        os.system(cmd)
    else:
        print(f"[!] {target_script} not found. Please place it in this directory first.")

if __name__ == "__main__":
    main()
