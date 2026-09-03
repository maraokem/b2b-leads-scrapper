import platform
import subprocess
import hashlib
import os


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

MID = get_machine_id()
FINGERPRINT = get_fingerprint()
if __name__ == "__main__":
    print("OS:", platform.system())
    print("Machine ID:", MID)
    print("Fingerprint:", FINGERPRINT)