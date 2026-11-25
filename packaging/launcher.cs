using System;
using System.IO;
using System.Diagnostics;
using System.Windows.Forms;

namespace LopixAI
{
    static class Program
    {
        [STAThread]
        static void Main()
        {
            try
            {
                string baseDir = AppDomain.CurrentDomain.BaseDirectory;
                Directory.SetCurrentDirectory(baseDir);

                string mainScript = Path.Combine(baseDir, "main.py");
                if (!File.Exists(mainScript))
                {
                    MessageBox.Show(
                        "main.py dosyası bulunamadı!\nKonum: " + baseDir,
                        "LopixAI - Başlatma Hatası",
                        MessageBoxButtons.OK,
                        MessageBoxIcon.Error
                    );
                    return;
                }

                string pythonPath = FindPythonw();
                if (string.IsNullOrEmpty(pythonPath))
                {
                    MessageBox.Show(
                        "Sisteminizde Python bulunamadı!\nLütfen Python kurun veya PATH ortam değişkenine ekleyin.",
                        "LopixAI - Python Bulunamadı",
                        MessageBoxButtons.OK,
                        MessageBoxIcon.Warning
                    );
                    return;
                }

                ProcessStartInfo psi = new ProcessStartInfo
                {
                    FileName = pythonPath,
                    Arguments = "\"" + mainScript + "\"",
                    WorkingDirectory = baseDir,
                    UseShellExecute = false,
                    CreateNoWindow = true,
                    WindowStyle = ProcessWindowStyle.Hidden
                };

                Process.Start(psi);
            }
            catch (Exception ex)
            {
                MessageBox.Show(
                    "LopixAI başlatılırken beklenmeyen bir hata oluştu:\n" + ex.Message,
                    "LopixAI - Hata",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Error
                );
            }
        }

        static string FindPythonw()
        {
            // 1. Bilinen doğrudan pythonw yolları
            string[] knownPaths = new string[]
            {
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), @"Python\pythoncore-3.14-64\pythonw.exe"),
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), @"Programs\Python\Python314\pythonw.exe"),
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), @"Programs\Python\Python313\pythonw.exe"),
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), @"Programs\Python\Python312\pythonw.exe"),
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), @"Programs\Python\Python311\pythonw.exe"),
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), @"Programs\Python\Python310\pythonw.exe"),
                @"C:\Python314\pythonw.exe",
                @"C:\Python313\pythonw.exe",
                @"C:\Python312\pythonw.exe",
                @"C:\Python311\pythonw.exe"
            };

            foreach (string p in knownPaths)
            {
                if (File.Exists(p)) return p;
            }

            // 2. PATH içinde pythonw ara
            string pathEnv = Environment.GetEnvironmentVariable("PATH") ?? "";
            string[] dirs = pathEnv.Split(';');
            foreach (string dir in dirs)
            {
                string trimmed = dir.Trim().Trim('"');
                if (string.IsNullOrEmpty(trimmed)) continue;
                string candidate = Path.Combine(trimmed, "pythonw.exe");
                if (File.Exists(candidate)) return candidate;
            }

            // 3. python.exe varsa onu kullan (CreateNoWindow=true olduğu için CMD açılmaz)
            foreach (string p in knownPaths)
            {
                string pNormal = p.Replace("pythonw.exe", "python.exe");
                if (File.Exists(pNormal)) return pNormal;
            }

            foreach (string dir in dirs)
            {
                string trimmed = dir.Trim().Trim('"');
                if (string.IsNullOrEmpty(trimmed)) continue;
                string candidate = Path.Combine(trimmed, "python.exe");
                if (File.Exists(candidate)) return candidate;
            }

            return null;
        }
    }
}
