# AE BigFont — 放大 After Effects 界面字体

After Effects 从来不给 UI 字号设置，中文版默认还是宋体 9–12px，2K/4K 屏上看着很吃力。
这个工具用 **Frida 运行时 hook** 把 AE 界面所有文字的渲染字号按倍数放大，**不修改任何 Adobe 文件**，也不会破坏语言包签名。

```
DirectWrite CreateTextFormat: 12.0 -> 15.0 (x1.25)
```

## 为什么不用改文件

- **改 `Dictionaries\zh_CN\after_effects_zh_CN.dat`**：这个目录是一个签过名的 UCF 包（`mimetype` + `META-INF/signatures.xml`，RSA-SHA1）。改任何一个字节、甚至只在目录里多放一个文件，`ZXPSign_verify` 就返回 `50`（失败），AE 判定语言包不可用 → 回退英文 → 中文订阅授权不匹配 → 启动直接弹 `Licensing Error`（错误码 0x13），进不去。
- **`AdobeCleanFontSize`（Debug Database）**：25.x 里它只影响行距/内边距，不改字形大小，改了等于没改。
- **本方案**：语言包原封不动，只在内存里把 `IDWriteFactory::CreateTextFormat` 的字号参数乘一个系数。AE 的 UI 文字由 DirectWrite 渲染，所以全部生效。

## 依赖

- Windows + After Effects（2023–2026 实测同一条路径，2025 25.2.2 验证）
- Python 3.9+
- `pip install frida`

## 使用

1. 把 4 个文件放到同一个目录，比如 `D:\ae-bigfont\`
2. 装依赖：`C:\Python313\python.exe -m pip install frida`
3. **先把 After Effects 完全退出**
4. 双击 `AE-BigFont.vbs`

启动器会自己找 `Program Files\Adobe\Adobe After Effects *\Support Files\AfterFX.exe`，挂上 hook 后再拉起 AE。
想从命令行用：

```bat
python ae_bigfont.py            :: 用 factor.txt 里的倍数
python ae_bigfont.py 1.4        :: 临时指定倍数
python ae_bigfont.py --exe "D:\Adobe\Adobe After Effects 2025\Support Files\AfterFX.exe"
```

### 倍数怎么选

| 倍数 | 效果 |
|---|---|
| 1.0 | 原样 |
| 1.15 – 1.3 | 舒服，布局不挤，**推荐 1.25** |
| 1.4 | 已经能看出面板标签变挤 |
| ≥1.5 | 面板标签开始重叠，不建议 |

倍数写在 `factor.txt` 里（一行，比如 `1.25`），改完重启 AE 生效。hook 只在启动那一刻写进字号，运行中改没用。

### 做桌面快捷方式

```powershell
$ws = New-Object -ComObject WScript.Shell
$lnk = $ws.CreateShortcut("$env:USERPROFILE\Desktop\AE 大字体.lnk")
$lnk.TargetPath = "C:\Windows\System32\wscript.exe"
$lnk.Arguments = '"D:\ae-bigfont\AE-BigFont.vbs"'
$lnk.IconLocation = "C:\Program Files\Adobe\Adobe After Effects 2025\Support Files\AfterFX.exe,0"
$lnk.Save()
```

### 换字体（可选）

字号解决了，字体本身也换掉的话，用 [adobe-no-simsun](https://github.com/scrpr/adobe-no-simsun) 把 `dvaui.dll` 里的 `SimSun` 改成 `Microsoft YaHei UI`，两者互不冲突。

## 已知限制

- **顶部菜单栏**（`文件(F) 编辑(E) …`）是 Windows 原生菜单，不走 DirectWrite，这个 hook 管不到；它的字号只跟系统缩放走。
- 文字放大但面板的固定宽度不跟着变，所以倍数太大会挤。想要整体等比放大，用 Windows 显示缩放（125%/150%）更干净。
- 依赖 Python 环境；`pip` 坏掉或换解释器路径（VBS 里写死了 `C:\Python313\pythonw.exe`）就启动不了。
- 只在 Windows 上做了，macOS 需要换成 CoreText 的 hook。

## 原理备忘

`IDWriteFactory` vtable 第 15 项是 `CreateTextFormat`：

```
HRESULT CreateTextFormat(
    WCHAR const* familyName, IDWriteFontCollection*, DWRITE_FONT_WEIGHT,
    DWRITE_FONT_STYLE, DWRITE_FONT_STRETCH, FLOAT fontSize, WCHAR const* locale,
    IDWriteTextFormat**);
```

x64 上前 4 个参数在寄存器（rcx/rdx/r8/r9），第 7 个 `fontSize` 落在栈上，位置是 `rsp+0x38`（call 压入返回地址 + 0x20 影子空间）。hook 里直接改这个 float 即可。

拿 factory 指针的办法：hook `dwrite.dll!DWriteCreateFactory` 的 `onLeave`，读第 4 个参数（out 指针），再拿它的 vtable。

## License

MIT
