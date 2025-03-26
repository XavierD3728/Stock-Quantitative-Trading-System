from app import app, db
from database import Stock, User, Position, Trade, TradingStrategy, QuantStrategy

def init_db():
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Add default stocks
        default_stocks = Stock.get_default_stocks()
        for stock_data in default_stocks:
            stock = Stock(**stock_data)
            db.session.add(stock)
        
        try:
            db.session.commit()
            print("Database initialized successfully!")
        except Exception as e:
            print(f"Error initializing database: {e}")
            db.session.rollback()

if __name__ == "__main__":
    init_db() 