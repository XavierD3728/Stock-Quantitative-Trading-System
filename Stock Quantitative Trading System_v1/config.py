import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-please-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///stock_trading.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TUSHARE_TOKEN = os.environ.get('TUSHARE_TOKEN')
    
    # 会话配置
    PERMANENT_SESSION_LIFETIME = timedelta(days=31)  # 会话持续31天
    REMEMBER_COOKIE_DURATION = timedelta(days=31)    # Remember Me cookie持续31天
    REMEMBER_COOKIE_SECURE = False                   # 开发环境下不要求HTTPS
    REMEMBER_COOKIE_HTTPONLY = True                 # 防止JavaScript访问cookie
    
    # 交易相关配置
    INITIAL_BALANCE = 100000  # 初始资金
    COMMISSION_RATE = 0.0003  # 手续费率
    MIN_TRADE_AMOUNT = 1      # 最小交易数量
    MAX_TRADE_AMOUNT = 100000 # 最大交易数量 