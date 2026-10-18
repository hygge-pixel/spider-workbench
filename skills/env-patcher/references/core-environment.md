# Browser Environment Core

浏览器 API、指纹、VM、SDK/WASM 加载和失败诊断的通用材料。具体厂商差异读取 sdks 目录。

## Contents

- 一、补环境最小依赖清单
- Level 1: 基础环境（按实际缺失补齐，已有能力不重复模拟）
- Level 2: 增强环境（风控严格的站点）
- Level 3: SDK专用（按需加载的完整模板）
- 二、Function.prototype.toString 修复
- 三、指纹注入模板
- 四、VM 沙箱创建模板
- 五、SDK加载器模板
- WASM 桥接模板（京东jcap/字节rmc-captcha/阿里Baxia专用）
- 六、Python 桥接模板
- 七、对抗深度增强
- 7.1 WebGL 状态机深度模拟
- 7.2 Canvas 渲染哈希稳定性
- 7.3 requestAnimationFrame 时序检测对抗
- 7.4 CSSOM 属性枚举检测对抗
- 失败模式编码
- SDK检测到非浏览器：系统性排查清单
- 反模式黑名单

## 一、补环境最小依赖清单

### Level 1: 基础环境（按实际缺失补齐，已有能力不重复模拟）

```javascript
// === 全局对象 ===
globalThis.window = globalThis;
globalThis.self = globalThis;
globalThis.top = globalThis;
globalThis.parent = globalThis;
globalThis.frames = globalThis;

// === document ===
const doc = {
  createElement: (tag) => ({
    tagName: tag.toUpperCase(),
    style: {},
    children: [],
    appendChild: () => {},
    removeChild: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    getAttribute: () => null,
    setAttribute: () => {},
    getBoundingClientRect: () => ({ top: 0, left: 0, width: 100, height: 100 }),
    getElementsByTagName: () => [],
    querySelectorAll: () => [],
    querySelector: () => null,
    innerHTML: '', innerText: '', textContent: '',
    offsetWidth: 100, offsetHeight: 100,
    classList: { add: () => {}, remove: () => {}, contains: () => false },
  }),
  getElementById: () => null,
  querySelector: () => null,
  querySelectorAll: () => [],
  documentElement: { style: {}, clientWidth: 1920, clientHeight: 1080 },
  body: { appendChild: () => {}, removeChild: () => {} },
  cookie: '',
  readyState: 'complete',
  title: '',
  referrer: '',
  domain: '',
  URL: 'https://www.example.com/',
  addEventListener: () => {},
  removeEventListener: () => {},
  createEvent: () => ({ initEvent: () => {} }),
  head: {},
};
globalThis.document = doc;

// === navigator ===
globalThis.navigator = {
  userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
  platform: 'Win32',
  language: 'zh-CN',
  languages: ['zh-CN', 'zh', 'en'],
  vendor: 'Google Inc.',
  appVersion: '5.0 (Windows NT 10.0; Win64; x64)',
  appName: 'Netscape',
  product: 'Gecko',
  productSub: '20030107',
  cookieEnabled: true,
  onLine: true,
  hardwareConcurrency: 8,
  deviceMemory: 8,
  maxTouchPoints: 0,
  plugins: { length: 0 },
  mimeTypes: { length: 0 },
  connection: { effectiveType: '4g', downlink: 10, rtt: 50 },
  // Chrome 90+
  userAgentData: {
    brands: [{ brand: 'Chromium', version: '136' }, { brand: 'Google Chrome', version: '136' }],
    mobile: false,
    platform: 'Windows',
  },
};

// === screen ===
globalThis.screen = { width: 1920, height: 1080, availWidth: 1920, availHeight: 1040, colorDepth: 24, pixelDepth: 24 };

// === location ===
globalThis.location = { href: 'https://www.example.com/', hostname: 'www.example.com', protocol: 'https:', pathname: '/', search: '', hash: '' };

// === 性能API ===
const startTime = Date.now();
globalThis.performance = {
  now: () => Date.now() - startTime + Math.random() * 0.1,
  timing: { navigationStart: startTime },
  getEntriesByType: () => [],
  getEntriesByName: () => [],
  mark: () => {},
  measure: () => {},
};

// === 存储API ===
const storage = {
  _data: {},
  getItem(k) { return this._data[k] || null; },
  setItem(k, v) { this._data[k] = String(v); },
  removeItem(k) { delete this._data[k]; },
  clear() { this._data = {}; },
  get length() { return Object.keys(this._data).length; },
  key(i) { return Object.keys(this._data)[i] || null; },
};
globalThis.localStorage = storage;
globalThis.sessionStorage = { ...storage, _data: {} };

// === 编码API ===
globalThis.atob = (s) => Buffer.from(s, 'base64').toString('binary');
globalThis.btoa = (s) => Buffer.from(s, 'binary').toString('base64');

// === 定时器 ===
globalThis.setTimeout = (fn, ms) => setTimeout(fn, Math.min(ms || 0, 100));
globalThis.setInterval = (fn, ms) => setInterval(fn, Math.min(ms || 0, 100));
globalThis.clearTimeout = clearTimeout;
globalThis.clearInterval = clearInterval;
globalThis.requestAnimationFrame = (fn) => setTimeout(fn, 16);
```

### Level 2: 增强环境（风控严格的站点）

```javascript
// === Canvas 2D ===
class MockCanvas2D {
  constructor() {
    this.fillStyle = '#000000';
    this.font = '10px sans-serif';
    this.textBaseline = 'alphabetic';
    this.globalCompositeOperation = 'source-over';
    this.canvas = { width: 300, height: 150 };
    // ... 其他属性和 no-op 方法
  }
  fillRect() {}
  fillText() {}
  measureText() { return { width: 10 }; }
  getImageData() { return { data: new Uint8ClampedArray(400) }; }
  putImageData() {}
  toDataURL() { return 'data:image/png;base64,iVBOR...'; }
  arc() {} beginPath() {} closePath() {} lineTo() {} moveTo() {}
  stroke() {} fill() {} save() {} restore() {} translate() {}
  rect() {} clip() {} drawImage() {} createLinearGradient() { return { addColorStop: () => {} }; }
}

// === WebGL ===
class MockWebGL {
  getParameter(p) {
    const params = {
      37445: 'Google Inc. (NVIDIA)',           // UNMASKED_VENDOR
      37446: 'ANGLE (NVIDIA, GeForce GTX 1060, OpenGL 4.5)', // UNMASKED_RENDERER
      7937: 'WebKit WebGL',                     // RENDERER
      7936: 'WebKit',                           // VENDOR
      7938: 'WebGL 1.0 (OpenGL ES 2.0 Chromium)', // VERSION
    };
    return params[p] || null;
  }
  getExtension(name) {
    if (name === 'WEBGL_debug_renderer_info') return { UNMASKED_VENDOR_WEBGL: 37445, UNMASKED_RENDERER_WEBGL: 37446 };
    return null;
  }
  getSupportedExtensions() {
    return ['ANGLE_instanced_arrays', 'EXT_blend_minmax', 'WEBGL_debug_renderer_info'];
  }
  createBuffer() { return {}; }
  bindBuffer() {}
  bufferData() {}
  // ... 其他 no-op 方法
}

// === AudioContext ===
globalThis.AudioContext = class {
  createOscillator() { return { connect: () => {}, start: () => {}, stop: () => {}, frequency: { value: 0 } }; }
  createDynamicsCompressor() { return { connect: () => {}, threshold: { value: 0 }, knee: { value: 0 } }; }
  createAnalyser() { return { connect: () => {}, getFloatFrequencyData: () => {} }; }
  createGain() { return { connect: () => {}, gain: { value: 0 } }; }
  get destination() { return {}; }
  close() {}
};
globalThis.OfflineAudioContext = class extends globalThis.AudioContext {
  startRendering() { return Promise.resolve({ getChannelData: () => new Float32Array(0) }); }
};

// === EventTarget ===
class MockEventTarget {
  constructor() { this._listeners = {}; }
  addEventListener(type, fn) { (this._listeners[type] = this._listeners[type] || []).push(fn); }
  removeEventListener(type, fn) { if (this._listeners[type]) this._listeners[type] = this._listeners[type].filter(f => f !== fn); }
  dispatchEvent(event) { (this._listeners[event.type] || []).forEach(fn => fn(event)); return true; }
}

// === 其他增强API ===
globalThis.MutationObserver = class { constructor() {} observe() {} disconnect() {} };
globalThis.IntersectionObserver = class { constructor() {} observe() {} disconnect() {} };
globalThis.matchMedia = () => ({ matches: false, addListener: () => {}, removeListener: () => {} });
globalThis.speechSynthesis = { getVoices: () => [] };
globalThis.Notification = { permission: 'default' };
```

### Level 3: SDK专用（按需加载的完整模板）

|-----|-----------|---------|---------|

---

## 二、Function.prototype.toString 修复

```javascript
// 所有 mock 函数必须通过 native code 检测
const nativeFunctions = [
  'createElement', 'getElementById', 'querySelector',
  'addEventListener', 'removeEventListener', 'dispatchEvent',
  'getContext', 'toDataURL', 'getParameter', 'getExtension',
  'getItem', 'setItem', 'removeItem',
  // ... 所有 mock 的函数
];

nativeFunctions.forEach(name => {
  const orig = globalThis[name];
  if (orig) {
    orig.toString = () => `function ${name}() { [native code] }`;
  }
});

// 通用修复：让所有 Function 都看起来是 native
const origToString = Function.prototype.toString;
Function.prototype.toString = function() {
  if (this._nativeName) return `function ${this._nativeName}() { [native code] }`;
  return origToString.call(this);
};
```

---

## 三、指纹注入模板

```javascript
// 固定设备指纹（同一session内一致）
const FINGERPRINT = {
  canvas: 'data:image/png;base64,iVBORw0KGgo...',  // Canvas 2D指纹
  webgl_vendor: 'Google Inc. (NVIDIA)',
  webgl_renderer: 'ANGLE (NVIDIA, GeForce GTX 1060)',
  audio: '35.770000000000003',  // AudioContext指纹
  fonts: ['Arial', 'Times New Roman', 'Consolas'],
  screen: '1920x1080x24',
  timezone: -480,
  platform: 'Win32',
  plugins_count: 0,
  hardwareConcurrency: 8,
  deviceMemory: 8,
};

// 注入到 navigator/screen 等
Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => FINGERPRINT.hardwareConcurrency });
Object.defineProperty(navigator, 'deviceMemory', { get: () => FINGERPRINT.deviceMemory });
```

---

## 四、VM 沙箱创建模板

```javascript
const { VM } = require('vm2'); // 或 Node.js 内置 vm
const vm = require('vm');

function createSandbox() {
  const context = vm.createContext({
    // 注入 Level 1-3 环境
    ...require('./browser.js'),
    console,  // 保留console用于调试
    Buffer,
    process: { argv: [], env: {}, version: 'v20.0.0' },
    require,  // 如需限制require，使用自定义函数
  });
  return context;
}

function loadSDK(context, sdkCode) {
  try {
    const script = new vm.Script(sdkCode, { filename: 'sdk.js' });
    script.runInContext(context, { timeout: 10000 });
    return context;
  } catch (e) {
    console.error('SDK加载失败:', e.message);
    throw e;
  }
}
```

---

## 五、SDK加载器模板

```javascript
// 通用SDK加载器
function loadSDKAndGenerate(sdkPath, methodName, args) {
  const fs = require('fs');
  const vm = require('vm');

  // 1. 创建沙箱
  const context = createSandbox();

  // 2. 加载SDK
  const sdkCode = fs.readFileSync(sdkPath, 'utf-8');
  loadSDK(context, sdkCode);

  // 3. 调用方法
  const result = context[methodName](...args);

  // 4. 返回结果给Python（JSON序列化）
  return JSON.stringify(result);
}

// 从命令行调用
if (require.main === module) {
  const [,, sdkPath, method, ...restArgs] = process.argv;
  const args = JSON.parse(restArgs[0] || '[]');
  console.log(loadSDKAndGenerate(sdkPath, method, args));
}
```

### WASM 桥接模板（京东jcap/字节rmc-captcha/阿里Baxia专用）

```javascript
const fs = require('fs');
const path = require('path');

function setupWasmBridge(context, wasmPath) {
  // 1. 模拟WebAssembly全局对象
  context.WebAssembly = {
    instantiate: async (bufferSource, importObject) => {
      const wasmBuffer = fs.readFileSync(wasmPath);
      // 如果importObject中需要env函数，必须逐一提供
      const defaultImports = {
        env: {
          memory: new WebAssembly.Memory({ initial: 256, maximum: 256 }),
          table: new WebAssembly.Table({ initial: 0, element: 'anyfunc' }),
          // 常见WASM导入函数
          abort: () => { throw new Error('WASM abort'); },
          _abort: () => { throw new Error('WASM _abort'); },
          _grow: () => {},
          segfault: () => { throw new Error('WASM segfault'); },
          alignfault: () => { throw new Error('WASM alignfault'); },
          // 数学函数
          Math_sqrt: Math.sqrt,
          Math_abs: Math.abs,
          Math_floor: Math.floor,
          Math_ceil: Math.ceil,
          Math_min: Math.min,
          Math_max: Math.max,
          // 特定SDK函数（按需补充）
          ...importObject?.env || {},
        },
        wasi_snapshot_preview1: {
          fd_write: () => 0,
          proc_exit: () => {},
          random_get: (ptr, len) => {
            const mem = new Uint8Array(context.WebAssembly.instance.exports.memory.buffer);
            for (let i = 0; i < len; i++) mem[ptr + i] = Math.floor(Math.random() * 256);
            return 0;
          },
        },
      };

      const mergedImports = { ...defaultImports, ...importObject };
      const result = await WebAssembly.instantiate(wasmBuffer, mergedImports);
      context.WebAssembly.instance = result.instance;
      return result;
    },
    Instance: WebAssembly.Instance,
    Memory: WebAssembly.Memory,
    Table: WebAssembly.Table,
    instance: null, // 运行时填充
  };

  // 2. 模拟fetch加载WASM的路径
  context.fetch = async (url) => {
    if (url.endsWith('.wasm')) {
      const wasmBuffer = fs.readFileSync(path.resolve(wasmPath));
      return { arrayBuffer: () => Promise.resolve(wasmBuffer) };
    }
    return { text: () => Promise.resolve(''), json: () => Promise.resolve({}) };
  };
}
```

🔴 **CHECKPOINT**：WASM桥接完成后，必须验证 `WebAssembly.instance.exports` 包含SDK所需的导出函数名。常见导出函数：`__update_img`（Baxia）、`getCTData`（jcap）、`encrypt`（rmc-captcha）。

---

## 六、Python 桥接模板

```python
import subprocess, json

class NodeSigner:
    """Python调用Node.js签名器的桥接类"""

    def __init__(self, node_script: str, sdk_path: str):
        self.node_script = node_script
        self.sdk_path = sdk_path

    def call(self, method: str, args: list = None) -> dict:
        """调用Node.js方法"""
        cmd = ['node', self.node_script, self.sdk_path, method, json.dumps(args or [])]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise RuntimeError(f"Node.js错误: {result.stderr}")
        return json.loads(result.stdout)
```

---

## 七、对抗深度增强

> 补环境不仅是 API 模拟，还必须对抗 SDK 的多层级检测。以下是高级对抗策略。

### 7.1 WebGL 状态机深度模拟

```javascript
// SDK 检测 WebGL 状态一致性：bindTexture → texParameter → drawArrays 调用链
// 简单 stub 会导致状态检查失败
class MockWebGLStateMachine {
    constructor() {
        this._textures = new Map();
        this._buffers = new Map();
        this._programs = new Map();
        this._currentTexture = null;
        this._currentProgram = null;
        this._viewport = { x: 0, y: 0, w: 300, h: 150 };
        this._error = 0;  // gl.NO_ERROR
    }

    createTexture() { const id = { _id: Math.random() }; this._textures.set(id, {}); return id; }
    bindTexture(target, texture) { this._currentTexture = texture; }
    texParameteri(target, pname, param) { /* 记录参数但不报错 */ }
    texImage2D() {}

    createShader(type) { return { _type: type, _source: '' }; }
    shaderSource(shader, source) { shader._source = source; }
    compileShader(shader) { shader._compiled = true; }
    getShaderParameter(shader, pname) {
        if (pname === 0x8B81) return true;  // COMPILE_STATUS
        return null;
    }

    createProgram() { const id = { _shaders: [] }; this._programs.set(id, id); return id; }
    attachShader(program, shader) { program._shaders.push(shader); }
    linkProgram(program) { program._linked = true; }
    getProgramParameter(program, pname) {
        if (pname === 0x8B82) return true;  // LINK_STATUS
        return null;
    }
    useProgram(program) { this._currentProgram = program; }

    getError() { const e = this._error; this._error = 0; return e; }
    viewport(x, y, w, h) { this._viewport = { x, y, w, h }; }

    drawingBufferWidth = 300;
    drawingBufferHeight = 150;
}
```

### 7.2 Canvas 渲染哈希稳定性

```javascript
// Canvas 指纹检测的核心：toDataURL() 必须在多次调用间返回相同值
// 否则 SDK 判定为伪造环境
class StableCanvas {
    constructor() {
        this._fixedDataUrl = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUg...'; // 从真实浏览器捕获
        this._callCount = 0;
    }

    toDataURL(type) {
        this._callCount++;
        // 关键：每次返回完全相同的值
        return this._fixedDataUrl;
    }

    toBlob(callback, type, quality) {
        // 同样必须稳定
        const blob = new Blob([Buffer.from(this._fixedDataUrl.split(',')[1], 'base64')]);
        callback(blob);
    }
}
```

### 7.3 requestAnimationFrame 时序检测对抗

```javascript
// 部分 SDK 检测 requestAnimationFrame 的回调间隔
// 真实浏览器约 16.67ms (60fps)，固定间隔暴露伪造
let rafId = 0;
const rafCallbacks = new Map();

globalThis.requestAnimationFrame = (callback) => {
    const id = ++rafId;
    // 模拟 16.67ms ± 2ms 的自然抖动
    const delay = 16 + Math.random() * 4 - 2;
    const timer = setTimeout(() => {
        const now = performance.now();
        callback(now);
        rafCallbacks.delete(id);
    }, delay);
    rafCallbacks.set(id, timer);
    return id;
};

globalThis.cancelAnimationFrame = (id) => {
    const timer = rafCallbacks.get(id);
    if (timer) {
        clearTimeout(timer);
        rafCallbacks.delete(id);
    }
};
```

### 7.4 CSSOM 属性枚举检测对抗

```javascript
// 高级 SDK 会检查 document.styleSheets、getComputedStyle 等
globalThis.getComputedStyle = (element) => {
    const proxy = new Proxy({}, {
        get(target, prop) {
            // 返回合理的默认 CSS 值
            const defaults = {
                display: 'block', position: 'static', visibility: 'visible',
                opacity: '1', overflow: 'visible', zIndex: 'auto',
                width: '100px', height: '100px', margin: '0px', padding: '0px',
                fontFamily: 'Arial, sans-serif', fontSize: '16px', color: 'rgb(0, 0, 0)',
                backgroundColor: 'rgba(0, 0, 0, 0)', border: '0px none rgb(0, 0, 0)',
            };
            return defaults[prop] || '';
        }
    });
    return proxy;
};

globalThis.document.styleSheets = [];
```

---

## 失败模式编码

| 症状 | 原因 | 一线修复 | 仍失败兜底 |
|------|------|---------|-----------|
| `window is not defined` | 缺少window全局对象 | 补 Level 1 基础环境 | 检查SDK是否用了`globalThis`以外的方式访问 |
| `canvas.getContext is not a function` | Canvas API未模拟 | 补 Level 2 Canvas 2D | 检查是否还需要WebGL |
| `AudioContext not defined` | 音频指纹API缺失 | 补OfflineAudioContext | 检查是否返回了正确的Float32Array |
| SDK加载超时 | 无限循环或死锁 | 设置vm timeout=10s | 检查SDK是否有setInterval未清理 |
| `Function.toString`检测失败 | native code检测 | 应用toString修复 | 检查是否是`bind`后的函数 |
| navigator.userAgentData缺失 | Chrome 90+ API | 补userAgentData对象 | 检查brands格式 |
| Cookie操作报错 | document.cookie未实现 | 补cookie getter/setter | 检查是否需要httpOnly模拟 |
| `WebAssembly.instantiate`失败 | WASM导入函数缺失 | 补WASM桥接模板（见下文） | 用IdaPro分析WASM导入表 |
| Proxy/iframe检测 | SDK检测到代理或沙箱 | 补iframe contentWindow | 补Proxy handler默认行为 |
| 时区/语言不一致 | new Date()时区偏移 | 补Date.prototype.getTimezoneOffset | 统一navigator.language与时区 |

### SDK检测到非浏览器：系统性排查清单

当Step 4验证失败且错误信息模糊（如"环境异常"、"检测失败"无具体API名），按以下顺序逐一排查：

```
□ 1. Function.prototype.toString — 所有mock函数调用.toString()，必须返回 [native code]
□ 2. navigator.userAgent 一致性 — UA中的Chrome版本与userAgentData.brands一致
□ 3. navigator.plugins 长度 — 如需非零，补PluginArray模板
□ 4. iframe检测 — document.createElement('iframe').contentWindow 必须不为null
□ 5. Proxy检测 — 检查SDK是否用Proxy.observe检测代理对象
□ 6. 时区一致性 — Date.getTimezoneOffset() 必须与navigator.language匹配
□ 7. screen尺寸合理性 — width/height/colorDepth组合必须合理
□ 8. canvas指纹稳定性 — 同一session内多次getContext必须返回相同toDataURL
□ 9. WebSocket模拟 — 如SDK尝试ws连接，补WebSocket mock（+03ms随机延迟）
□ 10. localStorage配额 — 补localStorage剩余空间返回值（通常5MB）
```

🛑 **STOP**：排查清单全部通过但验证仍失败 → 进入Phase 2.5探索性重写（从头重新组织browser.js结构）

---

## 反模式黑名单

| # | 不要做 | 替代 |
|---|--------|------|
| 1 | 一次补全所有API | 从最小环境开始，按SDK报错递增 |
| 2 | 用jsdom替代手动补环境 | jsdom太重，触发更多检测，手动mock更可控 |
| 3 | 忽略toString检测 | 所有mock函数必须返回`[native code]` |
| 4 | 随机生成指纹值 | 同一session内指纹必须固定 |
| 5 | 在VM外执行SDK | 必须在VM沙箱内执行，避免污染全局 |
| 6 | 不设超时 | 必须设置10s超时，防止SDK死循环 |

---
