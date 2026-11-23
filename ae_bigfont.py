#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""After Effects 界面字体放大启动器

用 Frida 在运行时 hook DirectWrite 的 CreateTextFormat，把所有 UI 字号乘以一个系数。
不修改任何 Adobe 文件，不碰语言包签名，所以不会触发 "Licensing Error"。

用法:
    python ae_bigfont.py                # 用 factor.txt 里的系数（默认 1.25）
    python ae_bigfont.py 1.4            # 指定系数
    python ae_bigfont.py --exe "D:\\...\\AfterFX.exe"
"""
import argparse
import glob
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
JS_PATH = os.path.join(HERE, 'ae_bigfont.js')
FACTOR_FILE = os.path.join(HERE, 'factor.txt')


def log_to(path=None):
    if not path:
        return lambda s: None
    f = open(path, 'w', encoding='utf-8')
    def w(s):
        f.write(str(s) + '\n')
        f.flush()
    return w


def detect_exe():
    pats = []
    for root in (r'C:\Program Files\Adobe', r'C:\Program Files (x86)\Adobe', r'D:\Program Files\Adobe'):
        pats += glob.glob(os.path.join(root, 'Adobe After Effects *', 'Support Files', 'AfterFX.exe'))
    pats.sort()
    return pats[-1] if pats else None


def ae_running():
    try:
        out = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq AfterFX.exe', '/FO', 'CSV', '/NH'],
                             capture_output=True, text=True, errors='ignore').stdout
        return 'AfterFX.exe' in out
    except Exception:
        return False


def read_factor():
    try:
        with open(FACTOR_FILE, encoding='utf-8') as f:
            return float(f.read().strip().splitlines()[0])
    except Exception:
        return 1.25


def main():
    ap = argparse.ArgumentParser(description='AE 界面字体放大启动器')
    ap.add_argument('factor', nargs='?', type=float, default=None, help='放大系数，默认读 factor.txt，再默认 1.25')
    ap.add_argument('--exe', default=None, help='AfterFX.exe 完整路径（默认自动查找）')
    ap.add_argument('--log', default=None, help='把运行日志写到指定文件')
    args = ap.parse_args()

    factor = args.factor if args.factor else read_factor()
    if not 1.0 <= factor <= 3.0:
        print('系数应在 1.0 ~ 3.0 之间，收到 %s' % factor)
        return 2

    exe = args.exe or detect_exe()
    if not exe or not os.path.exists(exe):
        print('找不到 AfterFX.exe，请用 --exe 指定')
        return 2

    if ae_running():
        print('After Effects 正在运行，请先完全退出再启动')
        return 3

    try:
        import frida
    except ImportError:
        print('缺少依赖 frida：C:\\Python313\\python.exe -m pip install frida')
        return 4

    w = log_to(args.log)
    with open(JS_PATH, encoding='utf-8') as f:
        js = f.read().replace('__FACTOR__', str(factor))

    def on_msg(m, data):
        p = m.get('payload', m)
        if isinstance(p, str) and p.startswith('CTF'):
            return
        w(p)

    dev = frida.get_local_device()
    pid = dev.spawn([exe])
    w('spawned pid=%d factor=%s' % (pid, factor))
    sess = dev.attach(pid)
    sess.on('detached', lambda *a: w('detached %r' % (a,)))
    script = sess.create_script(js)
    script.on('message', on_msg)
    script.load()
    dev.resume(pid)
    print('已启动 After Effects（字体 x%.2f），pid=%d' % (factor, pid))
    w('resumed')
    try:
        while True:
            time.sleep(2)
            try:
                if not any(p.pid == pid for p in dev.enumerate_processes()):
                    break
            except Exception:
                time.sleep(1)
    except KeyboardInterrupt:
        pass
    w('exit')
    return 0


if __name__ == '__main__':
    sys.exit(main())
