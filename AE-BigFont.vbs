' 用大字体模式启动 After Effects（隐藏窗口）
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
dir = fso.GetParentFolderName(WScript.ScriptFullName)
sh.Run """C:\Python313\pythonw.exe"" """ & dir & "\ae_bigfont.py""", 0, False
