# 外部优秀逆向工具收录

本文件收录GitHub上优秀的Web逆向工程工具，均为跨平台可用（npm/pip安装）。

---

## 一、JS反混淆与解包

### webcrack (⭐推荐)
- **仓库**: https://github.com/j4k0xb/webcrack
- **安装**: `npm install -g webcrack`
- **能力**: obfuscator.io 反混淆、webpack/browserify 解包、代码美化、死代码移除
- **用法**: `npx webcrack input.js -o output.js`
- **特点**: 自动检测混淆模式，无需配置，TypeScript编写，安全（考虑作用域和引用）

### js-beautify
- **仓库**: https://github.com/beautifier/js-beautify
- **安装**: `npm install -g js-beautify`
- **能力**: JS代码格式化、解压缩
- **用法**: `npx js-beautify input.js -o output.js`
- **特点**: 最基础的代码美化工具，处理简单压缩的代码

### synchrony (js-deobfuscator)
- **仓库**: https://github.com/ben-sb/obfuscator-io-deobfuscator
- **能力**: obfuscator.io 专用反混淆
- **特点**: 针对 obfuscator.io 的专用工具，支持字符串数组、控制流平坦化等

---

## 二、流量分析与抓包

### mitmproxy & mitmproxy-mcp
- **仓库**: https://github.com/mitmproxy/mitmproxy
- **MCP Server**: https://github.com/snapspecter/mitmproxy-mcp
- **安装**: `pip install mitmproxy`
- **能力**: HTTPS中间人代理，拦截/修改/重放HTTP流量
- **特点**: Python原生，支持脚本化流量处理，可集成到逆向workflow
- **MCP版本**: 允许AI Agent直接操作流量拦截和分析

### Yakit
- **仓库**: https://github.com/yaklang/yakit
- **能力**: 国产网络安全工具平台，内置MITM代理、流量重放、漏洞扫描
- **特点**: 图形化界面，适合复杂流量分析和Web安全测试

### whistle
- **仓库**: https://github.com/avwo/whistle
- **安装**: `npm install -g whistle`
- **能力**: 跨平台Web调试代理工具
- **特点**: Node.js实现，支持规则配置，可拦截修改请求/响应

---

## 三、浏览器自动化与反检测

### DrissionPage
- **仓库**: https://github.com/g1879/DrissionPage
- **能力**: Python浏览器自动化，内置反检测
- **特点**: 国产工具，对国内网站适配好，无需WebDriver

### pydoll
- **仓库**: https://github.com/autoscrape-labs/pydoll
- **安装**: `pip install pydoll`
- **能力**: Python CDP浏览器自动化，内置反检测
- **特点**: 异步架构，支持拦截修改请求

### nodriver / camopy
- **仓库**: https://github.com/ultrafunkamsterdam/nodriver (原 undetected-chromedriver 作者)
- **能力**: Python反检测浏览器自动化
- **特点**: 极简API，持续更新对抗反自动化检测

---

## 四、爬虫框架

### crawlee (Python)
- **仓库**: https://github.com/apify/crawlee-python
- **安装**: `pip install crawlee`
- **能力**: 生产级爬虫框架，自动重试、队列管理、反爬处理
- **特点**: 现代化设计，支持Playwright/HTTP混合模式

### Scrapy
- **仓库**: https://github.com/scrapy/scrapy
- **安装**: `pip install scrapy`
- **能力**: 经典Python爬虫框架
- **特点**: 生态成熟，中间件丰富

### colly (Go)
- **仓库**: https://github.com/gocolly/colly
- **能力**: Go语言高性能爬虫框架
- **特点**: 适用于高并发采集场景

---

## 五、加解密工具

### CyberChef
- **仓库**: https://github.com/gchq/CyberChef
- **能力**: 浏览器端数据转换"瑞士军刀"，支持数百种编解码/加解密/压缩操作
- **特点**: 拖拽式操作，可视化编解码链，支持自定义配方

### gmssl (国密)
- **仓库**: https://github.com/duanhongyi/gmssl
- **安装**: `pip install gmssl`
- **能力**: Python国密SM2/SM3/SM4实现
- **特点**: 国产加密算法Python库

### ecdsa (椭圆曲线)
- **仓库**: https://github.com/tlsfuzzer/python-ecdsa
- **安装**: `pip install ecdsa`
- **能力**: ECDSA 签名/验证，支持 P-256/P-384/secp256k1 曲线
- **特点**: 纯 Python 实现，Web Crypto API 对齐

### blackboxprotobuf
- **仓库**: https://github.com/nccgroup/blackboxprotobuf
- **安装**: `pip install blackboxprotobuf`
- **能力**: 无 .proto 文件的 Protobuf 解码
- **特点**: 自动推断消息结构，适合逆向未知 Protobuf 数据

---

## 六、验证码识别

### ddddocr
- **仓库**: https://github.com/sml2h3/ddddocr
- **安装**: `pip install ddddocr`
- **能力**: 深度学习通用验证码OCR识别
- **特点**: 国产，支持多种验证码类型，开箱即用

### muggle_ocr
- **仓库**: https://github.com/kerlomz/muggle_ocr
- **能力**: 神经网络验证码识别
- **特点**: 训练好的模型，识别率较高

---

## 七、反混淆学习资源

### Awesome JavaScript Deobfuscation
- **仓库**: https://github.com/topics/javascript-deobfuscation
- **内容**: GitHub上的JS反混淆工具集合

### javascript-malware-collection
- **仓库**: https://github.com/HynekPetrak/javascript-malware-collection
- **内容**: 近40,000个JavaScript恶意软件样本
- **用途**: 作为反混淆工具测试集

### CrawlSpace (反反爬)
- **仓库**: https://github.com/BruceDone/awesome-crawler
- **内容**: 各语言的爬虫工具/框架大合集

---

## 八、平台专用逆向参考

### 京东 h5st
- **dengbaikun/jdh5st**: https://github.com/dengbaikun/jdh5st — h5st 签名算法分析 + Python 实现
- **ShilongLee/Crawler**: https://github.com/ShilongLee/Crawler — 多平台爬虫（含京东 h5st），Docker 一键部署

### 抖音 a_bogus / X-Bogus
- **jackluson/a_bogus_douyin**: https://github.com/jackluson/a_bogus_douyin — 在线签名服务（Cloudflare Worker），开箱即用
- **G-catmint/douyin**: https://github.com/G-catmint/douyin — JSVMP 纯算法还原，含 captchaBody/滑块轨迹
- **ShilongLee/Crawler**: https://github.com/ShilongLee/Crawler — 同样包含抖音 a_bogus

### 小红书 X-s
- **ShilongLee/Crawler**: https://github.com/ShilongLee/Crawler — 含小红书签名

### 拼多多 anti_content
方法范围：通用资料示例；本包不含旧项目实现、运行记录或当前在线验证状态。

---

## 使用建议

| 需求 | 首选工具 | 备选 |
|------|----------|------|
| JS反混淆/解webpack | webcrack | js-beautify + 手动分析 |
| 流量抓包分析 | mitmproxy / reqable | whistle / Yakit |
| 浏览器自动化(有反爬) | DrissionPage / pydoll | nodriver |
| 验证码识别 | ddddocr | 云打码平台 |
| 国密算法 | gmssl | 手动实现 |
| ECDSA 签名 | python-ecdsa | cryptography |
| Protobuf 解码 | blackboxprotobuf | protoc 编译 |
| 京东 h5st 签名 | dengbaikun/jdh5st | ShilongLee/Crawler |
| 抖音 a_bogus | jackluson/a_bogus_douyin | G-catmint/douyin |
| 数据快速转换 | CyberChef | Python REPL |
