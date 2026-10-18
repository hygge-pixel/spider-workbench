# param-encryptor · 对抗深度增强（按需加载）

> 从 SKILL.md 下沉的请求级反检测六层防御栈（TLS 指纹对齐 / 时钟漂移 / Weibull 请求间隔 / Header 顺序 / Session 老化 / 请求依赖序）。**仅当目标有请求级行为风控时加载**；常规签名/加密参数生成不需要本文件。

## 对抗深度增强

> 加密参数还原不仅是算法复现，还必须对抗服务端的多维参数校验：
> **TLS 指纹一致性**、**时间漂移追踪**、**请求间隔分布**、**Header 排序**、**指纹老化**、**请求依赖序**。
> 六层防御，由外到内。

### 层1: TLS 指纹对齐（JA3/JA4）

```python
"""
TLS 指纹对齐 — 确保底层连接指纹与签名中的 User-Agent 一致。

问题：用 requests 发送请求时，Python 的 TLS 握手指纹（JA3 hash）
与声称的 Chrome UA 完全不同。高级风控会交叉校验：
  签名参数中 UA="Chrome 120" + 实际 TLS JA3="Python/urllib3" → 立即拒绝。

解决方案：使用 curl_cffi 控制 TLS 指纹，预置主流浏览器指纹库。
"""

# pip install curl_cffi
from curl_cffi import requests as cffi_requests

# ── 浏览器指纹预设 ──
BROWSER_PROFILES = {
    "chrome_120": {
        "ja3_hash": "771,4865-4866-4867-49195-49199-49196-49200-52393-52392-49171-49172-156-157-47-53,0-23-65281-10-11-35-16-5-13-18-51-45-43-27-17513,29-23-24,0",
        "impersonate": "chrome120",       # curl_cffi 内置 impersonate 标识
        "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    },
    "chrome_131": {
        "ja3_hash": "771,4865-4866-4867-49195-49199-49196-49200-52393-52392-49171-49172-156-157-47-53,0-23-65281-10-11-35-16-5-13-18-51-45-43-27-17513,29-23-24,0",
        "impersonate": "chrome131",
        "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    },
    "safari_17": {
        "ja3_hash": "771,4865-4866-4867-49195-49199-52393-52392-49171-49172-156-157-47-53,0-23-65281-10-11-35-16-5-13-18-51-45-43-27-17513,29-23-24,0",
        "impersonate": "safari17_0",
        "ua": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    },
}

class TLSFingerprintAligner:
    """TLS 指纹对齐器：确保请求 TLS 指纹与签名 UA 一致。

    用法：
        aligner = TLSFingerprintAligner("chrome_131")
        session = aligner.create_session()           # 已带正确 TLS 指纹 + UA
        resp = session.get("https://target.com/api")
    """

    def __init__(self, profile_name: str = "chrome_131"):
        if profile_name not in BROWSER_PROFILES:
            raise ValueError(f"未知浏览器配置: {profile_name}，可选: {list(BROWSER_PROFILES.keys())}")
        self.profile = BROWSER_PROFILES[profile_name]

    def create_session(self, **kwargs) -> cffi_requests.Session:
        """创建 TLS 指纹对齐的 Session。

        curl_cffi impersonate 参数会自动设置：
        - TLS ClientHello 参数（cipher suites、extensions、elliptic curves）
        - HTTP/2 SETTINGS 帧（HEADER_TABLE_SIZE、INITIAL_WINDOW_SIZE 等）
        - ALPN 协议协商顺序
        """
        session = cffi_requests.Session(impersonate=self.profile["impersonate"])
        session.headers.update({
            "User-Agent": self.profile["ua"],
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
        })
        return session

    def verify_fingerprint_consistency(self, sign_params: dict) -> bool:
        """校验签名参数与 TLS 指纹的一致性。

        检查项：
        1. sign_params 中的 UA 必须与 TLS 配置的 UA 相同
        2. sign_params 中的 platform 必须与 TLS 配置匹配
        3. sign_params 中的 screen 必须与 TLS 配置的设备类型合理
        """
        sign_ua = sign_params.get("_ua", sign_params.get("User-Agent", ""))
        if sign_ua and sign_ua != self.profile["ua"]:
            return False
        # platform 校验
        if "Macintosh" in self.profile["ua"]:
            if sign_params.get("_plat") not in ("MacIntel",):
                return False
        elif "Windows" in self.profile["ua"]:
            if sign_params.get("_plat") != "Win32":
                return False
        return True
```

### 层2: 时间漂移卡尔曼滤波

```python
"""
时间漂移追踪 — 解决本地时钟与服务器时钟偏差。

问题：很多站点校验时间戳与服务器时间差值。
  差值 > 5s → 拒绝；差值 < 0 → 拒绝。
简单的 server_time ± 500ms 不够：
  - 没有追踪累积漂移（本地时钟每分钟可能偏移 ±50ms）
  - 没有处理网络延迟的不对称性（上行 vs 下行 RTT 不同）
  - 没有检测服务器时间突变（服务器负载均衡导致 NTP 源不同）

方案：一维卡尔曼滤波器追踪 local-server 时间偏差。
"""

import time
import math

class ClockDriftTracker:
    """基于卡尔曼滤波的本地-服务器时钟偏差追踪器。

    状态模型：
        x[k] = local_time - server_time  （偏差，ms）
        观测模型：
            z[k] = (local_send + local_recv) / 2 - server_date_ms
            使用 RTT/2 作为测量噪声

    用法：
        tracker = ClockDriftTracker()
        # 每次收到服务器响应时更新
        tracker.update(server_date_ms=1717000000000, local_send_s=1717000000.0, local_recv_s=1717000000.1)
        # 生成签名时使用对齐后的时间戳
        ts = tracker.aligned_timestamp()
    """

    def __init__(self, process_noise: float = 50.0, initial_uncertainty: float = 5000.0):
        # 状态
        self.x = 0.0            # 估计偏差 (ms)，初始假设 0
        self.P = initial_uncertainty  # 估计不确定性 (ms²)
        self.Q = process_noise  # 过程噪声 (ms²/step)，时钟漂移约 50ms/步

        self._initialized = False
        self._samples = []

    def update(self, server_date_ms: int, local_send_s: float, local_recv_s: float):
        """从一次请求-响应对中更新偏差估计。

        Args:
            server_date_ms: 服务器 Date header 或接口返回的时间戳（ms）
            local_send_s: 发送请求时的本地时间（秒，time.time()）
            local_recv_s: 收到响应时的本地时间（秒）
        """
        local_mid_ms = (local_send_s + local_recv_s) / 2 * 1000  # RTT 中点
        rtt_ms = (local_recv_s - local_send_s) * 1000
        measurement_noise = max(rtt_ms / 2, 100.0)  # 测量噪声 ≥ RTT/2，下限 100ms

        # 观测值：本地 RTT 中点 - 服务器时间 = 偏差估计
        z = local_mid_ms - server_date_ms

        if not self._initialized:
            # 首次：直接用观测值初始化
            self.x = z
            self.P = measurement_noise ** 2
            self._initialized = True
            self._samples.append(z)
            return

        # ── 卡尔曼滤波更新 ──
        # 预测步骤（偏差恒定模型，加过程噪声）
        # x_pred = x（恒定）
        P_pred = self.P + self.Q

        # 更新步骤
        K = P_pred / (P_pred + measurement_noise ** 2)   # 卡尔曼增益
        self.x = self.x + K * (z - self.x)               # 状态更新
        self.P = (1 - K) * P_pred                         # 不确定性更新

        self._samples.append(z)
        # 突变检测：最近 5 次偏差标准差 > 2000ms → 可能服务器切换了 NTP 源
        if len(self._samples) >= 5:
            recent = self._samples[-5:]
            std = math.sqrt(sum((s - sum(recent)/5)**2 for s in recent) / 5)
            if std > 2000:
                self.P = 5000.0  # 重置不确定性，允许快速重新收敛

    def aligned_timestamp(self) -> int:
        """返回与服务器对齐的当前时间戳（ms）。

        local_time - x_estimated ≈ server_time
        """
        local_ms = int(time.time() * 1000)
        return local_ms - int(self.x)

    def aligned_timestamp_with_jitter(self) -> int:
        """对齐时间戳 + 微小自然抖动（±30ms，模拟网络传输延迟）"""
        import random
        ts = self.aligned_timestamp()
        return ts + random.randint(-30, 30)

    @property
    def confidence(self) -> str:
        """偏差估计的置信度"""
        std = math.sqrt(self.P)
        if std < 200:
            return "HIGH"   # ±200ms 内
        elif std < 1000:
            return "MEDIUM"
        else:
            return "LOW"    # 需要更多样本
```

### 层3: Weibull 请求间隔模型

```python
"""
请求间隔建模 — 替代 uniform 随机，使用 Weibull 分布模拟真实行为。

问题：uniform(1.5, 4.0) 产生均匀分布的间隔，统计学上太"整齐"。
真实人类的请求间隔服从 Weibull 分布：
  - 短间隔频繁（快速连续点击）
  - 偶尔长停顿（阅读/思考）
  - 形状参数 k 控制分布形态

Weibull 分布的形状参数：
  k < 1.0  → 前重分布（大量短间隔，偶尔极长） — 模拟"浏览翻页"
  k ≈ 1.0  → 指数分布（完全随机） — 模拟"无目的浏览"
  k = 1.5  → 偏右分布（集中在中段） — 模拟"有节奏的操作"
  k = 3.0+ → 近似正态（非常规律） — 模拟"机器行为" ← 避免！
"""

import random
import math

class WeibullIntervalModel:
    """Weibull 分布请求间隔生成器。

    用法：
        model = WeibullIntervalModel(shape=1.3, scale=3.0)  # k=1.3, λ=3s
        interval = model.next_interval()  # 返回秒
        time.sleep(interval)
    """

    def __init__(self, shape: float = 1.3, scale: float = 3.0, min_s: float = 0.5, max_s: float = 60.0):
        """
        Args:
            shape: Weibull 形状参数 k（推荐 1.0~1.5）
            scale: 尺度参数 λ（秒），中位数约 λ × (ln2)^(1/k)
            min_s: 最小间隔（秒）
            max_s: 最大间隔（秒），超出则截断
        """
        self.shape = shape
        self.scale = scale
        self.min_s = min_s
        self.max_s = max_s

    def next_interval(self) -> float:
        """生成一个 Weibull 分布的间隔（秒）。"""
        u = random.random()
        while u == 0:
            u = random.random()
        # Weibull 逆 CDF: x = λ × (-ln(U))^(1/k)
        interval = self.scale * (-math.log(u)) ** (1.0 / self.shape)
        return max(self.min_s, min(interval, self.max_s))

    def batch_intervals(self, count: int) -> list[float]:
        """预生成 count 个间隔，用于批量调度。"""
        return [self.next_interval() for _ in range(count)]


# ── 预置行为模型 ──
BEHAVIOR_MODELS = {
    "casual_browsing": WeibullIntervalModel(shape=1.0, scale=4.0),   # 随机浏览
    "focused_reading": WeibullIntervalModel(shape=1.5, scale=8.0),   # 阅读模式（间隔长）
    "rapid_interaction": WeibullIntervalModel(shape=0.8, scale=1.5), # 快速操作（短间隔多）
    "scroll_and_click": WeibullIntervalModel(shape=1.2, scale=3.0),  # 滚动+点击
    "form_filling": WeibullIntervalModel(shape=1.8, scale=5.0),      # 表单填写（节奏稳定）
}


class PriorityRequestScheduler:
    """带优先级的请求调度器 — 不同类型请求使用不同间隔模型。

    请求优先级：
    - "navigation": 页面导航（HTML），间隔短，优先级最高
    - "api": 数据接口（XHR/Fetch），间隔中等
    - "resource": 静态资源（CSS/JS/IMG），间隔短但可并发
    """

    INTERVAL_MODELS = {
        "navigation": WeibullIntervalModel(shape=1.3, scale=2.0, min_s=0.8, max_s=15.0),
        "api":        WeibullIntervalModel(shape=1.2, scale=3.5, min_s=1.0, max_s=30.0),
        "resource":   WeibullIntervalModel(shape=0.9, scale=0.5, min_s=0.1, max_s=5.0),
    }

    def __init__(self):
        self._last_request_time = 0.0
        self._last_type = None

    def wait(self, request_type: str = "api"):
        """根据请求类型等待适当的间隔。"""
        model = self.INTERVAL_MODELS.get(request_type, self.INTERVAL_MODELS["api"])
        interval = model.next_interval()

        now = time.time()
        if self._last_request_time > 0:
            elapsed = now - self._last_request_time
            if elapsed < interval:
                time.sleep(interval - elapsed)

        self._last_request_time = time.time()
        self._last_type = request_type
```

### 层4: Header 排序随机化

```python
"""
HTTP Header 排序 — 浏览器发送 header 有固定顺序，Python requests 没有。

问题：Python requests 按字母序发送 header，Chrome 按固定非字母序。
高级风控会检查 header 顺序是否与声称的浏览器一致。

方案：按浏览器类型预置 header 顺序模板，每次请求时应用。
"""

import random

# Chrome 131 典型 header 发送顺序（通过 DevTools Network > Headers 观察得到）
CHROME_HEADER_ORDER = [
    ":method", ":authority", ":scheme", ":path",      # HTTP/2 伪头部
    "host", "connection",                               # 连接控制
    "content-length",                                   # 内容元数据
    "sec-ch-ua", "sec-ch-ua-mobile", "sec-ch-ua-platform",  # Client Hints
    "upgrade-insecure-requests",
    "user-agent",
    "accept",
    "sec-fetch-site", "sec-fetch-mode", "sec-fetch-user", "sec-fetch-dest",  # Fetch Metadata
    "referer",
    "accept-encoding",
    "accept-language",
    "cookie",
]

# 导航请求 vs API 请求的 header 子集
NAVIGATION_HEADERS = ["host", "user-agent", "accept", "accept-encoding", "accept-language",
                      "sec-ch-ua", "sec-ch-ua-mobile", "sec-ch-ua-platform",
                      "sec-fetch-site", "sec-fetch-mode", "sec-fetch-user", "sec-fetch-dest",
                      "upgrade-insecure-requests", "cookie"]
API_HEADERS = ["host", "content-length", "sec-ch-ua", "sec-ch-ua-mobile", "sec-ch-ua-platform",
               "user-agent", "accept", "sec-fetch-site", "sec-fetch-mode", "sec-fetch-dest",
               "referer", "accept-encoding", "accept-language", "cookie",
               "content-type", "x-requested-with"]


class HeaderOrderRandomizer:
    """Header 排序随机化器。

    原理：
    1. 每个浏览器有固定的 header 发送顺序（指纹之一）
    2. 同一浏览器不同版本的顺序可能略有不同
    3. 用 curl_cffi impersonate 时已自动处理 HTTP/2 帧的 header 顺序
    4. 此模块用于需要手动控制 header 顺序的场景（如 HTTP/1.1）

    用法：
        randomizer = HeaderOrderRandomizer()
        ordered = randomizer.order_headers(my_headers, request_type="api")
        session.headers = ordered  # 注意：普通 dict 不保证顺序，需要用 OrderedDict
    """

    def __init__(self, browser: str = "chrome"):
        self.order = CHROME_HEADER_ORDER

    def order_headers(self, headers: dict, request_type: str = "api") -> dict:
        """将 headers 按浏览器顺序排列。

        Args:
            headers: 原始 header dict
            request_type: "navigation" | "api"

        Returns:
            OrderedDict，key 按 Chrome 顺序排列
        """
        from collections import OrderedDict

        template = API_HEADERS if request_type == "api" else NAVIGATION_HEADERS
        ordered = OrderedDict()

        # 按 Chrome 模板顺序放入
        for key in template:
            lower_key = key.lower()
            for orig_key, value in headers.items():
                if orig_key.lower() == lower_key:
                    ordered[orig_key] = value
                    break

        # 剩余不在模板中的 header 追加到末尾
        for orig_key, value in headers.items():
            if orig_key.lower() not in {k.lower() for k in ordered}:
                ordered[orig_key] = value

        return ordered
```

### 层5: Session 指纹老化

```python
"""
Session 指纹老化 — 模拟真实用户 session 随时间自然演变。

问题：真实用户的 session 行为会随时间变化：
  - 新用户：探索性行为多、操作慢、请求间隔大
  - 熟悉用户：操作快、请求间隔短、路径固定
  - 老化 session：Cookie 数量增长、行为模式稳定

如果多个 session 永远保持相同的行为参数 → 可被识别为批量账号。
"""

import time
import random
import math

class SessionFingerprintAging:
    """Session 行为参数随时间自然演变。

    用法：
        aging = SessionFingerprintAging(session_start=time.time())
        # 每次生成签名参数时，注入老化参数
        params = aging.inject_aging_params(base_params)
    """

    def __init__(self, session_start: float = None, personality: str = None):
        """
        Args:
            session_start: session 创建时间（time.time()）
            personality: "cautious"(谨慎) | "normal"(普通) | "expert"(熟练)
        """
        self.session_start = session_start or time.time()
        # 随机选择人格，避免所有 session 行为模式相同
        self.personality = personality or random.choice(["cautious", "normal", "expert"])

        # 人格参数基线
        self._personality_params = {
            "cautious": {"base_speed": 0.6, "explore_rate": 0.4, "error_rate": 0.05},
            "normal":   {"base_speed": 1.0, "explore_rate": 0.2, "error_rate": 0.02},
            "expert":   {"base_speed": 1.5, "explore_rate": 0.05, "error_rate": 0.01},
        }

    @property
    def age_minutes(self) -> float:
        """session 年龄（分钟）"""
        return (time.time() - self.session_start) / 60.0

    @property
    def speed_multiplier(self) -> float:
        """操作速度随 session 老化变化。

        学习曲线模型：speed = base × (1 - e^(-age/τ))
        - 新 session → 接近 base（慢）
        - 老 session → 趋近 base × 1.3（快 30%）
        """
        base = self._personality_params[self.personality]["base_speed"]
        tau = 10.0  # 时间常数（分钟），10 分钟后达到 63% 的最大速度
        return base * (1.3 - 0.3 * math.exp(-self.age_minutes / tau))

    def inject_aging_params(self, params: dict) -> dict:
        """向签名参数注入老化特征。

        添加的参数不会直接被服务端校验，但影响行为模型：
        - 请求间隔的 scale 参数（速度快 → 间隔短）
        - 操作复杂度标记
        """
        params["_session_age"] = int(self.age_minutes)
        params["_speed_mult"] = round(self.speed_multiplier, 3)
        return params

    def get_interval_model(self) -> 'WeibullIntervalModel':
        """根据 session 年龄返回适配的间隔模型。

        新 session → shape=1.0（随机探索），scale 较大
        老 session → shape=1.5（有节奏），scale 较小
        """
        # shape: 1.0 → 1.5，随年龄线性增长
        shape = 1.0 + min(0.5, self.age_minutes / 60.0 * 0.5)
        # scale: 初始 5s，老化后缩短到 2s
        scale = max(2.0, 5.0 - self.age_minutes / 30.0)

        return WeibullIntervalModel(shape=shape, scale=scale)
```

### 层6: 请求依赖序守卫

```python
"""
请求依赖序 — 维护请求之间的逻辑顺序约束。

问题：真实浏览器的请求有严格的依赖顺序：
  1. 先 GET / → 获取 HTML
  2. 再 GET /static/app.js → 加载 JS
  3. 再 POST /api/token → 获取 token
  4. 最后 POST /api/data → 带 token 的业务请求

如果跳过步骤 3 直接发步骤 4 → 请求无效，且可能触发风控。
"""

import time
import random
from collections import defaultdict

class RequestSequenceGuard:
    """请求依赖序守卫。

    用法：
        guard = RequestSequenceGuard()
        guard.declare("token_api", requires=["html_page"])
        guard.declare("data_api", requires=["token_api"])

        guard.wait_for_deps("data_api")  # 会阻塞直到 token_api 已完成
        resp = session.post("/api/data", ...)
        guard.mark_done("data_api")
    """

    def __init__(self):
        self._deps = {}           # name → [required_names]
        self._done = {}           # name → timestamp
        self._cascade_delay = defaultdict(float)  # dep → 完成后的最小等待

    def declare(self, name: str, requires: list[str] = None, cascade_delay: float = 0.5):
        """声明请求依赖关系。

        Args:
            name: 请求标识
            requires: 前置请求列表
            cascade_delay: 前置请求完成后的最小等待（秒），模拟浏览器解析+执行延迟
        """
        self._deps[name] = requires or []
        for dep in (requires or []):
            self._cascade_delay[dep] = cascade_delay

    def wait_for_deps(self, name: str, timeout: float = 30.0):
        """等待所有前置请求完成，并加上瀑布流延迟。

        瀑布流模型：
        - HTML 加载后 200-500ms 才开始加载 JS（解析时间）
        - JS 加载后 100-300ms 才发起 API 请求（执行时间）
        - token 获取后 50-200ms 才发起业务请求（构造请求时间）
        """
        deps = self._deps.get(name, [])
        start = time.time()

        for dep in deps:
            while dep not in self._done:
                if time.time() - start > timeout:
                    raise TimeoutError(f"请求依赖超时: {name} 等待 {dep}")
                time.sleep(0.05)

            # 瀑布流延迟：前置请求完成后等待一段时间
            cascade = self._cascade_delay.get(dep, 0.5)
            jitter = random.uniform(0.8, 1.2)  # ±20% 抖动
            elapsed_since_dep = time.time() - self._done[dep]
            wait_time = cascade * jitter - elapsed_since_dep
            if wait_time > 0:
                time.sleep(wait_time)

    def mark_done(self, name: str):
        """标记请求已完成。"""
        self._done[name] = time.time()

    def is_done(self, name: str) -> bool:
        return name in self._done

    def reset(self):
        """重置所有状态（新页面/新流程时调用）。"""
        self._done.clear()


# ── 典型 Web 请求依赖图 ──
def create_typical_web_flow() -> RequestSequenceGuard:
    """创建典型 Web 应用的请求依赖图。

    依赖链：
    html_page → js_bundle → token_api → data_api
                js_bundle → config_api → data_api
    """
    guard = RequestSequenceGuard()
    guard.declare("html_page", cascade_delay=0.3)                          # HTML 解析
    guard.declare("js_bundle", requires=["html_page"], cascade_delay=0.2)  # JS 下载+解析
    guard.declare("token_api", requires=["js_bundle"], cascade_delay=0.15) # token 获取
    guard.declare("config_api", requires=["js_bundle"], cascade_delay=0.1) # 配置加载
    guard.declare("data_api", requires=["token_api", "config_api"])        # 业务请求
    return guard
```

### 整合示例：六层防御全栈用法

```python
"""
完整对抗栈整合示例 — 从 TLS 到请求序的全链路防护。
"""

def create_resilient_session(browser: str = "chrome_131") -> dict:
    """创建对抗感知的请求栈。

    Returns:
        dict containing:
        - session: curl_cffi Session（TLS 对齐）
        - clock: ClockDriftTracker（时间漂移）
        - scheduler: PriorityRequestScheduler（间隔控制）
        - aging: SessionFingerprintAging（指纹老化）
        - sequence: RequestSequenceGuard（依赖序）
        - aligner: TLSFingerprintAligner（TLS 校验）
    """
    # 层1: TLS 指纹对齐
    aligner = TLSFingerprintAligner(browser)
    session = aligner.create_session()

    # 层2: 时间漂移追踪
    clock = ClockDriftTracker()

    # 层3: 请求间隔
    scheduler = PriorityRequestScheduler()

    # 层5: Session 老化
    aging = SessionFingerprintAging()

    # 层6: 请求依赖序
    sequence = create_typical_web_flow()

    return {
        "session": session,
        "clock": clock,
        "scheduler": scheduler,
        "aging": aging,
        "sequence": sequence,
        "aligner": aligner,
    }


# ── 典型使用流程 ──
def example_usage():
    stack = create_resilient_session("chrome_131")
    session = stack["session"]
    clock = stack["clock"]
    scheduler = stack["scheduler"]
    sequence = stack["sequence"]
    aging = stack["aging"]
    aligner = stack["aligner"]

    # 1. 先请求首页，同步时钟
    scheduler.wait("navigation")
    t0 = time.time()
    resp = session.get("https://target.com/")
    t1 = time.time()
    # 从 Date header 获取服务器时间
    from email.utils import parsedate_to_datetime
    server_date = parsedate_to_datetime(resp.headers["Date"])
    server_ms = int(server_date.timestamp() * 1000)
    clock.update(server_ms, t0, t1)
    sequence.mark_done("html_page")

    # 2. 加载 JS
    scheduler.wait("resource")
    resp = session.get("https://target.com/static/app.js")
    sequence.mark_done("js_bundle")

    # 3. 获取 token
    sequence.wait_for_deps("token_api")
    scheduler.wait("api")
    timestamp = clock.aligned_timestamp_with_jitter()
    sign_params = aging.inject_aging_params({"_ts": timestamp, "action": "get_token"})
    # 校验 TLS-签名一致性
    assert aligner.verify_fingerprint_consistency(sign_params)
    resp = session.post("https://target.com/api/token", json=sign_params)
    sequence.mark_done("token_api")

    # 4. 业务请求
    sequence.wait_for_deps("data_api")
    scheduler.wait("api")
    timestamp = clock.aligned_timestamp_with_jitter()
    params = aging.inject_aging_params({"_ts": timestamp, "data": "..."})
    resp = session.post("https://target.com/api/data", json=params)
    sequence.mark_done("data_api")
```
