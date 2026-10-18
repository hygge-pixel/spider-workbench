# Captcha Core Techniques

通用的图片识别、轨迹生成和行为建模材料。厂商协议与提交加密请读取对应 provider 文档。

## Contents

- 一、识别配方
- 配方1: slider-opencv（滑块本地识别）
- 二、轨迹生成配方
- 配方5: trajectory-bezier（贝塞尔曲线轨迹）
- 配方6: trajectory-5phase（五段式物理轨迹）
- 行为建模增强
- 鼠标加速度曲线建模
- 点击热区分布建模
- 操作时序建模
- 配方8: encrypt-aes-cbc（AES-CBC加密验证码数据）

### 一、识别配方

#### 配方1: slider-opencv（滑块本地识别）

```python

### 二、轨迹生成配方

#### 配方5: trajectory-bezier（贝塞尔曲线轨迹）

```python
import random, math

def generate_trajectory(distance: int, duration_ms: int = 1000) -> list:
    """贝塞尔曲线 + 过冲回拉 + Y轴抖动
    返回：[[x, y, elapsed_ms], ...]
    """
    points = []
    # 参数
    overshoot = random.randint(3, 8)  # 过冲量
    y_jitter = lambda: random.randint(-3, 3)

    # 阶段1：加速 (0 → 70%)
    steps1 = int(duration_ms * 0.4 / 15)
    for i in range(steps1):
        t = i / steps1
        x = int(distance * 0.7 * t * t)  # 二次加速
        points.append([x, y_jitter(), i * 15])

    # 阶段2：匀速过冲 (70% → 100%+overshoot)
    steps2 = int(duration_ms * 0.2 / 15)
    for i in range(steps2):
        t = i / steps2
        x = int(distance * 0.7 + (distance * 0.3 + overshoot) * t)
        points.append([x, y_jitter(), int(duration_ms * 0.4) + i * 15])

    # 阶段3：回拉到目标
    steps3 = int(duration_ms * 0.1 / 15)
    for i in range(steps3):
        t = i / steps3
        x = int(distance + overshoot - overshoot * t)
        points.append([x, y_jitter(), int(duration_ms * 0.6) + i * 15])

    # 阶段4：停留抖动
    steps4 = int(duration_ms * 0.3 / 15)
    for i in range(steps4):
        points.append([distance + random.randint(-1, 1), y_jitter(), int(duration_ms * 0.7) + i * 15])

    return points
```

#### 配方6: trajectory-5phase（五段式物理轨迹）

```python

## 行为建模增强

> 验证码检测不仅看结果（坐标是否正确），还看过程（轨迹是否像人类、操作时序是否自然）。
> 以下是对抗行为分析的系统性建模方法。

### 鼠标加速度曲线建模

```python
import random
import math

class MouseBehaviorModel:
    """鼠标行为模型：模拟人类从起点移动到目标的完整过程

    人类特征：
    1. 起动阶段：加速度从 0 逐渐增大（不是瞬间达到最大速度）
    2. 接近阶段：在目标附近减速（不是精确停在目标上）
    3. 微调阶段：到达后做微小调整（±1-3px）
    4. 点击前有短暂停留（100-300ms）
    """

    @staticmethod
    def generate_mouse_path(start_x, start_y, end_x, end_y, duration_ms=800):
        """生成从起点到终点的鼠标移动路径"""
        points = []
        distance = math.sqrt((end_x - start_x)**2 + (end_y - start_y)**2)

        # 贝塞尔控制点：加入随机弧度（人类不会直线移动）
        mid_offset = random.randint(10, 30) * random.choice([-1, 1])
        ctrl_x = (start_x + end_x) / 2 + mid_offset
        ctrl_y = (start_y + end_y) / 2 + random.randint(-15, 15)

        steps = int(duration_ms / 15)  # ~15ms 采样间隔
        for i in range(steps):
            t = i / steps
            # 贝塞尔插值
            x = (1-t)**2 * start_x + 2*(1-t)*t * ctrl_x + t**2 * end_x
            y = (1-t)**2 * start_y + 2*(1-t)*t * ctrl_y + t**2 * end_y

            # 速度曲线：缓入缓出（sigmoid-like）
            speed_factor = 4 * t * (1 - t)  # 抛物线，中间快两端慢
            # 加入加速度抖动
            x += random.gauss(0, 0.5) * (1 - speed_factor)
            y += random.gauss(0, 0.3)

            points.append([round(x, 1), round(y, 1), i * 15])

        # 到达后微调（模拟人类手抖）
        for _ in range(random.randint(2, 5)):
            t = points[-1][2] + random.randint(50, 150)
            points.append([
                end_x + random.gauss(0, 1.2),
                end_y + random.gauss(0, 0.8),
                t
            ])

        return points
```

### 点击热区分布建模

```python
class ClickHeatmapModel:
    """点击热区模型：人类不会精确点击按钮中心

    人类点击特征：
    1. 点击位置围绕目标中心呈高斯分布
    2. 标准差约 5-15px（取决于按钮大小）
    3. 偏好偏上方和偏右方（右手习惯）
    4. 连续点击位置不会完全相同
    """

    @staticmethod
    def human_click(center_x, center_y, button_size=50):
        """生成一个人类风格的点击坐标

        Args:
            center_x, center_y: 按钮中心坐标
            button_size: 按钮直径（像素）
        Returns:
            (click_x, click_y): 点击坐标
        """
        # 标准差约为按钮尺寸的 10-20%
        sigma = button_size * random.uniform(0.1, 0.2)

        # 偏右偏上偏好（右手习惯）
        offset_x = random.gauss(sigma * 0.3, sigma)
        offset_y = random.gauss(-sigma * 0.2, sigma)

        click_x = center_x + offset_x
        click_y = center_y + offset_y

        return round(click_x), round(click_y)
```

### 操作时序建模

```python
class OperationTimingModel:
    """操作时序模型：控制各步骤之间的时间间隔

    验证码 SDK 会检测：
    1. 图片加载到开始操作的时间（人类需要 0.5-3s 观察图片）
    2. 滑动/点击的持续时间（太快或太慢都是可疑的）
    3. 操作结束到提交的时间（人类会检查结果再提交）
    """

    @staticmethod
    def observation_delay(image_complexity='normal'):
        """图片观察时间（从图片加载完成到开始操作）

        Args:
            image_complexity: 'simple'(算术题)/'normal'(标准滑块)/'complex'(点选/九宫格)
        """
        ranges = {
            'simple': (300, 800),     # 简单验证码：0.3-0.8s
            'normal': (800, 2500),    # 标准滑块：0.8-2.5s
            'complex': (2000, 5000),  # 点选/九宫格：2-5s
        }
        low, high = ranges.get(image_complexity, ranges['normal'])
        return random.uniform(low, high) / 1000  # 返回秒

    @staticmethod
    def slide_duration(distance_px):
        """滑动持续时间（基于距离的自然映射）

        人类特征：
        - 短距离(50-100px)：300-600ms
        - 中距离(100-200px)：500-1000ms
        - 长距离(200-300px)：800-1500ms
        - 有自然变异（同距离多次滑动时间不同）
        """
        base = 300 + distance_px * 3  # 基础时间与距离正相关
        jitter = random.uniform(-100, 200)  # 自然变异
        return (base + jitter) / 1000  # 返回秒

    @staticmethod
    def verification_delay():
        """操作完成到提交的延迟（人类会检查结果）

        人类特征：
        - 滑块：松手后等 0.2-0.8s 再提交
        - 点选：最后一个点选后等 0.5-1.5s
        """
        return random.uniform(0.2, 0.8)
```

> 以下加密配方服务于验证码提交流程（与轨迹+坐标一起使用）。非验证码的加密参数场景使用 `param-encryptor`。

#### 配方8: encrypt-aes-cbc（AES-CBC加密验证码数据）

```python
