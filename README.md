# GraphGen 🚀

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![Vue 3](https://img.shields.io/badge/Vue-3-4FC08D.svg)](https://vuejs.org/)

> **智能知识图谱生成平台** - 从文档到问答对，一键生成高质量训练数据

GraphGen 是一个企业级的知识图谱生成工具，能够从各种数据源自动构建高质量的知识图谱，并生成相应的问答对用于训练大语言模型。支持多用户协作、权限管理、数据审核等企业级功能。

## ✨ 核心特性

### 🔐 企业级权限管理
- **角色分离**：管理员负责任务管理，审核员专注数据审核
- **安全认证**：JWT Token 认证，支持用户管理
- **权限控制**：细粒度权限控制，确保数据安全

### 📊 智能任务管理
- **多文件支持**：单任务支持多个文件上传
- **实时监控**：任务状态实时追踪，进度可视化
- **断点续传**：任务中断后可继续执行
- **批量操作**：支持批量任务管理

### 🔍 数据质量保障
- **人工审核**：支持逐条数据审核和标记
- **AI 自动审核**：基于大模型的智能审核
- **批量审核**：支持批量审核操作
- **审核统计**：详细的审核统计和报告

### 🎨 现代化界面
- **响应式设计**：支持桌面和移动端
- **直观操作**：拖拽上传、一键操作
- **实时反馈**：操作结果实时提示
- **多语言支持**：中英文界面切换

### 🚀 高性能架构
- **异步处理**：FastAPI 异步架构，高并发支持
- **微服务设计**：前后端分离，易于扩展
- **RESTful API**：标准化 API 接口
- **容器化部署**：支持 Docker 部署

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

- **多数据源支持**: 支持文本、PDF、CSV、JSON 等多种格式
- **智能知识图谱构建**: 自动提取实体、关系和属性
- **多种输出格式**: 支持 Alpaca、ShareGPT、ChatML 等格式
- **Web 界面**: 提供直观的 Web 界面进行交互
- **API 接口**: 提供 RESTful API 供程序调用
- **任务管理**: 支持任务创建、监控、下载等完整生命周期

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

## 📊 性能优化

- **并行处理**: 支持多线程并行处理
- **内存管理**: 智能内存使用，支持大文件处理
- **缓存机制**: 内置缓存系统，提高处理效率
- **增量更新**: 支持增量更新知识图谱

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

感谢所有为 GraphGen 项目做出贡献的开发者和用户！

## 📞 支持

如果您遇到问题或有任何建议，请：

- 提交 Issue
- 发送邮件至项目维护者
- 查看文档和 FAQ
