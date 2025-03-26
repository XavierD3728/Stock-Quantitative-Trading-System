from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import tushare as ts
import pandas as pd
from datetime import datetime, timedelta
import json
from dotenv import load_dotenv
import os
import threading
import time
import random
from flask_migrate import Migrate
from threading import Thread

from config import Config
from database import db, User, Stock, Position, Trade, TradingStrategy, QuantStrategy

# 加载环境变量
load_dotenv()

app = Flask(__name__)
app.config.from_object(Config)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///stock_trading.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# 添加会话配置
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)  # 会话有效期7天
app.config['SESSION_COOKIE_SECURE'] = False  # 开发环境设为False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# 初始化扩展
db.init_app(app)
migrate = Migrate(app, db)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# 初始化Tushare
ts.set_token(os.getenv('TUSHARE_TOKEN'))
pro = ts.pro_api()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def init_stock_data():
    """初始化股票数据"""
    try:
        print("开始初始化股票数据...")
        
        # 尝试从Tushare获取数据
        try:
            stocks = pro.stock_basic(exchange='', list_status='L')
            print(f"从Tushare获取到 {len(stocks)} 只股票")
            
            # 获取最新交易日
            today = datetime.now().strftime('%Y%m%d')
            trade_date = pro.trade_cal(exchange='SSE', is_open=1, end_date=today, limit=1).iloc[0]['cal_date']
            
            # 获取最新行情数据
            price_df = pro.daily(trade_date=trade_date)
            
            # 批量处理股票数据
            for _, row in stocks.iterrows():
                try:
                    # 检查股票是否已存在
                    stock = Stock.query.filter_by(code=row['ts_code']).first()
                    if not stock:
                        stock = Stock(
                            code=row['ts_code'],
                            name=row['name'],
                            industry=row['industry'],
                            market=row['market'],
                            last_price=0.0,
                            prev_price=0.0
                        )
                        db.session.add(stock)
                    
                    # 更新最新价格
                    if price_df is not None and not price_df.empty:
                        stock_price = price_df[price_df['ts_code'] == row['ts_code']]
                        if not stock_price.empty:
                            stock.last_price = float(stock_price.iloc[0]['close'])
                            stock.prev_price = float(stock_price.iloc[0]['pre_close'])
                            stock.last_update = datetime.now()
                    
                except Exception as e:
                    print(f"处理股票 {row['ts_code']} 时出错: {str(e)}")
                    continue
            
            db.session.commit()
            print("从Tushare获取的股票数据初始化完成")
            
        except Exception as e:
            print(f"从Tushare获取数据失败: {str(e)}")
            print("使用默认股票数据...")
            
            # 使用默认数据
            default_stocks = Stock.get_default_stocks()
            for stock_data in default_stocks:
                try:
                    stock = Stock.query.filter_by(code=stock_data['code']).first()
                    if not stock:
                        stock = Stock(
                            code=stock_data['code'],
                            name=stock_data['name'],
                            industry=stock_data['industry'],
                            market=stock_data['market'],
                            last_price=stock_data['last_price'],
                            prev_price=stock_data['prev_price'],
                            last_update=datetime.now()
                        )
                        db.session.add(stock)
                except Exception as e:
                    print(f"添加默认股票 {stock_data['code']} 时出错: {str(e)}")
                    continue
            
            db.session.commit()
            print("默认股票数据初始化完成")
        
    except Exception as e:
        print(f"初始化股票数据时出错: {str(e)}")
        db.session.rollback()

def update_stock_prices():
    """定期更新股票价格的函数"""
    while True:
        try:
            with app.app_context():
                print("开始更新股票价格...")
                stocks = Stock.query.all()
                
                # 检查是否是新的交易日
                now = datetime.now()
                is_new_trading_day = now.hour == 9 and now.minute == 30  # 假设每天9:30开盘
                
                for stock in stocks:
                    try:
                        # 如果是新的交易日，更新prev_price为昨日收盘价
                        if is_new_trading_day:
                            stock.prev_price = stock.last_price
                        
                        # 模拟价格波动（-2% 到 +2% 之间的随机波动）
                        price_change = random.uniform(-0.02, 0.02)
                        new_price = stock.last_price * (1 + price_change)
                        stock.last_price = round(new_price, 2)
                        
                        # 计算涨跌幅
                        if stock.prev_price > 0:  # 防止除以0
                            change_percent = ((stock.last_price - stock.prev_price) / stock.prev_price) * 100
                            print(f"更新股票 {stock.code} 价格: {stock.last_price} (变动: {change_percent:.2f}%)")
                        else:
                            stock.prev_price = stock.last_price  # 如果没有前收盘价，使用当前价格
                            print(f"更新股票 {stock.code} 价格: {stock.last_price}")
                            
                    except Exception as e:
                        print(f"更新股票 {stock.code} 价格失败: {str(e)}")
                        continue
                
                db.session.commit()
                print("股票价格更新完成")
        except Exception as e:
            print(f"更新股票价格时发生错误: {str(e)}")
        time.sleep(30)  # 每30秒更新一次

@app.before_first_request
def create_tables():
    """创建数据库表"""
    with app.app_context():
        db.create_all()
        init_stock_data()

@app.before_first_request
def start_price_updater():
    """启动价格更新线程"""
    with app.app_context():  # 添加应用上下文
        price_updater = threading.Thread(target=update_stock_prices, daemon=True)
        price_updater.start()

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash('用户名已存在')
            return redirect(url_for('register'))
        
        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('注册成功，请登录')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user, remember=True)
            session.permanent = True  # 设置会话为永久性
            return redirect(url_for('dashboard'))
        flash('用户名或密码错误')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    positions = Position.query.filter_by(user_id=current_user.id).all()
    
    # 计算总持仓市值和总盈亏
    total_position_value = 0
    total_profit = 0
    position_details = []
    
    for position in positions:
        market_value = position.quantity * position.stock.last_price
        profit = position.quantity * (position.stock.last_price - position.average_price)
        total_position_value += market_value
        total_profit += profit
        
        position_details.append({
            'code': position.stock.code,
            'name': position.stock.name,
            'quantity': position.quantity,
            'average_price': position.average_price,
            'current_price': position.stock.last_price,
            'market_value': market_value,
            'profit': profit,
            'profit_color': 'text-danger' if profit > 0 else 'text-success'
        })
    
    return render_template('dashboard.html',
                         balance=current_user.balance,
                         total_position_value=total_position_value,
                         total_profit=total_profit,
                         positions=position_details,
                         profit_color='text-danger' if total_profit > 0 else 'text-success')

@app.route('/trade', methods=['GET', 'POST'])
@login_required
def trade():
    if request.method == 'POST':
        stock_code = request.form.get('stock_code')
        quantity = int(request.form.get('quantity'))
        trade_type = request.form.get('type')
        
        stock = Stock.query.filter_by(code=stock_code).first()
        if not stock:
            flash('股票代码不存在', 'danger')
            return redirect(url_for('trade'))
        
        # 更新股票价格
        try:
            price_data = pro.daily(ts_code=stock_code, start_date=(datetime.now() - timedelta(days=1)).strftime('%Y%m%d'))
            if not price_data.empty:
                stock.last_price = float(price_data.iloc[0]['close'])
                db.session.commit()
        except Exception as e:
            print(f"更新股票价格时出错: {str(e)}")
        
        total_amount = quantity * stock.last_price
        commission = total_amount * app.config['COMMISSION_RATE']
        
        if trade_type == 'buy':
            # 检查余额是否足够
            if current_user.balance < total_amount + commission:
                flash('余额不足', 'danger')
                return redirect(url_for('trade'))
            
            # 创建交易记录
            trade = Trade(
                user_id=current_user.id,
                stock_id=stock.id,
                type='BUY',
                quantity=quantity,
                price=stock.last_price,
                commission=commission,
                total_amount=total_amount
            )
            db.session.add(trade)
            
            # 更新用户余额
            current_user.balance -= (total_amount + commission)
            
            # 更新或创建持仓
            position = Position.query.filter_by(user_id=current_user.id, stock_id=stock.id).first()
            if position:
                # 计算新的平均成本
                total_cost = position.average_price * position.quantity + total_amount
                position.quantity += quantity
                position.average_price = total_cost / position.quantity
            else:
                position = Position(
                    user_id=current_user.id,
                    stock_id=stock.id,
                    quantity=quantity,
                    average_price=stock.last_price
                )
                db.session.add(position)
            
            flash(f'成功买入 {quantity} 股 {stock.name}', 'success')
            
        elif trade_type == 'sell':
            # 检查持仓是否足够
            position = Position.query.filter_by(user_id=current_user.id, stock_id=stock.id).first()
            if not position or position.quantity < quantity:
                flash('持仓不足', 'danger')
                return redirect(url_for('trade'))
            
            # 创建交易记录
            trade = Trade(
                user_id=current_user.id,
                stock_id=stock.id,
                type='SELL',
                quantity=quantity,
                price=stock.last_price,
                commission=commission,
                total_amount=total_amount
            )
            db.session.add(trade)
            
            # 更新用户余额
            current_user.balance += (total_amount - commission)
            
            # 更新持仓
            position.quantity -= quantity
            if position.quantity == 0:
                db.session.delete(position)
            
            flash(f'成功卖出 {quantity} 股 {stock.name}', 'success')
        
        db.session.commit()
        return redirect(url_for('positions'))
    
    stocks = Stock.query.all()
    positions = Position.query.filter_by(user_id=current_user.id).all()
    total_position_value = sum(p.quantity * p.stock.last_price for p in positions)
    total_profit = sum(p.quantity * (p.stock.last_price - p.average_price) for p in positions)
    
    return render_template('trade.html',
                         stocks=stocks,
                         positions=positions,
                         balance=current_user.balance,
                         total_position_value=total_position_value,
                         total_profit=total_profit)

@app.route('/positions')
@login_required
def positions():
    positions = Position.query.filter_by(user_id=current_user.id).all()
    
    # 计算总持仓市值和总盈亏
    total_position_value = sum(position.quantity * position.stock.last_price for position in positions)
    total_profit = sum(position.quantity * (position.stock.last_price - position.average_price) for position in positions)
    
    return render_template('positions.html',
                         positions=positions,
                         total_position_value=total_position_value,
                         total_profit=total_profit,
                         balance=current_user.balance)

@app.route('/api/stock/<code>')
@login_required
def get_stock_price(code):
    try:
        stock = Stock.query.filter_by(code=code).first()
        if not stock:
            return jsonify({'error': '股票不存在'}), 404
        
        # 更新股票价格
        price_data = pro.daily(ts_code=code, start_date=(datetime.now() - timedelta(days=1)).strftime('%Y%m%d'))
        if not price_data.empty:
            stock.last_price = price_data.iloc[0]['close']
            db.session.commit()
        
        return jsonify({
            'code': stock.code,
            'name': stock.name,
            'price': stock.last_price
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stock/<code>/price')
@login_required
def get_stock_price_real_time(code):
    """获取股票实时价格的API"""
    try:
        stock = Stock.query.filter_by(code=code).first()
        if stock:
            # 确保有前收盘价
            if not stock.prev_price:
                stock.prev_price = stock.last_price
                db.session.commit()
            
            # 计算涨跌幅
            change = ((stock.last_price - stock.prev_price) / stock.prev_price) * 100 if stock.prev_price > 0 else 0.0
            
            return jsonify({
                'code': stock.code,
                'name': stock.name,
                'price': stock.last_price,
                'prev_price': stock.prev_price,
                'change': round(change, 2),
                'industry': stock.industry
            })
        return jsonify({'error': 'Stock not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/positions/update')
@login_required
def update_positions():
    """更新持仓信息的API"""
    try:
        positions = Position.query.filter_by(user_id=current_user.id).all()
        total_position_value = 0
        total_profit = 0
        
        for position in positions:
            market_value = position.quantity * position.stock.last_price
            profit = position.quantity * (position.stock.last_price - position.average_price)
            total_position_value += market_value
            total_profit += profit
        
        return jsonify({
            'total_position_value': total_position_value,
            'total_profit': total_profit,
            'balance': current_user.balance,
            'profit_color': 'text-danger' if total_profit > 0 else 'text-success'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/quant')
@login_required
def quant():
    """Quantitative trading interface"""
    stocks = Stock.query.all()
    strategies = QuantStrategy.query.filter_by(user_id=current_user.id).all()
    
    # 获取今日日期
    today = datetime.now().date()
    
    # 获取今日交易记录
    today_trades = Trade.query.filter(
        Trade.user_id == current_user.id,
        Trade.created_at >= today
    ).count()
    
    # 计算活跃策略数量
    active_strategies = sum(1 for s in strategies if s.is_active)
    
    # 计算总收益
    total_profit = sum(s.total_profit for s in strategies)
    
    # 获取最近7天的日期
    dates = [(today - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(6, -1, -1)]
    
    # 准备每个策略的收益数据
    profits = []
    for strategy in strategies:
        # 获取该策略最近7天的交易记录
        strategy_profits = []
        cumulative_profit = 0
        for date in dates:
            date_obj = datetime.strptime(date, '%Y-%m-%d').date()
            next_date = date_obj + timedelta(days=1)
            
            # 获取当天的交易记录
            day_trades = Trade.query.filter(
                Trade.user_id == current_user.id,
                Trade.stock_id == Stock.query.filter_by(code=strategy.stock_code).first().id,
                Trade.created_at >= date_obj,
                Trade.created_at < next_date
            ).all()
            
            # 计算当天的收益
            day_profit = sum(
                trade.quantity * (trade.price - trade.commission/trade.quantity)
                if trade.type == 'SELL'
                else -trade.quantity * (trade.price + trade.commission/trade.quantity)
                for trade in day_trades
            )
            
            cumulative_profit += day_profit
            strategy_profits.append(cumulative_profit)
        
        profits.append(strategy_profits)
    
    # 准备策略数据
    strategy_data = []
    for strategy in strategies:
        stock = Stock.query.filter_by(code=strategy.stock_code).first()
        if stock:
            # 通过stock_id查询持仓
            position = Position.query.filter_by(
                user_id=current_user.id,
                stock_id=stock.id
            ).first()
            
            strategy_info = {
                'id': strategy.id,
                'stock_code': strategy.stock_code,
                'stock_name': stock.name,
                'position': position.quantity if position else 0,
                'avg_price': position.average_price if position else 0,
                'current_price': stock.last_price,
                'total_profit': strategy.total_profit,
                'profit_rate': ((stock.last_price / position.average_price) - 1) * 100 if position and position.average_price > 0 else 0,
                'is_active': strategy.is_active
            }
            strategy_data.append(strategy_info)
    
    return render_template(
        'quant.html',
        stocks=stocks,
        strategies=strategy_data,
        dates=dates,
        profits=profits,
        total_profit=total_profit,
        active_strategies=active_strategies,
        today_trades=today_trades
    )

@app.route('/quant/add', methods=['POST'])
@login_required
def add_quant_strategy():
    """Add a new quantitative trading strategy"""
    try:
        stock_code = request.form.get('stock_code')
        ma_short = int(request.form.get('ma_short'))
        ma_long = int(request.form.get('ma_long'))
        momentum_days = int(request.form.get('momentum_days'))
        position_size = int(request.form.get('position_size'))
        
        # Validate parameters
        if ma_short >= ma_long:
            flash('短期均线周期必须小于长期均线周期', 'error')
            return redirect(url_for('quant'))
        
        # Check for existing strategy
        existing = QuantStrategy.query.filter_by(
            user_id=current_user.id,
            stock_code=stock_code
        ).first()
        
        if existing:
            flash('该股票已有策略存在', 'error')
            return redirect(url_for('quant'))
        
        # Create new strategy
        strategy = QuantStrategy(
            user_id=current_user.id,
            stock_code=stock_code,
            ma_short=ma_short,
            ma_long=ma_long,
            momentum_days=momentum_days,
            position_size=position_size
        )
        
        db.session.add(strategy)
        db.session.commit()
        
        flash('策略添加成功', 'success')
    except Exception as e:
        flash(f'策略添加失败: {str(e)}', 'error')
    
    return redirect(url_for('quant'))

@app.route('/quant/toggle/<int:strategy_id>')
@login_required
def toggle_strategy(strategy_id):
    """Toggle strategy active status"""
    strategy = QuantStrategy.query.get_or_404(strategy_id)
    
    if strategy.user_id != current_user.id:
        flash('无权操作此策略', 'error')
        return redirect(url_for('quant'))
    
    strategy.is_active = not strategy.is_active
    db.session.commit()
    
    status = '启动' if strategy.is_active else '停止'
    flash(f'策略已{status}', 'success')
    return redirect(url_for('quant'))

def run_quant_strategies():
    """执行所有活跃的量化策略"""
    with app.app_context():
        while True:
            try:
                print("开始执行量化策略检查...")
                # 获取所有活跃的策略
                strategies = QuantStrategy.query.filter_by(is_active=True).all()
                current_date = datetime.now().date()
                
                for strategy in strategies:
                    try:
                        # 检查是否已经今日交易
                        if strategy.last_trade_date == current_date:
                            continue
                        
                        # 获取股票信息
                        stock = Stock.query.filter_by(code=strategy.stock_code).first()
                        if not stock:
                            print(f"未找到股票: {strategy.stock_code}")
                            continue
                        
                        # 获取历史价格数据（这里使用模拟数据）
                        price_history = [stock.last_price * (1 + random.uniform(-0.02, 0.02)) 
                                       for _ in range(max(strategy.ma_long, strategy.momentum_days))]
                        price_history.append(stock.last_price)  # 添加当前价格
                        
                        # 计算信号
                        signal = strategy.calculate_signal(price_history)
                        print(f"策略 {strategy.id} ({strategy.stock_code}) 信号: {signal}")
                        
                        if signal == 1 and strategy.position == 0:  # 买入信号
                            # 计算可以买入的数量（考虑手续费）
                            amount = strategy.position_size * stock.last_price
                            commission = amount * 0.0003  # 手续费率
                            total_cost = amount + commission
                            
                            # 检查用户余额
                            user = User.query.get(strategy.user_id)
                            if user.balance >= total_cost:
                                print(f"执行买入: {strategy.stock_code}, 数量: {strategy.position_size}, 价格: {stock.last_price}")
                                
                                # 创建交易记录
                                trade = Trade(
                                    user_id=strategy.user_id,
                                    stock_id=stock.id,
                                    type='BUY',
                                    quantity=strategy.position_size,
                                    price=stock.last_price,
                                    commission=commission,
                                    total_amount=amount
                                )
                                db.session.add(trade)
                                
                                # 更新策略状态
                                strategy.position = strategy.position_size
                                strategy.avg_price = stock.last_price
                                strategy.last_trade_date = current_date
                                
                                # 更新用户余额
                                user.balance -= total_cost
                                
                                db.session.commit()
                                print(f"买入交易完成: {strategy.stock_code}")
                            else:
                                print(f"余额不足，无法买入: {strategy.stock_code}")
                            
                        elif signal == -1 and strategy.position > 0:  # 卖出信号
                            # 计算卖出金额和手续费
                            amount = strategy.position * stock.last_price
                            commission = amount * 0.0003  # 手续费率
                            net_amount = amount - commission
                            
                            print(f"执行卖出: {strategy.stock_code}, 数量: {strategy.position}, 价格: {stock.last_price}")
                            
                            # 创建交易记录
                            trade = Trade(
                                user_id=strategy.user_id,
                                stock_id=stock.id,
                                type='SELL',
                                quantity=strategy.position,
                                price=stock.last_price,
                                commission=commission,
                                total_amount=amount
                            )
                            db.session.add(trade)
                            
                            # 计算收益
                            profit = amount - (strategy.position * strategy.avg_price) - commission
                            strategy.total_profit += profit
                            
                            # 更新用户余额
                            user = User.query.get(strategy.user_id)
                            user.balance += net_amount
                            
                            # 更新策略状态
                            strategy.position = 0
                            strategy.avg_price = 0
                            strategy.last_trade_date = current_date
                            
                            db.session.commit()
                            print(f"卖出交易完成: {strategy.stock_code}, 收益: {profit}")
                    
                    except Exception as e:
                        print(f"处理策略 {strategy.id} 时出错: {str(e)}")
                        db.session.rollback()
                        continue
                
                print("量化策略检查完成")
            except Exception as e:
                print(f"执行量化策略时出错: {str(e)}")
                db.session.rollback()
            
            time.sleep(60)  # 每分钟检查一次

def start_quant_thread():
    """启动量化交易线程"""
    thread = Thread(target=run_quant_strategies)
    thread.daemon = True  # 设置为守护线程，这样主程序退出时线程会自动结束
    thread.start()
    print("量化交易线程已启动")

# 在应用启动时启动量化交易线程
@app.before_first_request
def initialize():
    """应用初始化"""
    try:
        # 确保数据库表存在
        db.create_all()
        
        # 初始化股票数据
        init_stock_data()
        
        # 启动价格更新线程
        start_price_updater()
        
        # 启动量化交易线程
        start_quant_thread()
        
        print("应用初始化完成")
    except Exception as e:
        print(f"初始化失败: {str(e)}")

@app.route('/quant/status')
@login_required
def quant_status():
    """查看量化交易状态"""
    # 获取用户的所有策略
    strategies = QuantStrategy.query.filter_by(user_id=current_user.id).all()
    
    # 获取今日交易记录
    today = datetime.now().date()
    trades = Trade.query.filter(
        Trade.user_id == current_user.id,
        Trade.created_at >= today
    ).order_by(Trade.created_at.desc()).all()
    
    # 准备策略状态数据
    strategy_status = []
    for strategy in strategies:
        # 获取股票信息
        stock = Stock.query.filter_by(code=strategy.stock_code).first()
        
        # 获取该策略今日交易
        strategy_trades = [t for t in trades if t.stock_id == stock.id]
        
        status = {
            'id': strategy.id,
            'stock_code': strategy.stock_code,
            'stock_name': stock.name if stock else '',
            'is_active': strategy.is_active,
            'position': strategy.position,
            'avg_price': strategy.avg_price,
            'total_profit': strategy.total_profit,
            'last_trade_date': strategy.last_trade_date,
            'today_trades': len(strategy_trades),
            'params': {
                'ma_short': strategy.ma_short,
                'ma_long': strategy.ma_long,
                'momentum_days': strategy.momentum_days,
                'position_size': strategy.position_size
            }
        }
        strategy_status.append(status)
    
    return render_template(
        'quant_status.html',
        strategies=strategy_status,
        trades=trades[:20]  # 只显示最近20条交易
    )

@app.route('/position_history')
@login_required
def position_history():
    """持仓历史页面"""
    positions = Position.query.filter_by(user_id=current_user.id).all()
    return render_template('position_history.html', positions=positions)

@app.route('/api/position/<int:position_id>/history')
@login_required
def get_position_history(position_id):
    """获取持仓30天历史数据的API"""
    print(f"\n=== 开始处理持仓历史数据请求 ===")
    print(f"请求的持仓ID: {position_id}")
    print(f"当前用户ID: {current_user.id}")
    
    try:
        position = Position.query.get_or_404(position_id)
        print(f"找到持仓: {position.stock.code} - {position.stock.name}")
        print(f"持仓数量: {position.quantity}")
        print(f"平均成本: {position.average_price}")
        
        # 验证权限
        if position.user_id != current_user.id:
            print(f"权限验证失败: 用户 {current_user.id} 尝试访问持仓 {position_id}")
            return jsonify({'error': '无权访问此持仓'}), 403
        
        # 获取过去30天的日期
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)
        print(f"获取数据时间范围: {start_date} 到 {end_date}")
        
        # 获取该持仓的30天交易记录
        trades = Trade.query.filter(
            Trade.user_id == current_user.id,
            Trade.stock_id == position.stock_id,
            Trade.created_at >= start_date,
            Trade.created_at <= end_date
        ).order_by(Trade.created_at).all()
        
        print(f"找到 {len(trades)} 条交易记录")
        
        # 准备数据
        dates = []
        profits = []
        cumulative_profit = 0
        
        # 计算初始持仓成本
        initial_cost = position.quantity * position.average_price
        print(f"初始持仓成本: {initial_cost}")
        
        current_date = start_date
        while current_date <= end_date:
            next_date = current_date + timedelta(days=1)
            
            # 获取当天的交易记录
            day_trades = [t for t in trades if t.created_at.date() == current_date]
            
            # 计算当天的交易收益
            day_profit = sum(
                trade.quantity * (trade.price - trade.commission/trade.quantity)
                if trade.type == 'SELL'
                else -trade.quantity * (trade.price + trade.commission/trade.quantity)
                for trade in day_trades
            )
            
            # 计算持仓市值变化
            if current_date == end_date:
                # 使用当前价格
                position_value = position.quantity * position.stock.last_price
            else:
                # 使用模拟数据（实际应用中应该使用历史数据）
                price_change = random.uniform(-0.02, 0.02)
                simulated_price = position.stock.last_price * (1 + price_change)
                position_value = position.quantity * simulated_price
            
            # 计算总收益（包括交易收益和持仓市值变化）
            current_profit = cumulative_profit + day_profit + (position_value - initial_cost)
            
            dates.append(current_date.strftime('%Y-%m-%d'))
            profits.append(round(current_profit, 2))
            
            # 更新累计交易收益
            cumulative_profit += day_profit
            
            current_date = next_date
        
        print(f"生成了 {len(dates)} 天的数据")
        
        # 确保数据不为空
        if not dates or not profits:
            print("没有生成任何数据")
            return jsonify({
                'error': '没有足够的历史数据',
                'dates': [],
                'profits': [],
                'stock_code': position.stock.code,
                'stock_name': position.stock.name,
                'position': position.quantity,
                'avg_price': position.average_price,
                'current_price': position.stock.last_price
            })
        
        response_data = {
            'dates': dates,
            'profits': profits,
            'stock_code': position.stock.code,
            'stock_name': position.stock.name,
            'position': position.quantity,
            'avg_price': position.average_price,
            'current_price': position.stock.last_price
        }
        print("准备返回的数据:", response_data)
        print("=== 持仓历史数据请求处理完成 ===\n")
        return jsonify(response_data)
    except Exception as e:
        print(f"处理持仓历史数据请求时出错: {str(e)}")
        print("=== 持仓历史数据请求处理失败 ===\n")
        return jsonify({'error': str(e)}), 500

@app.route('/api/check-session')
def check_session():
    """检查用户会话状态"""
    try:
        if current_user.is_authenticated:
            return jsonify({
                'status': 'ok',
                'user_id': current_user.id,
                'username': current_user.username
            })
        return jsonify({'error': 'unauthorized'}), 401
    except Exception as e:
        print(f"检查会话状态时出错: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.errorhandler(401)
def unauthorized_error(error):
    """处理未授权错误"""
    if request.is_xhr:  # 如果是AJAX请求
        return jsonify({'error': 'unauthorized', 'message': '请重新登录'}), 401
    return redirect(url_for('login'))

@app.errorhandler(500)
def internal_error(error):
    """处理内部服务器错误"""
    db.session.rollback()  # 回滚数据库会话
    if request.is_xhr:  # 如果是AJAX请求
        return jsonify({'error': 'internal_error', 'message': '服务器内部错误'}), 500
    return render_template('error.html', error=error), 500

@app.before_request
def check_user_session():
    """在每个请求之前检查用户会话"""
    if current_user.is_authenticated:
        # 更新用户最后活动时间
        session['last_activity'] = datetime.now().timestamp()
    elif request.endpoint and 'static' not in request.endpoint and request.endpoint not in ['login', 'register']:
        if request.is_xhr:
            # 如果是AJAX请求，返回401状态码
            return jsonify({'error': 'unauthorized', 'message': '请重新登录'}), 401
        # 否则重定向到登录页面
        return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True) 