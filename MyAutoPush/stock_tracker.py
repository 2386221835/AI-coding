# -*- coding: utf-8 -*-
import requests
import time
from datetime import datetime, time as dt_time

# ================== 请在这里配置你的信息 ==================
# 1. 飞书机器人 Webhook 地址（必填）
FEISHU_WEBHOOK = "https://open.feishu.cn/open-apis/bot/v2/hook/9bc8b638-b829-4eb2-b484-48f230405583"
# ↑ 把你在飞书群里复制的地址粘贴到引号里面

# 2. 自选股列表（在这里添加你想监控的股票）
MY_STOCKS = [
    {"code": "sz000785", "name": "居然智家"},
    {"code": "sz002050", "name": "三花智控"},
    {"code": "sz000977", "name": "浪潮信息"},
    {"code": "sh600038", "name": "中直股份"},
    {"code": "sz000617", "name": "中油资本"},
]

# 3. 推送间隔（秒），300 = 5分钟
PUSH_INTERVAL = 300

# 4. 是否每次推送所有自选股（True=全部推送，False=只推送有变化的）
PUSH_ALL_STOCKS = True
# ========================================================

def is_trading_time(now):
    """判断是否在A股交易时间内（周一至周五 9:30-11:30, 13:00-15:00）"""
    if now.weekday() >= 5:
        return False
    current = now.time()
    morning_start = dt_time(9, 30)
    morning_end = dt_time(11, 30)
    afternoon_start = dt_time(13, 0)
    afternoon_end = dt_time(15, 0)
    if morning_start <= current <= morning_end:
        return True
    if afternoon_start <= current <= afternoon_end:
        return True
    return False

def get_single_stock(stock):
    """获取单只股票的实时行情（使用新浪财经API，无需任何token）"""
    try:
        url = f"https://hq.sinajs.cn/list={stock['code']}"
        headers = {"Referer": "https://finance.sina.com.cn"}
        r = requests.get(url, headers=headers, timeout=10)
        r.encoding = 'gbk'
        
        if r.status_code == 200 and r.text and '=""' not in r.text:
            data = r.text.split(',')
            if len(data) >= 5:
                name = data[0].split('="')[1] if '="' in data[0] else stock['name']
                current_price = float(data[3])
                previous_close = float(data[2])
                change = current_price - previous_close
                change_percent = (change / previous_close) * 100
                up_icon = "📈" if change >= 0 else "📉"
                return {
                    "name": name,
                    "code": stock['code'],
                    "price": current_price,
                    "change": change,
                    "change_percent": change_percent,
                    "icon": up_icon,
                    "success": True
                }
        return {"name": stock['name'], "code": stock['code'], "success": False}
    except Exception as e:
        print(f"获取{stock['name']}失败: {e}")
        return {"name": stock['name'], "code": stock['code'], "success": False}

def get_all_stocks():
    """获取所有自选股的行情"""
    results = []
    for stock in MY_STOCKS:
        data = get_single_stock(stock)
        results.append(data)
        time.sleep(0.2)
    return results

def send_to_feishu(content):
    """发送消息到飞书"""
    if not FEISHU_WEBHOOK or "xxxxxxx" in FEISHU_WEBHOOK:
        print("❌ 错误：请先填写正确的飞书Webhook地址")
        return False
    
    headers = {"Content-Type": "application/json"}
    data = {"msg_type": "text", "content": {"text": content}}
    
    try:
        resp = requests.post(FEISHU_WEBHOOK, json=data, headers=headers, timeout=10)
        if resp.status_code == 200:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 推送成功")
            return True
        else:
            print(f"❌ 推送失败，状态码: {resp.status_code}")
            return False
    except Exception as e:
        print(f"❌ 推送异常: {e}")
        return False

def format_message(stocks_data):
    """格式化推送消息"""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = f"📊 【股票行情推送】\n🕒 {now_str}\n" + "=" * 20 + "\n"
    
    for stock in stocks_data:
        if stock["success"]:
            msg += f"{stock['icon']} {stock['name']}({stock['code']})\n"
            msg += f"   现价: {stock['price']:.2f}\n"
            msg += f"   涨跌: {stock['change']:+.2f}\n"
            msg += f"   涨幅: {stock['change_percent']:+.2f}%\n\n"
        else:
            msg += f"❌ {stock['name']}({stock['code']}) 获取失败\n\n"
    
    return msg.strip()

def main_loop():
    """主循环"""
    print(f"股票追踪器已启动")
    print(f"监控股票数量: {len(MY_STOCKS)}只")
    print(f"推送间隔: {PUSH_INTERVAL // 60}分钟")
    print(f"数据来源: 新浪财经API（无需注册）")
    
    last_data = None
    
    while True:
        now = datetime.now()
        
        if is_trading_time(now):
            print(f"\n[{now.strftime('%H:%M:%S')}] 获取自选股行情...")
            stocks_data = get_all_stocks()
            
            should_push = PUSH_ALL_STOCKS or (last_data != stocks_data)
            
            if should_push:
                message = format_message(stocks_data)
                send_to_feishu(message)
                last_data = stocks_data.copy() if stocks_data else None
            else:
                print("行情无变化，跳过推送")
        else:
            print(f"[{now.strftime('%H:%M:%S')}] 非交易时间，等待中...")
        
        # ========== 倒计时提示（每10秒打印一个点，总共等待 PUSH_INTERVAL 秒） ==========
        for i in range(PUSH_INTERVAL // 10):
            time.sleep(10)
            print(".", end="", flush=True)
        print()  # 换行，准备下一次循环

if __name__ == "__main__":
    main_loop()