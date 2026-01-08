from tkrtshare import tk
import pandas as pd
from datetime import datetime
import time

class TadawulLive:
    def __init__(self):
        self.tk = tk.TkShare()
        self.connected = False
        
    def connect(self):
        """الاتصال بخدمة تكرتشارت"""
        try:
            # الاتصال التلقائي
            self.tk.connect()
            self.connected = True
            print("✅ تم الاتصال بتكرتشارت لايف")
            return True
        except Exception as e:
            print(f"❌ خطأ في الاتصال: {e}")
            return False
    
    def get_realtime_data(self, symbol):
        """الحصول على بيانات مباشرة للسهم"""
        if not self.connected:
            self.connect()
        
        try:
            # بيانات مباشرة من تكرتشارت
            stock_data = self.tk.get_individual_stock(symbol)
            
            return {
                "symbol": symbol,
                "price": stock_data.get("current", 0),
                "change": stock_data.get("change", 0),
                "change_percent": stock_data.get("change_percent", 0),
                "volume": stock_data.get("volume", 0),
                "high": stock_data.get("high", 0),
                "low": stock_data.get("low", 0),
                "open": stock_data.get("open", 0),
                "previous_close": stock_data.get("previous_close", 0),
                "bid": stock_data.get("bid", 0),
                "ask": stock_data.get("ask", 0),
                "orders": stock_data.get("orders", []),
                "timestamp": datetime.now().strftime("%H:%M:%S")
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_historical_data(self, symbol, period="1y"):
        """الحصول على بيانات تاريخية"""
        try:
            # بيانات تاريخية من تكرتشارت
            hist_data = self.tk.get_historical_data(symbol, period)
            
            # تحويل لـ DataFrame
            df = pd.DataFrame(hist_data)
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            
            return df
        except Exception as e:
            # استخدام yfinance كبديل
            import yfinance as yf
            stock = yf.Ticker(symbol + ".SR")
            hist = stock.history(period=period)
            return hist
    
    def get_market_depth(self, symbol):
        """الحصول على عمق السوق (أوامر الشراء والبيع)"""
        try:
            market_depth = self.tk.get_market_depth(symbol)
            return {
                "bids": market_depth.get("bids", []),  # أوامر الشراء
                "asks": market_depth.get("asks", []),  # أوامر البيع
                "timestamp": datetime.now().strftime("%H:%M:%S")
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_all_stocks(self):
        """الحصول على جميع أسهم السوق"""
        try:
            all_stocks = self.tk.get_all_stocks()
            return all_stocks
        except Exception as e:
            return []
    
    def stream_realtime_data(self, symbols, callback):
        """بث بيانات مباشرة مستمرة"""
        def stream_handler(data):
            callback(data)
        
        try:
            self.tk.subscribe(symbols, stream_handler)
            print(f"✅ بدأ البث المباشر لـ {len(symbols)} سهم")
        except Exception as e:
            print(f"❌ خطأ في البث: {e}")

# مثال للاستخدام
if __name__ == "__main__":
    tadawul = TadawulLive()
    
    # بيانات مباشرة للراجحي
    data = tadawul.get_realtime_data("1120")
    print(f"سعر الراجحي الحالي: {data['price']}")
    print(f"التغيير: {data['change']} ({data['change_percent']}%)")
    
    # عمق السوق
    depth = tadawul.get_market_depth("1120")
    print(f"أعلى سعر شراء: {depth['bids'][0] if depth.get('bids') else 'N/A'}")
    print(f"أقل سعر بيع: {depth['asks'][0] if depth.get('asks') else 'N/A'}")