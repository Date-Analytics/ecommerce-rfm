"""
数据加载与清洗
"""
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / 'data'


def load_orders(mysql_engine=None):
    """加载订单数据，优先 MySQL，否则读 CSV"""
    if mysql_engine is not None:
        return pd.read_sql(
            "SELECT user_id, order_id, amount, order_time FROM orders WHERE amount > 0",
            mysql_engine, parse_dates=['order_time']
        )
    df = pd.read_csv(DATA_DIR / 'orders.csv', parse_dates=['order_time'])
    return df[df['amount'] > 0].copy()


def load_users(mysql_engine=None):
    if mysql_engine is not None:
        return pd.read_sql("SELECT * FROM users", mysql_engine, parse_dates=['register_time'])
    return pd.read_csv(DATA_DIR / 'users.csv', parse_dates=['register_time'])


def load_products(mysql_engine=None):
    if mysql_engine is not None:
        return pd.read_sql("SELECT * FROM products", mysql_engine)
    return pd.read_csv(DATA_DIR / 'products.csv')


def load_behavior_log(mysql_engine=None):
    if mysql_engine is not None:
        return pd.read_sql("SELECT * FROM behavior_log", mysql_engine, parse_dates=['event_time'])
    return pd.read_csv(DATA_DIR / 'behavior_log.csv', parse_dates=['event_time'])


def clean_orders(df):
    """清洗订单数据：去除金额<=0的异常记录"""
    return df[df['amount'] > 0].copy()


def overview(df_orders, df_users, df_products):
    """打印数据概览"""
    print(f'用户数: {df_users["user_id"].nunique()}')
    print(f'商品数: {df_products["product_id"].nunique()}')
    print(f'订单数: {len(df_orders)}')
    print(f'订单日期范围: {df_orders["order_time"].min()} ~ {df_orders["order_time"].max()}')
    print(f'客单价均值: ¥{df_orders["amount"].mean():.2f}')
    print(f'客单价中位数: ¥{df_orders["amount"].median():.2f}')
    print(f'有下单行为用户数: {df_orders["user_id"].nunique()}')
    return None
