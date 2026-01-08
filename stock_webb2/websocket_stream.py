"""
WebSocket لبث البيانات المباشرة من تكرتشارت لايف
يستخدم tkrtshare للبيانات الحية مع WebSocket محلي للبث
"""

import asyncio
import websockets
import json
from datetime import datetime
import threading
import time
from tkrtshare import tk
import pandas as pd

class TadawulLiveStream:
    """
    فئة لإدارة البث المباشر لبيانات الأسهم
    """
    
    def __init__(self, host='localhost', port=8765):
        """
        تهيئة خادم WebSocket المحلي
        
        Args:
            host: عنوان الخادم (localhost)
            port: منفذ الخادم (8765)
        """
        self.host = host
        self.port = port
        self.server = None
        self.connected_clients = set()
        self.tk_share = tk.TkShare()
        self.subscribed_symbols = set()
        self.is_streaming = False
        self.stream_thread = None
        self.stream_data = {}  # تخزين بيانات البث
        
        print(f" تم تهيئة خادم WebSocket على {host}:{port}")
    
    def connect_to_tadawul(self):
        """الاتصال بتكرتشارت"""
        try:
            self.tk_share.connect()
            print(" تم الاتصال بتكرتشارت لايف")
            return True
        except Exception as e:
            print(f" خطأ في الاتصال بتكرتشارت: {e}")
            return False
    
    def get_realtime_data(self, symbol):
        """الحصول على بيانات مباشرة لسهم واحد"""
        try:
            data = self.tk_share.get_individual_stock(symbol)
            
            # تنسيق البيانات للبث
            formatted_data = {
                "type": "stock_update",
                "symbol": symbol,
                "data": {
                    "price": data.get("current", 0),
                    "change": data.get("change", 0),
                    "change_percent": data.get("change_percent", 0),
                    "volume": data.get("volume", 0),
                    "high": data.get("high", 0),
                    "low": data.get("low", 0),
                    "open": data.get("open", 0),
                    "previous_close": data.get("previous_close", 0),
                    "bid": data.get("bid", 0),
                    "ask": data.get("ask", 0),
                    "orders": data.get("orders", []),
                    "timestamp": datetime.now().strftime("%H:%M:%S.%f")[:-3]
                }
            }
            
            # تحديث بيانات البث
            self.stream_data[symbol] = formatted_data
            
            return formatted_data
        except Exception as e:
            return {
                "type": "error",
                "symbol": symbol,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def get_market_depth(self, symbol):
        """الحصول على عمق السوق"""
        try:
            depth = self.tk_share.get_market_depth(symbol)
            return {
                "type": "market_depth",
                "symbol": symbol,
                "bids": depth.get("bids", [])[:5],  # أول 5 أوامر شراء
                "asks": depth.get("asks", [])[:5],  # أول 5 أوامر بيع
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def handler(self, websocket, path):
        """
        معالج اتصالات WebSocket
        """
        client_id = id(websocket)
        self.connected_clients.add(websocket)
        
        print(f" عميل متصل [{client_id}] - إجمالي العملاء: {len(self.connected_clients)}")
        
        try:
            async for message in self.connected_clients:
                try:
                    data = json.loads(message)
                    
                    # معالجة الرسائل الواردة من العملاء
                    if data.get("type") == "subscribe":
                        symbol = data.get("symbol")
                        if symbol:
                            self.subscribed_symbols.add(symbol)
                            print(f" اشتراك جديد في {symbol}")
                            
                            # إرسال بيانات أولية
                            stock_data = self.get_realtime_data(symbol)
                            await websocket.send(json.dumps(stock_data))
                    
                    elif data.get("type") == "unsubscribe":
                        symbol = data.get("symbol")
                        if symbol in self.subscribed_symbols:
                            self.subscribed_symbols.remove(symbol)
                            print(f" إلغاء اشتراك من {symbol}")
                    
                    elif data.get("type") == "ping":
                        await websocket.send(json.dumps({
                            "type": "pong",
                            "timestamp": datetime.now().isoformat()
                        }))
                    
                    elif data.get("type") == "get_history":
                        symbol = data.get("symbol")
                        period = data.get("period", "1d")
                        try:
                            hist_data = self.tk_share.get_historical_data(symbol, period)
                            await websocket.send(json.dumps({
                                "type": "history_data",
                                "symbol": symbol,
                                "data": hist_data
                            }))
                        except Exception as e:
                            await websocket.send(json.dumps({
                                "type": "error",
                                "message": str(e)
                            }))
                
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": "رسالة غير صالحة"
                    }))
        
        except websockets.exceptions.ConnectionClosed:
            print(f" عميل مفصول [{client_id}]")
        finally:
            self.connected_clients.remove(websocket)
            print(f" إجمالي العملاء المتبقين: {len(self.connected_clients)}")
    
    def start_streaming(self, interval=2):
        """
        بدء بث البيانات للمشتركين
        
        Args:
            interval: الفترة بين كل تحديث بالثواني
        """
        if not self.connect_to_tadawul():
            print("❌ لا يمكن بدء البث - الاتصال بتكرتشارت فشل")
            return
        
        self.is_streaming = True
        
        def stream_loop():
            while self.is_streaming:
                try:
                    # تحديث البيانات لكل سهم مشترك
                    for symbol in list(self.subscribed_symbols):
                        stock_data = self.get_realtime_data(symbol)
                        
                        # إرسال البيانات لجميع العملاء المتصلين
                        if self.connected_clients:
                            message = json.dumps(stock_data)
                            websockets.broadcast(self.connected_clients, message)
                    
                    # انتظر قبل التحديث التالي
                    time.sleep(interval)
                    
                except Exception as e:
                    print(f" خطأ في البث: {e}")
                    time.sleep(5)  # انتظر 5 ثواني قبل إعادة المحاولة
        
        # بدء البث في thread منفصل
        self.stream_thread = threading.Thread(target=stream_loop, daemon=True)
        self.stream_thread.start()
        print(f" بدأ البث المباشر (تحديث كل {interval} ثواني)")
    
    def stop_streaming(self):
        """إيقاف البث المباشر"""
        self.is_streaming = False
        if self.stream_thread:
            self.stream_thread.join(timeout=5)
        print("⏹ تم إيقاف البث المباشر")
    
    async def start_server(self):
        """بدء خادم WebSocket"""
        try:
            self.server = await websockets.serve(
                self.handler,
                self.host,
                self.port
            )
            print(f" خادم WebSocket يعمل على ws://{self.host}:{self.port}")
            
            # بدء بث البيانات
            self.start_streaming()
            
            # استمر في التشغيل
            await self.server.wait_closed()
            
        except Exception as e:
            print(f" خطأ في تشغيل الخادم: {e}")
    
    def get_connection_status(self):
        """الحصول على حالة الاتصال"""
        return {
            "websocket_clients": len(self.connected_clients),
            "subscribed_symbols": list(self.subscribed_symbols),
            "is_streaming": self.is_streaming,
            "last_update": datetime.now().strftime("%H:%M:%S")
        }


# كود JavaScript للاتصال بالـ WebSocket من المتصفح
CLIENT_JS = """
<script>
class TadawulWebSocketClient {
    constructor(url = 'ws://localhost:8765') {
        this.url = url;
        this.ws = null;
        this.connected = false;
        this.subscriptions = new Set();
        this.callbacks = {
            'stock_update': [],
            'market_depth': [],
            'error': [],
            'connected': [],
            'disconnected': []
        };
    }
    
    connect() {
        this.ws = new WebSocket(this.url);
        
        this.ws.onopen = () => {
            this.connected = true;
            console.log(' متصل بخادم WebSocket');
            this.triggerCallback('connected', {});
            
            // إعادة الاشتراك في الرموز السابقة
            this.subscriptions.forEach(symbol => {
                this.subscribe(symbol);
            });
        };
        
        this.ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.triggerCallback(data.type, data);
            } catch (e) {
                console.error('❌ خطأ في معالجة الرسالة:', e);
            }
        };
        
        this.ws.onclose = () => {
            this.connected = false;
            console.log(' انقطع الاتصال بخادم WebSocket');
            this.triggerCallback('disconnected', {});
            
            // إعادة الاتصال بعد 3 ثواني
            setTimeout(() => this.connect(), 3000);
        };
        
        this.ws.onerror = (error) => {
            console.error(' خطأ في WebSocket:', error);
            this.triggerCallback('error', { error: error.message });
        };
    }
    
    disconnect() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
            this.connected = false;
        }
    }
    
    subscribe(symbol) {
        if (!this.connected) {
            console.warn(' ليس متصلاً - سيتم الاشتراك عند الاتصال');
            this.subscriptions.add(symbol);
            return;
        }
        
        this.ws.send(JSON.stringify({
            type: 'subscribe',
            symbol: symbol,
            timestamp: new Date().toISOString()
        }));
        
        this.subscriptions.add(symbol);
        console.log(` اشتراك في ${symbol}`);
    }
    
    unsubscribe(symbol) {
        if (!this.connected) {
            this.subscriptions.delete(symbol);
            return;
        }
        
        this.ws.send(JSON.stringify({
            type: 'unsubscribe',
            symbol: symbol
        }));
        
        this.subscriptions.delete(symbol);
        console.log(` إلغاء اشتراك من ${symbol}`);
    }
    
    on(event, callback) {
        if (!this.callbacks[event]) {
            this.callbacks[event] = [];
        }
        this.callbacks[event].push(callback);
    }
    
    triggerCallback(event, data) {
        if (this.callbacks[event]) {
            this.callbacks[event].forEach(callback => {
                try {
                    callback(data);
                } catch (e) {
                    console.error(` خطأ في callback لـ ${event}:`, e);
                }
            });
        }
    }
    
    ping() {
        if (this.connected) {
            this.ws.send(JSON.stringify({ type: 'ping' }));
        }
    }
}

// استخدام المثال
// const client = new TadawulWebSocketClient();
// client.connect();
// 
// client.on('stock_update', (data) => {
//     console.log('تحديث سعر:', data);
//     // تحديث واجهة المستخدم
// });
// 
// client.on('connected', () => {
//     client.subscribe('1120'); // الراجحي
//     client.subscribe('1180'); // الأهلي
// });
</script>
"""

# مثال للاستخدام في Flask
def create_websocket_blueprint():
    """
    إنشاء blueprint لـ Flask لإدارة WebSocket
    """
    from flask import Blueprint, render_template_string
    
    ws_bp = Blueprint('websocket', __name__)
    
    @ws_bp.route('/websocket-test')
    def websocket_test():
        """صفحة تجربة WebSocket"""
        html_template = '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>تجربة WebSocket - تكرتشارت لايف</title>
            <style>
                body { font-family: Arial; padding: 20px; }
                .container { max-width: 800px; margin: 0 auto; }
                .status { padding: 10px; margin: 10px 0; border-radius: 5px; }
                .connected { background: #d4edda; color: #155724; }
                .disconnected { background: #f8d7da; color: #721c24; }
                .stock-card { border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px; }
                .stock-header { display: flex; justify-content: space-between; }
                .stock-price { font-size: 24px; font-weight: bold; }
                .positive { color: green; }
                .negative { color: red; }
                .controls { margin: 20px 0; }
                button { padding: 10px 15px; margin: 0 5px; cursor: pointer; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1> بث مباشر من تكرتشارت لايف</h1>
                
                <div id="status" class="status disconnected">
                     غير متصل
                </div>
                
                <div class="controls">
                    <input type="text" id="symbolInput" placeholder="أدخل رمز السهم (مثال: 1120)" />
                    <button onclick="subscribeSymbol()">اشتراك</button>
                    <button onclick="connectWS()">اتصال</button>
                    <button onclick="disconnectWS()">قطع الاتصال</button>
                </div>
                
                <div id="stocksContainer"></div>
            </div>
            
            <!-- تضمين كود WebSocket -->
            ''' + CLIENT_JS + '''
            
            <script>
                const client = new TadawulWebSocketClient();
                const stocks = {};
                
                function connectWS() {
                    client.connect();
                    
                    client.on('connected', () => {
                        document.getElementById('status').className = 'status connected';
                        document.getElementById('status').innerHTML = ' متصل بخادم البث المباشر';
                    });
                    
                    client.on('disconnected', () => {
                        document.getElementById('status').className = 'status disconnected';
                        document.getElementById('status').innerHTML = ' انقطع الاتصال - جاري إعادة الاتصال...';
                    });
                    
                    client.on('stock_update', (data) => {
                        updateStockDisplay(data);
                    });
                    
                    client.on('error', (data) => {
                        console.error('خطأ:', data);
                    });
                }
                
                function disconnectWS() {
                    client.disconnect();
                }
                
                function subscribeSymbol() {
                    const symbol = document.getElementById('symbolInput').value.trim();
                    if (symbol) {
                        client.subscribe(symbol);
                    }
                }
                
                function updateStockDisplay(data) {
                    const symbol = data.symbol;
                    const stockData = data.data;
                    
                    let stockCard = document.getElementById(`stock-${symbol}`);
                    
                    if (!stockCard) {
                        stockCard = document.createElement('div');
                        stockCard.id = `stock-${symbol}`;
                        stockCard.className = 'stock-card';
                        
                        stockCard.innerHTML = `
                            <div class="stock-header">
                                <h3>${symbol}</h3>
                                <span class="stock-price">0.00</span>
                            </div>
                            <div>
                                <p>التغيير: <span class="change">0.00 (0.00%)</span></p>
                                <p>الحجم: <span class="volume">0</span></p>
                                <p>آخر تحديث: <span class="timestamp">--:--:--</span></p>
                            </div>
                        `;
                        
                        document.getElementById('stocksContainer').appendChild(stockCard);
                    }
                    
                    // تحديث البيانات
                    const priceElement = stockCard.querySelector('.stock-price');
                    const changeElement = stockCard.querySelector('.change');
                    const volumeElement = stockCard.querySelector('.volume');
                    const timestampElement = stockCard.querySelector('.timestamp');
                    
                    priceElement.textContent = stockData.price.toFixed(2);
                    priceElement.className = `stock-price ${stockData.change >= 0 ? 'positive' : 'negative'}`;
                    
                    changeElement.textContent = `${stockData.change.toFixed(2)} (${stockData.change_percent.toFixed(2)}%)`;
                    changeElement.className = stockData.change >= 0 ? 'positive' : 'negative';
                    
                    volumeElement.textContent = stockData.volume.toLocaleString();
                    timestampElement.textContent = stockData.timestamp;
                }
                
                // اتصال تلقائي عند تحميل الصفحة
                window.onload = connectWS;
            </script>
        </body>
        </html>
        '''
        
        return render_template_string(html_template)
    
    return ws_bp


# تشغيل الخادم مباشرة (للتجربة)
if __name__ == "__main__":
    import asyncio
    
    async def main():
        stream_server = TadawulLiveStream()
        await stream_server.start_server()
    
    print(" بدء تشغيل خادم WebSocket لتكرتشارت لايف...")
    asyncio.run(main())