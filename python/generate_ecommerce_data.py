"""
生成电商模拟数据：users.csv / products.csv / orders.csv
"""

import random
import numpy as np
import pandas as pd

random.seed(42)
np.random.seed(42)

# ============================================================
# 常量
# ============================================================
N_USERS = 5000
N_PRODUCTS = 200
N_ORDERS = 50000

SURNAMES = [
    "赵", "钱", "孙", "李", "周", "吴", "郑", "王", "冯", "陈", "褚", "卫", "蒋", "沈", "韩", "杨",
    "朱", "秦", "尤", "许", "何", "吕", "施", "张", "孔", "曹", "严", "华", "金", "魏", "陶", "姜",
    "戚", "谢", "邹", "喻", "柏", "水", "窦", "章", "云", "苏", "潘", "葛", "奚", "范", "彭", "郎",
    "鲁", "韦", "昌", "马", "苗", "凤", "花", "方", "俞", "任", "袁", "柳", "酆", "鲍", "史", "唐",
    "费", "廉", "岑", "薛", "雷", "贺", "倪", "汤", "滕", "殷", "罗", "毕", "郝", "邬", "安", "常",
    "乐", "于", "时", "傅", "皮", "卞", "齐", "康", "伍", "余", "元", "卜", "顾", "孟", "平", "黄",
    "和", "穆", "萧", "尹", "姚", "邵", "湛", "汪", "祁", "毛", "禹", "狄", "米", "贝", "明", "臧",
    "计", "伏", "成", "戴", "谈", "宋", "茅", "庞", "熊", "纪", "舒", "屈", "项", "祝", "董", "梁",
    "杜", "阮", "蓝", "闵", "席", "季", "麻", "强", "贾", "路", "娄", "危", "江", "童", "颜", "郭",
    "梅", "盛", "林", "刁", "钟", "徐", "邱", "骆", "高", "夏", "蔡", "田", "樊", "胡", "凌", "霍",
    "虞", "万", "支", "柯", "昝", "管", "卢", "莫", "经", "房", "裘", "缪", "干", "解", "应", "宗",
    "丁", "宣", "贲", "邓", "郁", "单", "杭", "洪", "包", "诸", "左", "石", "崔", "吉", "钮", "龚",
    "程", "嵇", "邢", "滑", "裴", "陆", "荣", "翁", "荀", "羊", "於", "惠", "甄", "曲", "家", "封",
    "芮", "储", "靳", "汲", "邴", "糜", "松", "富", "山", "车", "侯", "宓", "蓬", "全", "郗", "班",
    "仰", "秋", "伊", "宫", "仇", "栾", "暴", "甘", "斜", "厉", "戎", "祖", "武", "符", "刘", "景",
    "詹", "束", "龙", "叶", "幸", "司", "韶", "郜", "黎", "蓟", "薄", "印", "白", "怀", "蒲", "台",
    "丛", "鄂", "索", "咸", "籍", "赖", "卓", "蔺", "屠", "蒙", "池", "乔", "阴", "郁", "胥", "能",
    "苍", "双", "闻", "莘", "党", "翟", "谭", "贡", "劳", "逄", "姬", "申", "扶", "堵", "冉", "宰",
    "郦", "雍", "却", "桑", "桂", "濮", "牛", "寿", "通", "边", "扈", "燕", "冀", "尚", "农", "温",
    "别", "庄", "晏", "柴", "瞿", "阎", "充", "慕", "连", "茹", "习", "宦", "艾", "鱼", "容", "向",
    "古", "易", "慎", "戈", "廖", "庾", "终", "暨", "居", "衡", "步", "都", "耿", "满", "弘", "匡",
    "国", "文", "寇", "广", "禄", "阙", "东", "欧", "殳", "沃", "利", "蔚", "越", "夔", "隆", "师",
    "巩", "厍", "聂", "晁", "勾", "敖", "融", "冷", "訾", "辛", "阚", "那", "简", "饶", "空", "曾",
    "毋", "沙", "乜", "养", "鞠", "须", "丰", "巢", "关", "蒯", "相", "查", "后", "荆", "红", "游",
    "竺", "权", "逯", "盖", "益", "桓", "公", "谌", "苑", "刘",
]

GIVEN_NAMES_MALE = [
    "伟", "强", "磊", "军", "勇", "杰", "涛", "明", "辉", "鹏", "斌", "峰", "超", "波", "浩",
    "阳", "平", "刚", "健", "志", "文", "华", "飞", "宁", "龙", "海", "亮", "林", "彬", "毅",
]

GIVEN_NAMES_FEMALE = [
    "芳", "敏", "静", "丽", "婷", "雪", "玲", "萍", "红", "霞", "兰", "凤", "洁", "梅", "娟",
    "英", "云", "莲", "珍", "秀", "琴", "娜", "燕", "花", "琳", "玉", "艳", "莉", "娟", "晶",
]

CATEGORIES = ["手机", "电脑", "家电", "服装", "运动", "美妆", "食品", "图书"]

CITIES = ["北京", "上海", "广州", "深圳", "杭州", "成都", "武汉", "南京", "重庆", "西安"]


# ============================================================
# 1. 用户表
# ============================================================
def generate_users(n=N_USERS):
    names = []
    for _ in range(n):
        surname = random.choice(SURNAMES)
        given_pool = random.choice([GIVEN_NAMES_MALE, GIVEN_NAMES_FEMALE])
        given = random.choice(given_pool)
        names.append(surname + given)

    ages = np.random.randint(18, 66, size=n)
    cities = np.random.choice(CITIES, size=n)

    start = pd.Timestamp("2023-01-01")
    end = pd.Timestamp("2025-12-31")
    register_times = pd.to_datetime(
        np.random.randint(start.value // 10**9, end.value // 10**9, size=n),
        unit="s",
    ).strftime("%Y-%m-%d")

    df = pd.DataFrame(
        {
            "user_id": range(1, n + 1),
            "user_name": names,
            "age": ages,
            "city": cities,
            "register_time": register_times,
        }
    )
    return df


# ============================================================
# 2. 商品表
# ============================================================
def generate_products(n=N_PRODUCTS):
    category_prefix_map = {
        "手机": "手机商品",
        "电脑": "电脑商品",
        "家电": "家电商品",
        "服装": "服装商品",
        "运动": "运动商品",
        "美妆": "美妆商品",
        "食品": "食品商品",
        "图书": "图书商品",
    }
    categories = np.random.choice(CATEGORIES, size=n)
    product_names = [
        f"{category_prefix_map[cat]}{i}" for i, cat in enumerate(categories, start=1)
    ]
    prices = np.round(np.random.uniform(50, 5000, size=n), 2)

    df = pd.DataFrame(
        {
            "product_id": range(1, n + 1),
            "product_name": product_names,
            "category": categories,
            "price": prices,
        }
    )
    return df


# ============================================================
# 3. 订单表
# ============================================================
def generate_orders(users_df, products_df, n=N_ORDERS):
    """订单金额 = 商品价格 × 数量;订单时间在用户注册时间之后"""
    user_ids = np.random.randint(1, N_USERS + 1, size=n)
    product_ids = np.random.randint(1, N_PRODUCTS + 1, size=n)
    quantities = np.random.randint(1, 6, size=n)

    price_map = products_df.set_index('product_id')['price']
    amounts = np.round(price_map.loc[product_ids].values * quantities, 2)

    reg_map = users_df.set_index('user_id')['register_time']
    reg_times = pd.to_datetime(reg_map.loc[user_ids].values)
    start = pd.Timestamp("2024-01-01")   # 交易数据业务窗口起点
    end = pd.Timestamp("2026-06-30")
    lower = np.maximum(reg_times, np.datetime64(start))
    order_times = (lower + (end - lower) * np.random.rand(n)).strftime("%Y-%m-%d")

    df = pd.DataFrame(
        {
            "order_id": range(1, n + 1),
            "user_id": user_ids,
            "product_id": product_ids,
            "quantity": quantities,
            "amount": amounts,
            "order_time": order_times,
        }
    )
    return df


# ============================================================
# 4. 用户行为日志表（漏斗分析用）
# ============================================================
def generate_behavior_log(orders_df):
    """
    为每个订单生成完整行为路径，同时生成未转化会话。
    设计要点：
    - 高购买频次用户（>=3单）：放弃率低，主要在浏览环节放弃（挑剔但不差钱）
    - 中等频次用户（2单）：放弃率中等，分布在各环节
    - 低频次用户（1单）：放弃率高，集中在加购→支付环节（价格敏感）
    """
    from datetime import timedelta as td

    events = []
    event_id = 1

    user_order_counts = orders_df.groupby('user_id')['order_id'].count()

    # ---- 为每个成功订单生成完整行为路径 ----
    for _, order in orders_df.iterrows():
        user_id = order['user_id']
        order_time = pd.Timestamp(order['order_time'])
        product_id = order['product_id']
        session_id = f"sess_{user_id}_{order['order_id']}"

        events.append({
            'id': event_id, 'user_id': user_id, 'event_type': 'page_view',
            'product_id': product_id,
            'event_time': (order_time - td(hours=random.randint(24, 72))).strftime('%Y-%m-%d %H:%M:%S'),
            'session_id': session_id
        }); event_id += 1

        events.append({
            'id': event_id, 'user_id': user_id, 'event_type': 'add_cart',
            'product_id': product_id,
            'event_time': (order_time - td(hours=random.randint(1, 24))).strftime('%Y-%m-%d %H:%M:%S'),
            'session_id': session_id
        }); event_id += 1

        events.append({
            'id': event_id, 'user_id': user_id, 'event_type': 'checkout',
            'product_id': product_id,
            'event_time': (order_time - td(minutes=random.randint(5, 60))).strftime('%Y-%m-%d %H:%M:%S'),
            'session_id': session_id
        }); event_id += 1

        events.append({
            'id': event_id, 'user_id': user_id, 'event_type': 'pay_success',
            'product_id': product_id,
            'event_time': order_time.strftime('%Y-%m-%d %H:%M:%S'),
            'session_id': session_id
        }); event_id += 1

    # ---- 为每个用户生成未转化会话（制造漏斗流失） ----
    for user_id in orders_df['user_id'].unique():
        n_orders = user_order_counts.get(user_id, 0)

        if n_orders >= 3:
            n_abandoned = random.randint(2, 5)
            add_cart_rate = 0.90     # 高频用户：看了大概率加购
            checkout_rate = 0.90     # 加购后大概率支付
        elif n_orders >= 2:
            n_abandoned = random.randint(10, 18)
            add_cart_rate = 0.55
            checkout_rate = 0.35     # 中等用户：加购→支付有明显流失
        else:
            n_abandoned = random.randint(20, 35)
            add_cart_rate = 0.35
            checkout_rate = 0.08     # 低频用户：大量在支付环节流失（价格敏感）

        for i in range(n_abandoned):
            sess_id = f"sess_{user_id}_ab_{i}"
            # 时间窗与订单一致(2024-01 ~ 2026-06),避免漏斗分母与转化事件跨时间错配
            base_time = pd.Timestamp('2024-01-01') + td(days=random.randint(0, 911))
            prod_id = random.randint(1, N_PRODUCTS)

            events.append({
                'id': event_id, 'user_id': user_id, 'event_type': 'page_view',
                'product_id': prod_id,
                'event_time': base_time.strftime('%Y-%m-%d %H:%M:%S'),
                'session_id': sess_id
            }); event_id += 1

            if random.random() < add_cart_rate:
                events.append({
                    'id': event_id, 'user_id': user_id, 'event_type': 'add_cart',
                    'product_id': prod_id,
                    'event_time': (base_time + td(minutes=random.randint(3, 20))).strftime('%Y-%m-%d %H:%M:%S'),
                    'session_id': sess_id
                }); event_id += 1

                if random.random() < checkout_rate:
                    events.append({
                        'id': event_id, 'user_id': user_id, 'event_type': 'checkout',
                        'product_id': prod_id,
                        'event_time': (base_time + td(minutes=random.randint(20, 50))).strftime('%Y-%m-%d %H:%M:%S'),
                        'session_id': sess_id
                    }); event_id += 1
                    # 未转化会话到此结束，不生成 pay_success（已通过订单表覆盖）

    df = pd.DataFrame(events)
    df = df.sort_values('event_time').reset_index(drop=True)
    return df


# ============================================================
# 主入口
# ============================================================
if __name__ == "__main__":
    import os

    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    os.makedirs(data_dir, exist_ok=True)

    users = generate_users()
    products = generate_products()
    orders = generate_orders(users, products)
    behavior_log = generate_behavior_log(orders)

    users.to_csv(os.path.join(data_dir, "users.csv"), index=False)
    products.to_csv(os.path.join(data_dir, "products.csv"), index=False)
    orders.to_csv(os.path.join(data_dir, "orders.csv"), index=False)
    behavior_log.to_csv(os.path.join(data_dir, "behavior_log.csv"), index=False)

    print(f"users:        {len(users)} 行 -> data/users.csv")
    print(f"products:     {len(products)} 行 -> data/products.csv")
    print(f"orders:       {len(orders)} 行 -> data/orders.csv")
    print(f"behavior_log: {len(behavior_log)} 行 -> data/behavior_log.csv")
