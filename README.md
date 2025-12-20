# 校园餐饮管理系统

## 项目概述
这是一个基于Flask框架的校园餐饮管理系统，主要功能包括：
- 用户注册、登录和身份验证
- 食品信息查询和分类浏览
- 管理员后台权限管理
- 档口信息展示和评价功能
- 自动化评分和招牌菜更新

项目采用前后端分离架构，使用Vue.js构建前端界面，Flask处理后端逻辑。

## 项目结构
```
webProject/
├── backend/         # Flask后端代码
│   ├── Database.py # 数据库连接池和分布式锁
│   ├── portal.py   # 主入口、路由处理及静态资源托管
│   ├── scheduler.py # 定时任务调度器（评分/招牌菜更新）
│   └── api/        # 业务逻辑模块
│       ├── food.py  # 前台食品相关API
│       ├── user.py  # 前台用户相关API
│       └── background/ # 后台管理API
│           ├── admin.py       # 管理员认证
│           ├── adminManage.py # 管理员账号管理
│           ├── dish.py        # 菜品管理
│           ├── food.py        # 档口管理
│           └── user.py        # 用户管理（冻结/解冻）
├── frontend/       # Vue前端应用
├── doc/            # 文档
│   ├── requirements.txt
│   ├── webAPI/      # API接口文档
│   └── database/   # 数据库设计文档
├── imgRepo/        # 图片存储
└── tests/          # 测试脚本
```

## 技术栈
- **后端**: Python 3.x, Flask, JWT
- **数据库**: MySQL
- **缓存**: Redis（用于分布式锁）
- **前端**: Vue.js 
- **工具**: Redis分布式锁, Asyncio (任务调度)

## 主要功能模块
### 1. 用户认证
- 用户注册/登录
- Token生成与验证
- 密码加密存储

### 2. 食品信息
- 档口列表查询
- 食品分类展示
- 价格和评分排序

### 3. 后台管理
- **管理员管理**: 登录、权限验证、账号增删改查
- **用户管理**: 用户列表查询、账号冻结/解冻、重置密码
- **餐饮管理**: 档口及菜品的增删改查
- **数据维护**: 手动触发评分更新

### 4. 自动化任务
- **定时调度**: 每日自动更新店铺评分和招牌菜品（默认 00:00）
- **手动触发**: 支持管理员手动触发更新任务

## 运行指南
1. 安装依赖
```bash
pip install -r doc/requirements.txt
```

2. 配置数据库
- 创建MySQL数据库
- 修改`Database.py`中的连接配置
- (可选) 在`.env`中配置定时任务时间 `SCHEDULE_TIME=00:00`

3. 启动后端服务器
```bash
# 启动Flask应用（会自动启动定时任务调度器）
python backend/portal.py
```

4. 启动前端应用
```bash
cd frontend
npm install
npm run dev
```

## API文档
详见 `doc/webAPI/` 目录下的文档文件

## 贡献指南
1. 克隆仓库
```bash
git clone https://github.com/your-repo/campus-dining-system.git
```

2. 创建新分支
```bash
git checkout -b feature/your-feature
```

3. 提交代码并推送
```bash
git add .
git commit -m "Add your feature"
git push origin feature/your-feature
```

4. 创建Pull Request

## 许可证
MIT License