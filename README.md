# AE BigFont — 放大 After Effects 界面字体

After Effects 从来不给 UI 字号设置，中文版默认还是宋体 9–12px，2K/4K 屏上看着很吃力。
配套的字体替换（宋体 → 微软雅黑）见 [adobe-no-simsun](https://github.com/scrpr/adobe-no-simsun)，两者可叠加。

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

### 配合「宋体 → 微软雅黑」

字号放大解决的是「小」，字形本身还是宋体的话，2K 屏上笔画偏细。AE 的 UI 字体名是**硬编码在 `dvaui.dll` 里**的，没有设置项，但可以打一个 38 字节的补丁换成系统里已有的字体。

工具：[adobe-no-simsun](https://github.com/scrpr/adobe-no-simsun)

```bat
:: 换成微软雅黑（先关掉 After Effects）
python adobe_no_simsun.py --product after-effects --font "Microsoft YaHei UI"

:: 想还原
python adobe_no_simsun.py --product after-effects --restore "<dvaui.dll.bak.no_simsun_xxx 的完整路径>"
```

它的做法是在 `dvaui.dll` 里模式匹配字体初始化点（`mov r8d,6` + `lea rdx,"SimSun"`），把指针重定向到 .text 尾部空白处写入的新字体名，并改长度立即数。不写死地址，所以小版本升级后通常还能用。

本机实测环境（After Effects 2025 / `dvaui.dll` 25.2.2.2，31,062,472 字节）：

- 整份 DLL 里 `SimSun\0` 只出现 1 次（RVA `0x7dcdf4`），候选初始化点唯一
- 总共改 38 字节，文件大小不变，不加节，导入表 / 重定位 / 入口点都不动
- 打完补丁 `objdump -p` 能正常解析，AE 启动无崩溃；原文件备份成 `dvaui.dll.bak.no_simsun_<时间戳>`

**注意不要走另一条路**：改 `Support Files\Dictionaries\zh_CN\after_effects_zh_CN.dat` 里的 `FontStyle/*` 换字体名。那个目录是签名过的 UCF 包（`mimetype` + `META-INF/signatures.xml`），内容改一个字节、甚至只在目录里多放一个文件，`ZXPSign_verify` 就返回 `50`，AE 判定语言包不可用 → 语言回退英文 → 中文订阅授权不匹配 → 启动直接弹 `Licensing Error`，进不去。这条弯路我在同一个 25.2.2 上踩实了。

两者可以叠加：`dvaui.dll` 负责换字形，本工具负责放大字号，互不干扰。

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
