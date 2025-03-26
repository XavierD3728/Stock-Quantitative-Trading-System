from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    balance = db.Column(db.Float, default=100000.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    positions = db.relationship('Position', backref='user', lazy=True)
    trades = db.relationship('Trade', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Stock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), unique=True, nullable=False)  # 股票代码
    name = db.Column(db.String(50), nullable=False)  # 股票名称
    industry = db.Column(db.String(50))  # 所属行业
    market = db.Column(db.String(20))  # 市场类型
    last_price = db.Column(db.Float)  # 最新价格
    prev_price = db.Column(db.Float)  # 前一日价格
    last_update = db.Column(db.DateTime)  # 最后更新时间
    positions = db.relationship('Position', backref='stock', lazy=True)
    trades = db.relationship('Trade', backref='stock', lazy=True)

    @classmethod
    def get_default_stocks(cls):
        """获取默认股票列表"""
        return [
            {'code': '000001.SZ', 'name': '平安银行', 'industry': '银行', 'market': '主板', 'last_price': 10.25, 'prev_price': 10.15},
            {'code': '000002.SZ', 'name': '万科A', 'industry': '房地产', 'market': '主板', 'last_price': 15.80, 'prev_price': 15.60},
            {'code': '000063.SZ', 'name': '中兴通讯', 'industry': '通信设备', 'market': '主板', 'last_price': 28.50, 'prev_price': 28.20},
            {'code': '000066.SZ', 'name': '中国长城', 'industry': '计算机设备', 'market': '主板', 'last_price': 12.30, 'prev_price': 12.20},
            {'code': '000333.SZ', 'name': '美的集团', 'industry': '家用电器', 'market': '主板', 'last_price': 45.20, 'prev_price': 44.80},
            {'code': '000651.SZ', 'name': '格力电器', 'industry': '家用电器', 'market': '主板', 'last_price': 35.80, 'prev_price': 35.50},
            {'code': '000725.SZ', 'name': '京东方A', 'industry': '光学光电子', 'market': '主板', 'last_price': 4.25, 'prev_price': 4.20},
            {'code': '000768.SZ', 'name': '中航飞机', 'industry': '航空装备', 'market': '主板', 'last_price': 25.60, 'prev_price': 25.40},
            {'code': '000858.SZ', 'name': '五粮液', 'industry': '白酒', 'market': '主板', 'last_price': 180.50, 'prev_price': 179.80},
            {'code': '000977.SZ', 'name': '浪潮信息', 'industry': '计算机设备', 'market': '主板', 'last_price': 32.40, 'prev_price': 32.20},
            {'code': '600000.SH', 'name': '浦发银行', 'industry': '银行', 'market': '主板', 'last_price': 8.25},
            {'code': '600036.SH', 'name': '招商银行', 'industry': '银行', 'market': '主板', 'last_price': 35.80},
            {'code': '600276.SH', 'name': '恒瑞医药', 'industry': '化学制药', 'market': '主板', 'last_price': 85.60},
            {'code': '600519.SH', 'name': '贵州茅台', 'industry': '白酒', 'market': '主板', 'last_price': 1800.50},
            {'code': '600745.SH', 'name': '闻泰科技', 'industry': '半导体', 'market': '主板', 'last_price': 95.30},
            {'code': '601318.SH', 'name': '中国平安', 'industry': '保险', 'market': '主板', 'last_price': 45.20},
            {'code': '601398.SH', 'name': '工商银行', 'industry': '银行', 'market': '主板', 'last_price': 5.25},
            {'code': '601888.SH', 'name': '中国中免', 'industry': '商业贸易', 'market': '主板', 'last_price': 180.50},
            {'code': '603501.SH', 'name': '韦尔股份', 'industry': '半导体', 'market': '主板', 'last_price': 125.30},
            {'code': '688981.SH', 'name': '中芯国际', 'industry': '半导体', 'market': '科创板', 'last_price': 45.80}
        ]

class Position(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    stock_id = db.Column(db.Integer, db.ForeignKey('stock.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    average_price = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Trade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    stock_id = db.Column(db.Integer, db.ForeignKey('stock.id'), nullable=False)
    type = db.Column(db.String(4), nullable=False)  # 'BUY' or 'SELL'
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    commission = db.Column(db.Float, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class TradingStrategy(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    parameters = db.Column(db.JSON)
    is_active = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class QuantStrategy(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    stock_code = db.Column(db.String(20), nullable=False)
    ma_short = db.Column(db.Integer, nullable=False)
    ma_long = db.Column(db.Integer, nullable=False)
    momentum_days = db.Column(db.Integer, nullable=False)
    position_size = db.Column(db.Integer, nullable=False)
    position = db.Column(db.Integer, default=0)  # 当前持仓数量
    avg_price = db.Column(db.Float, default=0)  # 持仓均价
    total_profit = db.Column(db.Float, default=0)  # 累计收益
    last_trade_date = db.Column(db.Date)  # 最后交易日期
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('quant_strategies', lazy=True))
    
    def __init__(self, user_id, stock_code, ma_short, ma_long, momentum_days, position_size):
        self.user_id = user_id
        self.stock_code = stock_code
        self.ma_short = ma_short
        self.ma_long = ma_long
        self.momentum_days = momentum_days
        self.position_size = position_size
        self.position = 0
        self.avg_price = 0
        self.total_profit = 0
    
    def calculate_signal(self, prices):
        """Calculate trading signal based on moving averages and momentum"""
        if len(prices) < max(self.ma_long, self.momentum_days):
            return 0
            
        # Calculate moving averages
        ma_short_values = pd.Series(prices).rolling(window=self.ma_short).mean()
        ma_long_values = pd.Series(prices).rolling(window=self.ma_long).mean()
        
        # Calculate momentum
        momentum = (prices[-1] - prices[-self.momentum_days]) / prices[-self.momentum_days]
        
        # Generate signal
        if ma_short_values.iloc[-1] > ma_long_values.iloc[-1] and momentum > 0:
            return 1  # Buy signal
        elif ma_short_values.iloc[-1] < ma_long_values.iloc[-1] and momentum < 0:
            return -1  # Sell signal
        return 0  # Hold

    def to_dict(self):
        """Convert strategy to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'stock_code': self.stock_code,
            'ma_short': self.ma_short,
            'ma_long': self.ma_long,
            'momentum_days': self.momentum_days,
            'position_size': self.position_size,
            'position': self.position,
            'avg_price': self.avg_price,
            'total_profit': self.total_profit,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        } 