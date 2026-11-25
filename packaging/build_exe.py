"""
LopixAI EXE Derleme Betiği
PyInstaller kullanarak LopixAI.exe oluşturur.
Kullanıcı sisteminde Python olmadan çalışabilen standalone dağıtım sağlar.
"""

import sys
import subprocess
from pathlib import Path

def build():
    pkg_dir = Path(__file__).resolve().parent
    spec_path = pkg_dir / "LopixAI.spec"
    
    print(f"[*] LopixAI PyInstaller derlemesi başlatılıyor: {spec_path}")
    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        str(spec_path)
    ]

    res = subprocess.run(cmd, cwd=str(pkg_dir.parent))
    if res.returncode == 0:
        print("[+] Derleme başarıyla tamamlandı! Çıktı: dist/LopixAI/LopixAI.exe")
    else:
        print(f"[-] Derleme hatası! Hata kodu: {res.returncode}")

if __name__ == "__main__":
    build()
