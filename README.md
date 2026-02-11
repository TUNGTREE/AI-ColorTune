# ColorTune - AI驱动的专业调色工具

<div align="center">
  <h3>🎨 智能调色 | 🤖 AI驱动 | 🎯 个性化建议</h3>
  <p>基于用户风格学习的专业照片调色系统</p>
</div>

---

## ✨ 核心特性

### 🎯 **智能风格发现**
- 通过多轮测试学习用户的调色偏好
- AI 分析用户选择，生成个性化风格档案
- 12 种预设示例场景（城市/自然/室内/人像 × 日间/夜间/日落）

### 🤖 **AI 调色建议**
- 结合用户风格档案生成个性化调色方案
- 支持多种 AI 模型（Claude、GPT-4、通义千问等）
- 实时预览调色效果

### 🎚️ **专业参数调整**
- 16 种图像调整算法（曝光、对比度、色温、HSL 等）
- 实时预览（CSS Filter + 服务端精确渲染）
- 完整的色调曲线和分通道调整

### 🌙 **专业暗色主题**
- 参考 Lightroom/DaVinci Resolve 的专业 UI 设计
- 暗色背景减少眼睛疲劳，更准确判断色彩
- 全宽自适应布局

---

## 🏗️ 技术架构

### **后端技术栈**
- **FastAPI** - 现代异步 Python Web 框架
- **SQLAlchemy** - ORM 数据库管理
- **Pillow + OpenCV** - 专业图像处理
- **Anthropic + OpenAI SDK** - 多模型 AI 支持

### **前端技术栈**
- **React 18 + TypeScript** - 类型安全的现代前端
- **Ant Design** - 企业级 UI 组件库
- **Zustand** - 轻量级状态管理
- **Vite** - 快速构建工具

### **AI 模型支持**
- ✅ Claude (Anthropic)
- ✅ GPT-4 Vision (OpenAI)
- ✅ 通义千问 VL (阿里云)
- ✅ 任意 OpenAI 兼容接口

---

## 🚀 快速开始

### **前置要求**
- Python 3.10+
- Node.js 18+
- AI API Key（Claude / OpenAI / 阿里云 DashScope 任选其一）

### **1. 克隆仓库**
```bash
git clone https://github.com/TUNGTREE/AI-ColorTune.git
cd AI-ColorTune
```

### **2. 后端设置**
```bash
cd backend

# 创建虚拟环境
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
copy .env.example .env
# 编辑 .env 填入你的 API Key

# 启动后端
uvicorn app.main:app --reload --port 8000
```

### **3. 前端设置**
```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### **4. 访问应用**
打开浏览器访问：`http://localhost:5173`

---

## 📖 使用指南

### **步骤 1：配置 AI**
点击右上角 **"AI 设置"** 按钮，配置你的 AI 提供商：

```yaml
# 示例：使用阿里云通义千问
提供商: OpenAI-compatible
API Key: sk-your-dashscope-key
Base URL: https://dashscope.aliyuncs.com/compatible-mode/v1
Model: qwen-vl-plus
```

### **步骤 2：风格发现**
1. 点击示例场景开始测试
2. 从 4 个调色风格中选择你喜欢的
3. 重复 3+ 轮测试
4. AI 自动分析生成你的风格档案

### **步骤 3：调色建议**
1. 上传待调色照片
2. AI 根据你的风格档案生成 3 个调色建议
3. 对比预览选择最满意的

### **步骤 4：参数微调**
1. 使用滑块微调参数（曝光、对比度、色温等）
2. 实时预览效果
3. 满意后进入导出

### **步骤 5：导出**
选择格式（JPEG/PNG/TIFF）和质量，导出全分辨率调色照片

---

## 🎨 调色参数说明

### **基础参数**
- **曝光 (Exposure)** - 整体亮度调整（EV 值）
- **对比度 (Contrast)** - 明暗对比强度
- **高光/阴影 (Highlights/Shadows)** - 选择性亮度调整
- **白色/黑色 (Whites/Blacks)** - 色阶端点控制

### **色彩调整**
- **色温 (Temperature)** - 冷暖色调（蓝↔橙）
- **色调 (Tint)** - 绿↔品红偏移
- **自然饱和度 (Vibrance)** - 选择性饱和度增强
- **饱和度 (Saturation)** - 全局饱和度

### **HSL 分通道**
独立调整 8 个色相通道（红、橙、黄、绿、青、蓝、紫、品红）的色相/饱和度/亮度

### **特效**
- **清晰度 (Clarity)** - 中频细节增强
- **去雾 (Dehaze)** - 去除雾霾提升通透感
- **暗角 (Vignette)** - 边缘压暗
- **颗粒 (Grain)** - 胶片质感

---

## 🧪 测试

后端包含 **101 个单元测试**，覆盖：
- 图像处理算法
- AI 服务集成
- API 端点
- 端到端用户流程

```bash
cd backend
pytest
```

---

## 📂 项目结构

```
colortune/
├── backend/                  # FastAPI 后端
│   ├── app/
│   │   ├── api/             # API 路由
│   │   ├── core/            # 核心算法（图像处理、AI 提示词）
│   │   ├── models/          # 数据库模型
│   │   ├── schemas/         # Pydantic 模型
│   │   └── services/        # 业务逻辑
│   ├── tests/               # 101 个单元测试
│   └── requirements.txt
├── frontend/                 # React 前端
│   └── src/
│       ├── components/      # UI 组件
│       ├── stores/          # 状态管理
│       └── api/             # API 客户端
└── README.md
```

---

## 🔐 安全说明

- ⚠️ `.env` 文件包含敏感信息（API Key），**永远不要提交到 Git**
- ✅ 项目已配置 `.gitignore` 自动排除 `.env`
- ✅ API Key 仅存储在后端，前端无法访问
- ✅ 用户上传的图片存储在本地 `uploads/` 目录（不上传到云端）

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

## 📄 许可证

MIT License

---

## 🙏 致谢

- [Anthropic Claude](https://www.anthropic.com/) - AI 视觉理解
- [OpenAI](https://openai.com/) - GPT-4 Vision
- [阿里云通义千问](https://dashscope.aliyun.com/) - 视觉语言模型
- [FastAPI](https://fastapi.tiangolo.com/) - 现代 Python Web 框架
- [Ant Design](https://ant.design/) - 企业级 UI 组件

---

<div align="center">
  <p>Made with ❤️ by TUNGTREE</p>
  <p>⭐ 如果这个项目对你有帮助，请给个 Star！</p>
</div>
