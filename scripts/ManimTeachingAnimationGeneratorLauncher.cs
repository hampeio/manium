using System;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;

internal static class ManimTeachingAnimationGeneratorLauncher
{
    [STAThread]
    private static void Main()
    {
        string projectRoot = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),
            "Documents",
            "manium"
        );
        string launcher = Path.Combine(projectRoot, "scripts", "desktop_launcher.ps1");

        if (!File.Exists(launcher))
        {
            MessageBox.Show("Cannot find launcher script:\n" + launcher, "Manim 教学动画生成器");
            return;
        }

        var info = new ProcessStartInfo
        {
            FileName = "powershell.exe",
            Arguments = "-NoProfile -ExecutionPolicy Bypass -File \"" + launcher + "\"",
            WorkingDirectory = projectRoot,
            UseShellExecute = true
        };
        Process.Start(info);
    }
}
