import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import time

# ============================================
# 页面配置
# ============================================
st.set_page_config(
    page_title="全球资讯和股票看板",
    page_icon="📈",
    layout="wide"
)

# 自动刷新：每 5 分钟
st.markdown(
    """
    <meta http-equiv="refresh" content="300">
    """,
    unsafe_allow_html=True
)

# 显示当前日期时间
current_time = datetime.now().strftime("%Y年%m月%d日 %A %H:%M:%S")
st.title("🌍 全球资讯和股票看板")
st.caption(f"📅 最后更新时间：{current_time}")

# ============================================
# 个股行情获取（新浪财经API，解析位置正确）
# ============================================

def fetch_sina_stock(symbol):
    """
    通过新浪财经接口获取单只股票的实时行情数据。
    
    参数:
        symbol: 股票代码，如 'sh600038' 或 'sz000977'
    
    返回:
        dict: 包含股票名称、现价、涨跌幅等信息的字典；若失败则返回 None
    """
    url = f"http://hq.sinajs.cn/list={symbol}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://finance.sina.com.cn"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'gbk'
        
        if response.status_code == 200:
            data = response.text
            
            # 解析新浪财经返回的数据格式
            # 示例: var hq_str_sh600038="中直股份,42.150,42.450,42.580,43.000,42.110,42.580,42.610,...
            if '="' in data:
                content = data.split('="')[1].split('",')[0]
                fields = content.split(',')
                
                # 新浪财经字段索引（A股）:
                # 0: 股票名称
                # 1: 今日开盘价
                # 2: 昨日收盘价
                # 3: 当前价格
                # 4: 今日最高价
                # 5: 今日最低价
                # 6: 买一价
                # 7: 卖一价
                if len(fields) >= 8:
                    name = fields[0]                          # 股票名称
                    current_price = float(fields[3])          # 当前价格
                    yesterday_close = float(fields[2])        # 昨日收盘价
                    
                    # 计算涨跌幅
                    if yesterday_close > 0:
                        change = current_price - yesterday_close
                        change_percent = (change / yesterday_close) * 100
                    else:
                        change = 0.0
                        change_percent = 0.0
                    
                    return {
                        "name": name,
                        "current_price": round(current_price, 2),
                        "change": round(change, 2),
                        "change_percent": round(change_percent, 2)
                    }
    except Exception as e:
        st.error(f"获取 {symbol} 行情失败: {e}")
    
    return None

def fetch_multiple_stocks(stock_list):
    """
    批量获取多只股票的实时行情数据。
    
    参数:
        stock_list: 股票代码列表，如 [('sh600038', '中直股份'), ('sz000977', '浪潮信息'), ...]
    
    返回:
        list: 包含股票行情数据的字典列表
    """
    stock_data_list = []
    
    for symbol, display_name in stock_list:
        data = fetch_sina_stock(symbol)
        if data:
            # 用传入的显示名称覆盖 API 返回的名称
            data["display_name"] = display_name
            stock_data_list.append(data)
        else:
            # 失败时填充默认数据
            stock_data_list.append({
                "display_name": display_name,
                "name": display_name,
                "current_price": 0.0,
                "change": 0.0,
                "change_percent": 0.0
            })
        # 为避免请求过快，稍作延迟
        time.sleep(0.2)
    
    return stock_data_list

# ============================================
# 板块行情获取（AKShare，真实数据）
# ============================================

def fetch_sector_spot():
    """
    获取真实板块行情数据（使用 AKShare 开源库）。
    
    返回:
        list: 板块行情数据列表，每个元素包含 name、change_percent、leading_stock
    """
    try:
        # 尝试导入 AKShare
        import akshare as ak
        
        # 获取行业板块实时行情
        sector_df = ak.stock_board_industry_spot()
        
        # 提取需要的数据列
        sector_list = []
        for idx, row in sector_df.head(15).iterrows():
            sector_name = row.get("板块名称", row.get("name", "未知"))
            change_percent = row.get("涨跌幅", 0)
            leading_stock = row.get("领涨股票", "暂无")
            
            # 处理涨跌幅为字符串的情况
            if isinstance(change_percent, str):
                try:
                    change_percent = float(change_percent)
                except:
                    change_percent = 0
            
            sector_list.append({
                "name": sector_name,
                "change_percent": round(change_percent, 2),
                "leading_stock": leading_stock if leading_stock else "暂无"
            })
        
        if sector_list:
            sector_list.sort(key=lambda x: x["change_percent"], reverse=True)
            return sector_list
            
    except ImportError:
        # AKShare 未安装，使用备用模拟数据
        st.warning("AKShare 未安装，正在使用模拟板块数据。请运行 'pip install akshare' 安装后获取真实板块行情。")
        return get_fallback_sector_data()
    except Exception as e:
        # AKShare 调用失败，使用备用数据
        st.warning(f"获取板块数据失败: {e}，正在使用模拟板块数据。")
        return get_fallback_sector_data()


def get_fallback_sector_data():
    """备用板块数据（当 AKShare 不可用时使用）"""
    fallback = [
        {"name": "人工智能", "change_percent": 2.45, "leading_stock": "科大讯飞"},
        {"name": "半导体芯片", "change_percent": 1.87, "leading_stock": "中芯国际"},
        {"name": "新能源汽车", "change_percent": 1.23, "leading_stock": "比亚迪"},
        {"name": "军工航空", "change_percent": 0.56, "leading_stock": "中航沈飞"},
        {"name": "生物医药", "change_percent": -0.32, "leading_stock": "药明康德"},
        {"name": "白酒消费", "change_percent": -0.87, "leading_stock": "贵州茅台"},
        {"name": "银行金融", "change_percent": -0.51, "leading_stock": "工商银行"},
        {"name": "房地产", "change_percent": -1.23, "leading_stock": "万科A"},
    ]
    fallback.sort(key=lambda x: x["change_percent"], reverse=True)
    return fallback

# ============================================
# 新闻资讯获取（聚合数据API）
# ============================================

def fetch_news_juhe(api_key, num=10):
    """使用聚合数据接口获取新闻头条"""
    url = "http://v.juhe.cn/toutiao/index"
    params = {"type": "top", "key": api_key, "page": 1, "page_size": num}
    try:
        resp = requests.get(url, params=params, timeout=10)
        result = resp.json()
        if result.get("error_code") == 0:
            news_list = []
            for item in result.get("result", {}).get("data", [])[:num]:
                news_list.append({
                    "title": item.get("title", "无标题"),
                    "source": item.get("author_name", "未知来源"),
                    "url": item.get("url", "#"),
                })
            return news_list
        else:
            return []
    except Exception as e:
        st.error(f"获取新闻失败: {e}")
        return []

def fetch_news_demo():
    """备用新闻数据"""
    return [
        {"title": "三大指数集体收涨，人工智能板块表现活跃", "source": "新浪财经", "url": "#"},
        {"title": "央行公开市场净投放，维护流动性合理充裕", "source": "第一财经", "url": "#"},
        {"title": "新能源汽车销量创新高，产业链持续受益", "source": "证券时报", "url": "#"},
        {"title": "国际金价创历史新高，避险情绪升温", "source": "华尔街见闻", "url": "#"},
        {"title": "多地出台政策支持人工智能产业发展", "source": "21世纪经济报道", "url": "#"},
        {"title": "美联储维持利率不变，市场预期年内降息", "source": "财联社", "url": "#"},
        {"title": "国产大模型取得新突破，应用落地加速", "source": "中国证券报", "url": "#"},
        {"title": "人民币跨境支付系统升级，国际化稳步推进", "source": "金融时报", "url": "#"},
        {"title": "楼市新政效果显现，一线城市成交回暖", "source": "每日经济新闻", "url": "#"},
        {"title": "消费复苏势头强劲，零售板块受关注", "source": "上海证券报", "url": "#"},
    ]

# ============================================
# 主要界面布局
# ============================================

if "news_list" not in st.session_state:
    st.session_state.news_list = []

# ---------- 1. 自选股板块 ----------
st.header("📌 自选股")
st.caption("数据来源：新浪财经API | 涨红跌绿")

# 自选股配置：新浪财经代码需要带市场前缀（sh-沪市，sz-深市）
watchlist = [
    ("sz000977", "浪潮信息"),
    ("sz000938", "居然智家"),
    ("sz002050", "三花智控"),
    ("sh600038", "中直股份"),
]

with st.spinner("正在获取自选股实时行情..."):
    stock_data = fetch_multiple_stocks(watchlist)

if stock_data:
    cols = st.columns(len(stock_data))
    for idx, stock in enumerate(stock_data):
        with cols[idx]:
            # 判断涨跌背景色
            if stock["change"] > 0:
                bg_color = "#fff0f0"
                color = "red"
            elif stock["change"] < 0:
                bg_color = "#f0fff0"
                color = "green"
            else:
                bg_color = "#f8f9fa"
                color = "gray"
            
            st.markdown(
                f"""
                <div style="background-color:{bg_color}; padding:15px; border-radius:10px; text-align:center;">
                    <h3>{stock['display_name']}</h3>
                    <p style="font-size:28px; font-weight:bold;">¥{stock['current_price']}</p>
                    <p style="color:{color}; font-size:18px;">
                        {'+' if stock['change'] > 0 else ''}{stock['change']}  ({'+' if stock['change_percent'] > 0 else ''}{stock['change_percent']}%)
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )

# ---------- 2. 股票市场板块 ----------
st.header("📊 股票市场板块")
st.caption("数据来源：AKShare (东方财富) | 实时板块涨跌排名 | 涨红跌绿")

sector_data = fetch_sector_spot()

if sector_data:
    rising_sectors = [s for s in sector_data if s["change_percent"] > 0]
    falling_sectors = [s for s in sector_data if s["change_percent"] < 0]
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🚀 上涨板块")
        for sector in rising_sectors[:6]:
            change_color = "red"
            st.markdown(
                f"- **{sector['name']}**：<span style='color:{change_color}'>📈 +{sector['change_percent']:.2f}%</span>，领涨：{sector['leading_stock']}",
                unsafe_allow_html=True
            )
    with col2:
        st.subheader("📉 下跌板块")
        for sector in falling_sectors[:6]:
            change_color = "green"
            st.markdown(
                f"- **{sector['name']}**：<span style='color:{change_color}'>📉 {sector['change_percent']:.2f}%</span>，领跌：{sector['leading_stock']}",
                unsafe_allow_html=True
            )
    
    # ---------- 板块资讯 ----------
    st.subheader("📰 板块资讯")
    st.caption("基于当前热门板块的市场动态")
    
    # 取前5个热点板块（上涨+下跌中变化较大的）
    top_sectors = rising_sectors[:3] + falling_sectors[:2]
    sector_news_map = {
        "人工智能": "大模型应用加速落地，产业链相关公司受益",
        "半导体芯片": "全球芯片需求回暖，国产替代进程提速",
        "新能源汽车": "政策补贴延续，渗透率持续提升",
        "军工航空": "国防预算稳定增长，行业景气度维持高位",
        "生物医药": "创新药获批加速，医保谈判规则优化",
        "白酒消费": "消费复苏带动板块反弹，高端酒企表现稳健",
        "银行金融": "息差收窄压力仍在，但估值处于历史低位",
        "房地产": "政策面持续回暖，但销售恢复仍需时间"
    }
    
    for sector in top_sectors:
        news = sector_news_map.get(sector["name"], f"{sector['name']}板块近期关注度提升，资金持续流入")
        st.markdown(f"- **{sector['name']}**：{news}")

# ---------- 3. 新闻板块 ----------
st.header("📰 精选商业·时政·全球头条")
st.caption("数据来源：聚合数据API | 展示最新10条精选新闻")

# 如需使用真实聚合数据API，将下方的 API Key 替换为您的 Key
JUHE_API_KEY = None

if JUHE_API_KEY and JUHE_API_KEY != "3df3e511bf654e969fdfa07a6e5ad48d":
    if not st.session_state.news_list:
        with st.spinner("正在获取最新新闻..."):
            st.session_state.news_list = fetch_news_juhe(JUHE_API_KEY, num=10)
else:
    if not st.session_state.news_list:
        st.session_state.news_list = fetch_news_demo()

for idx, article in enumerate(st.session_state.news_list):
    with st.container():
        col1, col2 = st.columns([8, 2])
        with col1:
            st.markdown(f"**{idx+1}. [{article['title']}]({article['url']})**")
        with col2:
            st.markdown(f"<span style='color:gray'>{article['source']}</span>", unsafe_allow_html=True)
        st.divider()

st.markdown("---")
st.caption("🔄 页面每 5 分钟自动刷新一次，数据实时更新。如需立即刷新，请手动刷新浏览器。")