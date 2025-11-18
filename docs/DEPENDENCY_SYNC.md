# 依赖同步说明

## 概述

本项目的依赖管理使用两个文件：
- `environment.yml` - Conda 环境配置（推荐使用）
- `requirements.txt` - Python 标准依赖文件（作为备选）

## 依赖对应关系

### environment.yml 独有
- `nodejs>=16` - Node.js 运行环境
- `npm` - Node.js 包管理器
- `git`, `curl`, `wget` - 系统工具
- `build-essential` - 编译工具链

### requirements.txt 独有
- 无

### 共同依赖（已同步）

#### 核心依赖
- `tqdm` - 进度条
- `openai` - OpenAI API 客户端
- `python-dotenv` - 环境变量管理
- `numpy` - 数值计算
- `networkx` - 图分析
- `tiktoken` - Token 计算
- `wikipedia` - 维基百科 API
- `tenacity` - 重试机制

#### 自然语言处理
- `nltk` - 自然语言处理工具包
- `jieba` - 中文分词
- `trafilatura` - 网页内容提取

#### 数据可视化
- `pyecharts` - 交互式图表
- `plotly` - 交互式可视化
- `kaleido` - 静态图表导出
- `matplotlib` - 数据可视化

#### 数据处理
- `pandas` - 数据分析
- `pyyaml` - YAML 解析
- `langcodes` - 语言代码

#### Web 框架
- `fastapi>=0.104.0` - 现代 Web 框架
- `uvicorn[standard]>=0.24.0` - ASGI 服务器
- `python-multipart>=0.0.6` - 多部分表单支持
- `pydantic-settings>=2.0.0` - 设置管理

#### 身份验证
- `python-jose[cryptography]` - JWT 令牌处理
- `passlib[bcrypt]` - 密码哈希

#### 图算法
- `leidenalg` - Leiden 社区检测算法
- `igraph` - 图分析库
- `python-louvain` - Louvain 社区检测算法

#### GUI
- `gradio>=5.44.1` - Web 界面构建

#### HTTP 客户端
- `requests` - HTTP 请求库

## 安装说明

### 方式 1: 使用 Conda（推荐）

```bash
# 创建并激活环境
conda env create -f environment.yml
conda activate graphgen

# 在项目目录下
cd GraphGen
```

### 方式 2: 使用 pip

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 注意：需要手动安装 nodejs
# 在 Linux/Mac:
# - 使用 nvm: nvm install 16
# - 使用包管理器: sudo apt install nodejs
```

## 同步策略

### 基本原则

1. **environment.yml** 是主配置文件
   - 包含所有系统级依赖
   - 包含 Python 包版本约束
   - 同步更新后，更新 `requirements.txt`

2. **requirements.txt** 是备选配置
   - 仅包含 Python 包
   - 保持与 `environment.yml` 中的 pip 部分同步
   - 用于纯 Python 环境安装

### 更新流程

1. 在 `environment.yml` 添加/更新依赖
2. 运行同步脚本（如果存在）或手动更新 `requirements.txt`
3. 测试安装以确保兼容性

## 版本说明

### FastAPI 相关
- `fastapi>=0.104.0` - 需要支持最新特性
- `uvicorn[standard]>=0.24.0` - 标准版本包含额外功能
- `python-multipart>=0.0.6` - 文件上传支持
- `pydantic-settings>=2.0.0` - 新版本设置管理

### Gradio
- `gradio>=5.44.1` - 需要 WebUI 新特性

### 身份验证
- `python-jose[cryptography]` - JWT 加密支持
- `passlib[bcrypt]` - Bcrypt 哈希算法

## 故障排除

### 常见问题

1. **Node.js 缺失**
   ```bash
   # 使用 conda 安装
   conda install nodejs
   
   # 或使用 nvm
   nvm install 16
   ```

2. **编译错误**
   ```bash
   # 确保 build-essential 已安装
   conda install build-essential
   ```

3. **Git 依赖缺失**
   ```bash
   conda install git
   ```

4. **网络问题**
   ```bash
   # 使用国内镜像（如需）
   conda config --add channels conda-forge
   conda config --add channels defaults
   ```

## 依赖审计

### 最后更新
- **日期**: 2025-10-27
- **Python 版本**: 3.10
- **Node.js 版本**: >=16

### 安全检查
定期更新依赖以获取安全补丁：
```bash
# Conda
conda update --all

# Pip
pip list --outdated
pip install --upgrade package_name
```

## 相关文件

- `environment.yml` - Conda 环境配置
- `requirements.txt` - Python 依赖列表
- `package.json` - 前端依赖（如果存在）
