# GraphGen 🚀

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![Vue 3](https://img.shields.io/badge/Vue-3-4FC08D.svg)](https://vuejs.org/)

> **知识图谱生成平台** - 从文档到问答对，生成训练数据

本项目基于 [GraphGen](https://github.com/HKUDS/GraphGen) 开发，是一个知识图谱生成工具，能够从文档数据源构建知识图谱，并生成相应的问答对用于训练大语言模型。提供了 Web 界面、用户权限管理、数据审核等功能。

## ✨ 核心特性

### 🔐 用户权限管理
- **角色分离**：管理员负责任务管理，审核员专注数据审核
- **安全认证**：JWT Token 认证，支持用户管理
- **权限控制**：基本的权限控制功能

### 📊 任务管理
- **多文件支持**：单任务支持多个文件上传
- **状态监控**：任务状态追踪
- **断点续传**：任务中断后可继续执行

### 🔍 数据审核
- **人工审核**：支持逐条数据审核和标记
- **自动审核**：基于大模型的自动审核（实验性功能）
- **批量审核**：支持批量审核操作
- **审核统计**：基本的审核统计信息

### 🎨 Web 界面
- **响应式设计**：支持桌面端访问
- **直观操作**：文件上传、任务管理
- **实时反馈**：操作结果提示

### 🚀 技术架构
- **异步处理**：FastAPI 异步架构
- **前后端分离**：Vue 3 前端 + FastAPI 后端
- **RESTful API**：标准化 API 接口

## 🚀 快速开始

### 使用 Conda 环境 (推荐)

1. **创建环境**
   ```bash
   conda env create -f environment.yml
   conda activate graphgen
   ```

2. **启动服务**
   ```bash
   ./start.sh start
   ```

3. **访问界面**
   - Vue 前端: http://localhost:3000
   - Gradio Web UI: http://localhost:7860
   - FastAPI 后端: http://localhost:8000
   - API 文档: http://localhost:8000/docs

4. **登录系统**
   
   **默认管理员账户**：
   - 用户名：`admin`
   - 密码：`admin123`
   
   **默认审核员账户**：
   - 用户名：`reviewer`
   - 密码：`reviewer123`
   
   ⚠️ **首次登录后请立即修改密码！**

### CLI 使用

```bash
# 激活环境
conda activate graphgen

# 运行 GraphGen
python graphgen_cli.py --input_file data/example_input.txt --output_dir tasks/outputs
```

## 📁 项目结构

```
GraphGen/
├── backend/           # FastAPI 后端服务
├── frontend/          # Vue 3 前端应用
├── webui/            # Gradio Web UI
├── graphgen/         # 核心 GraphGen 库
├── baselines/        # 基线方法实现
├── scripts/          # 脚本文件
├── resources/        # 资源文件
├── data/            # 示例数据
└── tasks/           # 任务输出目录
```

## 🎯 功能特性

- **多数据源支持**: 支持文本、PDF、CSV、JSON 等格式
- **知识图谱构建**: 基于 GraphGen 核心库，提取实体、关系和属性
- **多种输出格式**: 支持 Alpaca、ShareGPT、ChatML 等格式
- **Web 界面**: 提供 Web 界面进行交互
- **API 接口**: 提供 RESTful API 供程序调用
- **任务管理**: 支持任务创建、监控、下载等功能

## 🛠️ 使用说明

### Web UI 使用

1. **启动服务**: `./start.sh start`
2. **访问界面**: 打开 http://localhost:7860
3. **上传文件**: 选择要处理的数据文件
4. **配置参数**: 设置模型参数和生成选项
5. **开始生成**: 点击开始按钮，等待处理完成
6. **下载结果**: 处理完成后下载生成的数据

### API 使用

```python
import requests

# 创建任务
response = requests.post("http://localhost:8000/api/tasks", json={
    "name": "测试任务",
    "input_file": "example.txt",
    "config": {
        "output_data_type": "aggregated",
        "output_data_format": "Alpaca"
    }
})

task_id = response.json()["task_id"]

# 查询任务状态
status = requests.get(f"http://localhost:8000/api/tasks/{task_id}")

# 下载结果
result = requests.get(f"http://localhost:8000/api/tasks/{task_id}/download")
```

## ⚙️ 配置说明

### 环境变量

创建 `.env` 文件：

```env
# 大模型配置
SYNTHESIZER_MODEL=gpt-3.5-turbo
SYNTHESIZER_API_KEY=your-api-key
SYNTHESIZER_BASE_URL=https://api.openai.com/v1

# 服务器配置
HOST=0.0.0.0
PORT=8000
DEBUG=False
```

## 📊 技术说明

- **并行处理**: 支持多线程并行处理
- **内存管理**: 基本的内存管理，支持中等规模文件处理
- **缓存机制**: 使用缓存系统提高处理效率

## 🧪 开发指南

### 本地开发

```bash
# 克隆项目
git clone <repository-url>
cd GraphGen

# 创建环境
conda env create -f environment.yml
conda activate graphgen

# 安装前端依赖
cd frontend
npm install
cd ..

# 启动开发服务
./start.sh start
```

## 📚 文档

- [GraphGen框架详细解析](docs/FRAMEWORK_ANALYSIS.md) - 框架四步工作流程、技术实现细节、代码对应关系
- [认证系统使用指南](docs/AUTH_GUIDE.md) - 用户登录、权限管理、角色说明
- [数据审核功能指南](docs/REVIEW_GUIDE.md) - 人工审核、自动审核、批量操作
- [任务故障排查指南](docs/TASK_TROUBLESHOOTING.md) - 常见问题和解决方案

## 🤝 贡献

欢迎贡献代码！请遵循以下步骤：

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

本项目基于 [GraphGen](https://github.com/HKUDS/GraphGen) 开发，感谢 GraphGen 项目提供的核心知识图谱生成能力。
