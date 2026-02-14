# ColorTune - AI驱动的专业调色工具

<div align="center">
  <h3>🎨 个性化风格学习 | 🤖 多模型 AI 支持 | 🎯 专业级调色</h3>
  <p>通过 AI 学习你的审美偏好，自动生成符合你风格的调色方案</p>
  
  [![GitHub Stars](https://img.shields.io/github/stars/TUNGTREE/AI-ColorTune?style=social)](https://github.com/TUNGTREE/AI-ColorTune)
  [![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
  [![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
  [![TypeScript](https://img.shields.io/badge/TypeScript-5.0%2B-blue)](https://www.typescriptlang.org/)
</div>

---

## ✨ 核心特性

- 🎨 **AI 风格学习** - 通过多轮测试学习你的审美偏好，建立专属调色档案
- 🤖 **多 AI 模型** - 支持 Claude、OpenAI、通义千问、Deepseek、GLM，可运行时切换
- 🎯 **智能调色** - 基于风格档案为每张照片生成 3 个调色方案
- 🎚️ **专业参数** - 33 个参数：曝光、对比、色温、HSL 分通道、分离色调等
- ⚡ **实时预览** - CSS Filter 即时响应 + 服务端精确渲染
- 🌙 **暗色 UI** - 参考 Lightroom 的专业暗色界面

---

## 🚀 快速开始

### 环境要求
- Python 3.10+、Node.js 18+
- AI API Key（Claude / OpenAI / 阿里云通义千问/ Deepseek / GLM ）

### 安装步骤

```bash
# 1. 克隆项目
git clone https://github.com/TUNGTREE/AI-ColorTune.git
cd AI-ColorTune

# 2. 启动后端
cd backend
python -m venv venv
venv\Scripts\activate          # Windows (macOS/Linux: source venv/bin/activate)
pip install -r requirements.txt
uvicorn app.main:app --reload

# 3. 启动前端（新终端）
cd frontend
npm install
npm run dev
```

访问 http://localhost:5173，点击右上角 **"AI 设置"** 配置 AI 服务商即可开始使用。

---

## 📖 使用流程

### 步骤 0：风格发现
从示例场景中选择 3-12 个进行风格测试，AI 为每个场景生成 4 种调色风格，你选择最喜欢的。完成后 AI 分析你的选择模式，生成风格档案（色温偏好、对比度偏好、饱和度偏好等）。

### 步骤 1：智能调色
上传待调色照片（JPG/PNG/TIFF，最大 50MB），AI 结合你的风格档案和照片特征生成 3 个调色方案，每个方案包含预览图、参数和推荐理由。使用 Before/After 滑块对比效果。

### 步骤 2：精细微调
选择一个方案后进入微调面板，包含 3 大类共 33 个专业参数。拖动滑块即时预览（CSS Filter），停止拖动 500ms 后自动切换为服务端精确渲染。

### 步骤 3：全分辨率导出
选择导出格式（JPEG/PNG/TIFF），在原图全分辨率应用所有调色参数，下载成品。

---

## 🏗️ 技术架构

| 层级 | 技术 |
|------|------|
| **后端** | FastAPI + Uvicorn + SQLAlchemy + SQLite |
| **图像处理** | Pillow + NumPy + OpenCV |
| **AI** | Anthropic SDK + OpenAI SDK |
| **前端** | React 18 + TypeScript + Vite |
| **UI** | Ant Design + Zustand |

### 项目结构

```
AI-ColorTune/
├── backend/app/
│   ├── main.py              # FastAPI 应用入口
│   ├── core/                # 核心算法（图像处理、提示词、参数模型）
│   ├── models/              # SQLAlchemy 数据模型
│   ├── api/                 # API 端点（upload, style, grading, ai_config）
│   └── services/            # 业务逻辑（AI 提供商、风格、调色、示例场景）
│
├── frontend/src/
│   ├── components/          # StyleDiscovery, GradingSuggestion, FineTune, Export
│   ├── api/                 # Axios API 客户端
│   ├── stores/              # Zustand 状态管理
│   └── types/               # TypeScript 类型定义
│
├── uploads/                 # 用户上传原图
├── samples/                 # 示例场景图
├── previews/                # 调色预览缓存
└── exports/                 # 导出成品
```

---

## 🧪 测试

```bash
cd backend
pytest -v  # 运行所有单元测试
```

---

## 🤝 贡献

欢迎为项目贡献代码、文档或建议！

### 贡献方向
- 📝 **文档改进**：优化说明文档、添加使用案例
- 🐛 **Bug 修复**：修复已知问题、改进错误处理
- 🎨 **新增功能**：更多调色算法、胶片模拟效果
- 🤖 **AI 集成**：支持更多 AI 模型（Gemini、Llama-Vision 等）
- 📷 **格式支持**：RAW 格式支持（.CR2、.NEF、.ARW）
- 🎬 **视频调色**：视频 LUT 应用、批量处理

### 提交流程
1. Fork 本仓库
2. 创建特性分支：`git checkout -b feature/amazing-feature`
3. 提交修改：`git commit -m 'Add some amazing feature'`
4. 推送分支：`git push origin feature/amazing-feature`
5. 提交 Pull Request

---

## 📄 开源协议

本项目采用 **MIT License** 开源协议。

### 许可内容

✅ **商业使用** - 可用于商业项目  
✅ **修改** - 可自由修改代码  
✅ **分发** - 可重新分发  
✅ **私有使用** - 可用于私有项目  
✅ **专利授权** - 包含专利使用权  

### 唯一要求

📋 保留原作者版权声明和许可证副本

<details>
<summary><b>查看完整许可证文本</b></summary>

```
MIT License

Copyright (c) 2026 TUNGTREE

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

</details>

---

## 🙏 致谢

### AI 服务提供商
感谢以下 AI 服务提供商的强大支持：
- **[Anthropic](https://www.anthropic.com/)** - Claude Sonnet 4.5 提供卓越的视觉理解和专业调色建议
- **[OpenAI](https://openai.com/)** - GPT-4 Vision 的多模态能力
- **[阿里云 DashScope](https://dashscope.aliyun.com/)** - 通义千问 VL Plus 的高性价比方案

### 开源框架与工具
本项目基于以下优秀的开源项目构建：

**后端框架**
- [FastAPI](https://fastapi.tiangolo.com/) - 现代化的 Python Web 框架
- [Uvicorn](https://www.uvicorn.org/) - 高性能 ASGI 服务器
- [SQLAlchemy](https://www.sqlalchemy.org/) - Python SQL 工具包和 ORM
- [Pydantic](https://docs.pydantic.dev/) - 数据验证和设置管理

**图像处理**
- [Pillow](https://python-pillow.org/) - Python 图像处理库
- [OpenCV](https://opencv.org/) - 计算机视觉库
- [NumPy](https://numpy.org/) - 科学计算基础库
- [SciPy](https://scipy.org/) - 科学计算工具

**前端框架**
- [React](https://react.dev/) - 用户界面库
- [TypeScript](https://www.typescriptlang.org/) - JavaScript 的类型超集
- [Vite](https://vitejs.dev/) - 下一代前端构建工具
- [Ant Design](https://ant.design/) - 企业级 UI 设计语言

**状态管理与工具**
- [Zustand](https://zustand-demo.pmnd.rs/) - 轻量级状态管理
- [Axios](https://axios-http.com/) - HTTP 客户端

### 特别感谢
- 所有提交 Issue 和 PR 的贡献者
- 为项目点 Star 的每一位开发者
- 开源社区的无私分享精神

---

<div align="center">
  
**Made with ❤️ by [TUNGTREE](https://github.com/TUNGTREE)**

[![⭐ Star on GitHub](https://img.shields.io/github/stars/TUNGTREE/AI-ColorTune?style=social)](https://github.com/TUNGTREE/AI-ColorTune)

</div>

