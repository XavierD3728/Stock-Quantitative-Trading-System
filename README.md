# Stock-Quantitative-Trading-System
# 股票交易模拟系统

这是一个基于 Python Flask 的股票交易模拟系统，提供实时行情展示、交易操作、持仓管理等功能。系统采用 SQLite 数据库存储用户和交易数据，支持实时更新股票价格。

## 功能特点

- 用户注册和登录
- 实时股票行情展示（包括涨跌幅）
- 股票交易（买入/卖出）
- 持仓管理和分析
- 交易记录查询
- 账户资金管理
- 数据可视化（持仓分布图表）

## 运行环境要求

- Python 3.8+
- Windows/Linux/MacOS

## 安装步骤

1. 克隆项目到本地：
```bash
git clone [项目地址]
cd [项目目录]
```

2. 创建并激活虚拟环境（推荐）：
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/MacOS
python3 -m venv venv
source venv/bin/activate
```

3. 安装依赖包：
```bash
pip install -r requirements.txt
```

4. 创建环境变量文件：
```bash
# 创建 .env 文件并添加以下内容
SECRET_KEY=your-secret-key
TUSHARE_TOKEN=your-tushare-token  # 可选，用于获取实时行情
DATABASE_URL=sqlite:///stock_trading.db
```

## 数据库配置

系统使用 SQLite 数据库，首次运行时会自动创建。如需手动初始化数据库：
```bash
# 进入 Python 交互环境
python
>>> from app import app, db
>>> with app.app_context():
...     db.create_all()
```

## 启动应用

```bash
python app.py
```
启动后访问 http://127.0.0.1:5000 即可使用系统。

## 使用说明

1. 注册/登录：
   - 首次使用需要注册账号
   - 系统会自动为新用户分配初始资金（默认 100,000 元）

2. 交易功能：
   - 在交易页面可以查看所有可交易股票
   - 选择股票后输入交易数量进行买入或卖出
   - 系统会自动计算交易费用（默认费率 0.03%）
   - 交易完成后可在持仓页面查看结果

3. 持仓管理：
   - 持仓页面显示当前持有的所有股票
   - 包括持仓数量、成本价、当前价、盈亏等信息
   - 提供持仓分布饼图可视化
   - 盈利显示红色，亏损显示绿色（符合国内交易习惯）

4. 行情更新：
   - 股票价格每 30 秒自动更新一次
   - 涨跌幅动态显示，并带有颜色标识
   - 价格变动时有闪烁效果提示

## 配置说明

可在 `config.py` 文件中修改以下配置：
```python
INITIAL_BALANCE = 100000    # 初始资金
COMMISSION_RATE = 0.0003    # 交易手续费率
MIN_TRADE_AMOUNT = 100      # 最小交易数量
MAX_TRADE_AMOUNT = 100000   # 最大交易数量
```

## 数据来源

系统支持两种数据来源：
1. Tushare API（需配置 token）
2. 内置默认数据（无需配置，但不是实时数据）

## 注意事项

1. 这是一个模拟交易系统，不支持真实交易
2. 为了更好的体验，建议配置 Tushare token
3. 所有交易数据仅供学习和研究使用
4. 系统默认使用 SQLite 数据库，如需使用其他数据库请修改配置

## 常见问题

1. 数据库初始化失败：
   - 检查数据库文件权限
   - 确保路径可写入

2. 无法获取实时数据：
   - 检查网络连接
   - 验证 Tushare token 是否有效
   - 系统会自动切换到默认数据

3. 交易失败：
   - 检查账户余额是否充足
   - 确认交易数量是否在允许范围内
   - 查看具体错误提示

## 技术栈

- 后端：Python Flask
- 前端：HTML, CSS, JavaScript, Bootstrap
- 数据库：SQLite
- 数据可视化：ECharts
- 股票数据：Tushare API（可选）

## 贡献指南

欢迎提交 Issue 和 Pull Request 来帮助改进项目。

## 许可证

MIT License 
