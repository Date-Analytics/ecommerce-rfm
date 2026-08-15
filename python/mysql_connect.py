import json
import os
import subprocess
import pymysql
import pandas as pd
from sqlalchemy import create_engine, text

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_CONFIG_FILE = os.path.join(PROJECT_ROOT, 'db_config.json')


def _load_db_credentials():
    """优先读环境变量,其次读项目根目录 db_config.json(不入库)"""
    user = os.environ.get('MYSQL_USER')
    password = os.environ.get('MYSQL_PASSWORD')
    db = os.environ.get('MYSQL_DB')
    if (user is None or db is None) and os.path.exists(DB_CONFIG_FILE):
        with open(DB_CONFIG_FILE, encoding='utf-8') as f:
            cfg = json.load(f)
        user = user or cfg.get('user', 'root')
        password = password if password is not None else cfg.get('password', '')
        db = db or cfg.get('db', 'ecommerce')
    return user or 'root', password or '', db or 'ecommerce'


def _candidate_hosts():
    """收集 Windows 宿主机的候选 IP"""
    hosts = []
    # ip route 默认网关
    for ip_cmd in ['/usr/sbin/ip', '/sbin/ip', 'ip']:
        try:
            result = subprocess.run(
                [ip_cmd, 'route', 'show', 'default'],
                capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.strip().split('\n'):
                parts = line.split()
                if 'via' in parts:
                    hosts.append(parts[parts.index('via') + 1])
            if hosts:
                break
        except Exception:
            continue
    # /proc/net/route
    try:
        with open('/proc/net/route') as f:
            f.readline()
            for line in f:
                fields = line.strip().split()
                if len(fields) >= 3 and fields[1] == '00000000':
                    gw = '.'.join(str(int(fields[2][i:i+2], 16)) for i in (6, 4, 2, 0))
                    hosts.append(gw)
                    break
    except Exception:
        pass
    # resolv.conf
    try:
        with open('/etc/resolv.conf') as f:
            for line in f:
                if line.startswith('nameserver'):
                    ns = line.split()[1]
                    if ns not in hosts:
                        hosts.append(ns)
    except Exception:
        pass
    return hosts


def get_engine(host=None, user=None, password=None, db=None):
    cfg_user, cfg_password, cfg_db = _load_db_credentials()
    user = user or cfg_user
    password = password if password is not None else cfg_password
    db = db or cfg_db
    if host is None:
        # 候选列表 + 已知可用的 IP 兜底
        candidates = _candidate_hosts() + ['127.0.0.1', '127.0.0.1']
        for candidate in candidates:
            try:
                conn = pymysql.connect(
                    host=candidate, user=user, password=password,
                    database=db, connect_timeout=3
                )
                conn.close()
                host = candidate
                break
            except pymysql.err.OperationalError as e:
                if e.args[0] == 1045:  # 密码错误就不重试
                    host = candidate
                    break
                continue
        else:
            host = candidates[0]
    return create_engine(f'mysql+pymysql://{user}:{password}@{host}/{db}')


def read_rfm_data(engine):
    query = """
        SELECT o.user_id,
               o.order_id,
               o.amount,
               o.order_time
        FROM orders o
        WHERE o.amount > 0
    """
    return pd.read_sql(query, engine, parse_dates=['order_time'])


def read_users(engine):
    return pd.read_sql('SELECT * FROM users', engine)


def read_products(engine):
    return pd.read_sql('SELECT * FROM products', engine)


def read_rfm_wide_table(engine):
    """从 user_rfm_analysis 宽表读取 RFM 分析结果"""
    return pd.read_sql('SELECT * FROM user_rfm_analysis ORDER BY rfm_score DESC', engine)


def read_behavior_log(engine):
    """从 behavior_log 表读取用户行为数据"""
    return pd.read_sql('SELECT * FROM behavior_log', engine, parse_dates=['event_time'])


def read_marketing_roi(engine):
    """从 marketing_roi 表读取营销ROI预测结果"""
    return pd.read_sql('SELECT * FROM marketing_roi ORDER BY conversion_rate_pct', engine,
                       parse_dates=['analysis_date', 'created_at'])


def write_marketing_roi(engine, df_roi, n_target, avg_spend, coupon_cost=20.00,
                        target_segment='高价值流失预警（需挽留+需召回客户）'):
    """将营销ROI预测结果写入 marketing_roi 表（替换模式）"""
    import datetime as dt
    df_out = pd.DataFrame({
        'analysis_date': dt.date.today(),
        'target_segment': target_segment,
        'target_users': n_target,
        'avg_spend_est': round(avg_spend, 2),
        'conversion_rate_pct': df_roi['转化率(%)'],
        'expected_conversions': df_roi['预计转化人数'],
        'expected_gmv': df_roi['预期GMV(元)'],
        'coupon_cost_per_user': coupon_cost,
        'total_coupon_cost': df_roi['券成本(元)'],
        'expected_roi': df_roi['预期ROI'],
        'net_profit': df_roi['净收益(元)'],
    })
    with engine.connect() as conn:
        conn.execute(text('TRUNCATE TABLE marketing_roi'))
        conn.commit()
    df_out.to_sql('marketing_roi', engine, if_exists='append', index=False)
    print(f'marketing_roi 写入完成: {len(df_out)} 行')


def write_rfm_wide_table(engine, df_rfm):
    """将 RFM 分析结果写入 user_rfm_analysis 表（替换模式）"""
    cols = {
        'user_id': 'user_id',
        'last_order_date': 'last_order_date',
        'order_count': 'Frequency',
        'total_amount': 'Monetary',
        'avg_order_amount': 'avg_order_amount',
        'r_score': 'R_Score',
        'f_score': 'F_Score',
        'm_score': 'M_Score',
        'segment': 'Segment',
    }
    df_out = df_rfm[list(cols.values())].copy()
    df_out.columns = list(cols.keys())
    df_out['rfm_score'] = df_rfm['R_Score'] + df_rfm['F_Score'] + df_rfm['M_Score']
    with engine.connect() as conn:
        conn.execute(text('TRUNCATE TABLE user_rfm_analysis'))
        conn.commit()
    df_out.to_sql('user_rfm_analysis', engine, if_exists='append', index=False)
    print(f'user_rfm_analysis 写入完成: {len(df_out)} 行')


def import_behavior_log(engine, csv_path='../data/behavior_log.csv'):
    """将 behavior_log.csv 导入 MySQL"""
    df = pd.read_csv(csv_path, parse_dates=['event_time'])
    df.to_sql('behavior_log', engine, if_exists='append', index=False,
              method='multi', chunksize=5000)
    print(f'behavior_log 导入完成: {len(df)} 行')
    return df


def import_all_csv(engine, data_dir='../data'):
    """一键导入全部 CSV 到 MySQL（users/products/orders/behavior_log）"""
    import os
    tables = ['users', 'products', 'orders', 'behavior_log']
    for table in tables:
        path = os.path.join(data_dir, f'{table}.csv')
        if not os.path.exists(path):
            print(f'  {table}: 跳过（文件不存在）')
            continue
        df = pd.read_csv(path)
        if table == 'behavior_log':
            df['event_time'] = pd.to_datetime(df['event_time'])
        elif table in ('orders',):
            df['order_time'] = pd.to_datetime(df['order_time'])
        elif table in ('users',):
            df['register_time'] = pd.to_datetime(df['register_time'])
        # 清空旧数据，防止主键冲突
        with engine.connect() as conn:
            conn.execute(text(f'TRUNCATE TABLE {table}'))
            conn.commit()
        df.to_sql(table, engine, if_exists='append', index=False,
                  method='multi', chunksize=5000)
        print(f'  {table}: {len(df)} 行导入完成')
    print('全部 CSV 导入完毕')


if __name__ == '__main__':
    engine = get_engine()
    df = read_rfm_data(engine)
    print(f'订单数: {len(df)}')
    print(df.head())
