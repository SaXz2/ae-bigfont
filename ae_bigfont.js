// 把所有 DirectWrite 文字格式的字号乘以 FACTOR。
// 只影响渲染，不改任何磁盘文件。
const FACTOR = __FACTOR__;
const hooked = new Set();
let logged = 0;

function hookFactory(factory) {
  try {
    const vt = factory.readPointer();
    const fn = vt.add(15 * 8).readPointer();      // IDWriteFactory::CreateTextFormat
    const key = fn.toString();
    if (hooked.has(key)) return;
    hooked.add(key);
    Interceptor.attach(fn, {
      onEnter(args) {
        try {
          const slot = this.context.rsp.add(0x38);  // 第 7 个参数 fontSize: FLOAT
          const size = slot.readFloat();
          if (size > 0 && size < 200) {
            slot.writeFloat(size * FACTOR);
            if (logged < 8) {
              logged++;
              send('CTF size ' + size.toFixed(1) + ' -> ' + (size * FACTOR).toFixed(1));
            }
          }
        } catch (e) {}
      }
    });
  } catch (e) {}
}

Process.attachModuleObserver({
  onAdded(m) {
    if (!/^dwrite\.dll$/i.test(m.name)) return;
    try {
      const exp = m.enumerateExports().filter(e => String(e.name) === 'DWriteCreateFactory')[0];
      if (!exp) return;
      Interceptor.attach(exp.address, {
        onEnter(args) { this.out = args[3]; },
        onLeave() {
          try {
            const p = this.out.readPointer();
            if (!p.isNull()) hookFactory(p);
          } catch (e) {}
        }
      });
      send('dwrite hooked');
    } catch (e) {}
  }
});
