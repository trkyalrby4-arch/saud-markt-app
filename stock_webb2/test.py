# test.py - إصدار بدون رموز تعبيرية
import yfinance as yf
import pandas as pd
from datetime import datetime

print("اختبار اتصال yfinance بالإنترنت...")
print("=" * 50)

# قائمة الأسهم السعودية للاختبار
test_symbols = [
    "2222.SR",  # أرامكو
    "1211.SR",  # الراجحي
    "2010.SR",  # سابك
    "^TASI.SR"  # المؤشر العام
]

success_count = 0
fail_count = 0

for symbol in test_symbols:
    try:
        print(f"\nجاري جلب {symbol}...")
        ticker = yf.Ticker(symbol)
        
        # جلب بيانات 5 أيام
        data = ticker.history(period="5d")
        
        if data.empty:
            print(f"خطأ: {symbol}: لا توجد بيانات (مجلد فارغ)")
            fail_count += 1
            continue
        
        print(f"نجاح: {symbol}: تم جلب {len(data)} يوم")
        print(f"   آخر سعر: {data['Close'].iloc[-1]:.2f}")
        
        if len(data) >= 2:
            change = data['Close'].iloc[-1] - data['Close'].iloc[-2]
            print(f"   التغير: {change:+.2f}")
        
        success_count += 1
        
    except Exception as e:
        print(f"خطأ: {symbol}: {str(e)[:80]}")
        fail_count += 1

print("\n" + "=" * 50)
print(f"النتيجة: نجح {success_count} / فشل {fail_count} من {len(test_symbols)}")

if success_count == 0:
    print("المشكلة: yfinance لا يتصل بالإنترنت أو هناك حظر")
    print("الحل: جرب استخدام VPN أو تحديث المكتبات")
elif success_count < len(test_symbols):
    print("بعض الرموز تعمل والبعض لا - المشكلة في الرموز أو Yahoo Finance")
else:
    print("كل شيء يعمل - المشكلة في تطبيق Flask الرئيسي")

print("=" * 50)