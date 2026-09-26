import platform
import subprocess
import hashlib
import os


# Global reference to the caffeinate process on macOS
caffeinate_process = None

def get_machine_id():
    system = platform.system()

    if system == "Windows":
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Cryptography"
        )

        value, _ = winreg.QueryValueEx(key, "MachineGuid")
        return value

    elif system == "Darwin":
        output = subprocess.check_output(
            [
                "ioreg",
                "-rd1",
                "-c",
                "IOPlatformExpertDevice"
            ],
            text=True
        )

        for line in output.splitlines():
            if "IOPlatformUUID" in line:
                return line.split("=")[1].strip().strip('"')

        raise RuntimeError("Could not find IOPlatformUUID")

    elif system == "Linux":
        for path in [
            "/etc/machine-id",
            "/var/lib/dbus/machine-id"
        ]:
            if os.path.exists(path):
                with open(path, "r") as f:
                    return f.read().strip()

        raise RuntimeError("Could not find Linux machine ID")

    else:
        raise RuntimeError(f"Unsupported operating system: {system}")


def get_fingerprint():
    machine_id = get_machine_id()

    return hashlib.sha256(
        machine_id.encode("utf-8")
    ).hexdigest()

# Functions to keep the system awake
def keep_system_awake():
    global caffeinate_process

    system = platform.system()

    if system == "Windows":
        import ctypes

        ES_CONTINUOUS = 0x80000000
        ES_SYSTEM_REQUIRED = 0x00000001

        ctypes.windll.kernel32.SetThreadExecutionState(
            ES_CONTINUOUS | ES_SYSTEM_REQUIRED
        )

        print("✓ System sleep disabled.")

    elif system == "Darwin":
        # Keep Mac awake while this process is running
        caffeinate_process = subprocess.Popen(
            ["caffeinate", "-dims"]
        )

        print("✓ System sleep disabled.")

    elif system == "Linux":
        try:
            subprocess.run(
                ["xset", "s", "off"],
                check=True
            )

            subprocess.run(
                ["xset", "-dpms"],
                check=True
            )

            print("✓ System sleep disabled.")

        except (FileNotFoundError, subprocess.CalledProcessError):
            print("⚠ Could not configure Linux sleep prevention.")

    else:
        print(
            f"⚠ Unsupported operating system: {system}"
        )



# Function to restore the system's sleep settings after keeping it awake
def exit_system_awake():
    global caffeinate_process

    system = platform.system()

    if system == "Windows":
        import ctypes

        ES_CONTINUOUS = 0x80000000

        ctypes.windll.kernel32.SetThreadExecutionState(
            ES_CONTINUOUS
        )

        print("✓ System sleep restored.")

    elif system == "Darwin":
        if caffeinate_process is not None:
            caffeinate_process.terminate()
            caffeinate_process.wait()
            caffeinate_process = None

        print("✓ System sleep restored.")

    elif system == "Linux":
        try:
            subprocess.run(
                ["xset", "s", "on"],
                check=True
            )

            subprocess.run(
                ["xset", "+dpms"],
                check=True
            )

            print("✓ System sleep restored.")

        except (FileNotFoundError, subprocess.CalledProcessError):
            print("⚠ Could not restore Linux sleep settings.")

    else:
        print(
            f"⚠ Unsupported operating system: {system}"
        )



MID = get_machine_id()
FINGERPRINT = get_fingerprint()
if __name__ == "__main__":
    print("OS:", platform.system())
    print("Machine ID:", MID)
    print("Fingerprint:", FINGERPRINT)