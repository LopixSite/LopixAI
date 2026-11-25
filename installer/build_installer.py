"""
LopixAI Setup Paketleyici (Product Rule #16)
PyInstaller kullanarak installer/setup_gui.py dosyasını
LopixAI-Setup.exe olarak derler.
"""

import sys
import subprocess
from pathlib import Path

def build_setup():
    installer_dir = Path(__file__).resolve().parent
    setup_gui_path = installer_dir / "setup_gui.py"
    output_dir = installer_dir.parent / "dist"

    print("==================================================")
    print("   ✦ LopixAI-Setup.exe Derleme Süreci")
    print("==================================================")
    print(f"[*] Kaynak: {setup_gui_path}")
    print(f"[*] Çıktı Dizini: {output_dir}")

    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--onefile",
        "--noconfirm",
        "--clean",
        "--windowed",
        f"--name=LopixAI-Setup",
        f"--distpath={output_dir}",
        str(setup_gui_path)
    ]

    print("[*] PyInstaller komutu çalıştırılıyor...")
    res = subprocess.run(cmd, cwd=str(installer_dir.parent))
    if res.returncode == 0:
        setup_exe = output_dir / "LopixAI-Setup.exe"
        print(f"\n[✓] Kurulum dosyası başarıyla üretildi!")
        print(f"[✓] Konum: {setup_exe}")
    else:
        print(f"\n[-] Derleme başarısız oldu! Çıkış kodu: {res.returncode}")

if __name__ == "__main__":
    build_setup()
