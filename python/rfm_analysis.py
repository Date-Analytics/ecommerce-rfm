"""
RFM 模型：打分、分层、可视化
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns
from datetime import timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT

fm._load_fontmanager(try_read_cache=False)
plt.rcParams['font.sans-serif'] = ['WenQuanYi Micro Hei']
plt.rcParams['axes.unicode_minus'] = False
sns.set_style('darkgrid')

SEGMENT_LABELS = {
    '核心客户':  'VIP 专属服务 + 新品优先体验 + 年度回馈活动',
    '高潜力客户': '推荐高附加值商品 + 组合优惠套餐，提升客单价',
    '需挽留客户': '一对一沟通 + 大额专属优惠券 + 会员权益提醒',
    '需召回客户': '定向推送 + 限时大促 + 召回专属折扣',
    '活跃用户':   '引导升级消费 + 关联推荐 + 积分加速',
    '新晋用户':   '新手礼包 + 首单优惠 + 引导收藏加购',
    '沉睡用户':   '低价爆款唤醒 + 短信/App推送 + 签到有礼',
    '流失用户':   '沉默成本评估 + 选择性放弃或最后召回尝试',
}


def compute_rfm(df_orders, snapshot_date=None):
    """计算每个用户的 R/F/M 原始值"""
    if snapshot_date is None:
        snapshot_date = df_orders['order_time'].max() + timedelta(days=1)
    print(f'快照日期: {snapshot_date}')

    rfm = df_orders.groupby('user_id').agg(
        Recency=('order_time', lambda x: (snapshot_date - x.max()).days),
        Frequency=('order_id', 'count'),
        Monetary=('amount', 'sum'),
        last_order_date=('order_time', 'max'),
        avg_order_amount=('amount', 'mean')
    ).reset_index()
    return rfm, snapshot_date


def score_rfm(rfm):
    """先 rank 再 NTILE 五分位打分，R 反向，F/M 正向"""
    rfm = rfm.copy()
    rfm['R_rank'] = rfm['Recency'].rank(method='first')
    rfm['F_rank'] = rfm['Frequency'].rank(method='first')
    rfm['M_rank'] = rfm['Monetary'].rank(method='first')

    rfm['R_Score'] = pd.qcut(rfm['R_rank'], q=5, labels=[5, 4, 3, 2, 1]).astype(int)
    rfm['F_Score'] = pd.qcut(rfm['F_rank'], q=5, labels=[1, 2, 3, 4, 5]).astype(int)
    rfm['M_Score'] = pd.qcut(rfm['M_rank'], q=5, labels=[1, 2, 3, 4, 5]).astype(int)

    rfm.drop(['R_rank', 'F_rank', 'M_rank'], axis=1, inplace=True)
    return rfm


def rfm_segment(row):
    """根据 R/F/M 得分将用户分为 8 个层级"""
    r, f, m = row['R_Score'], row['F_Score'], row['M_Score']
    if r >= 3 and f >= 3 and m >= 3:
        return '核心客户'
    elif r >= 3 and f < 3 and m >= 3:
        return '高潜力客户'
    elif r < 3 and f >= 3 and m >= 3:
        return '需挽留客户'
    elif r < 3 and f < 3 and m >= 3:
        return '需召回客户'
    elif r >= 3 and f >= 3 and m < 3:
        return '活跃用户'
    elif r >= 3 and f < 3 and m < 3:
        return '新晋用户'
    elif r < 3 and f >= 3 and m < 3:
        return '沉睡用户'
    else:
        return '流失用户'


def segment_users(rfm):
    """对用户进行分层并返回带 Segment 列的 DataFrame"""
    rfm = rfm.copy()
    rfm['Segment'] = rfm.apply(rfm_segment, axis=1)
    return rfm


def summarize(rfm):
    """按分层汇总：人数、人均消费、消费贡献占比"""
    total_m = rfm['Monetary'].sum()
    summary = rfm.groupby('Segment').agg(
        用户数=('user_id', 'count'),
        平均消费金额=('Monetary', 'mean'),
        总消费占比=('Monetary', lambda x: round(x.sum() / total_m * 100, 2))
    ).round(2).sort_values('平均消费金额', ascending=False)
    return summary


def plot_all(rfm):
    """生成完整 RFM 可视化图表并保存到项目根目录"""
    plt.close('all')
    fig = plt.figure(figsize=(18, 12))

    # 图1：用户分层占比环形图
    ax1 = fig.add_subplot(2, 2, 1)
    seg_counts = rfm['Segment'].value_counts()
    colors = plt.cm.Set3(np.linspace(0, 1, len(seg_counts)))
    wedges, texts, autotexts = ax1.pie(
        seg_counts.values, labels=seg_counts.index,
        autopct='%1.1f%%', pctdistance=0.78,
        colors=colors, startangle=90, textprops={'fontsize': 9}
    )
    ax1.add_artist(plt.Circle((0, 0), 0.70, fc='white'))
    ax1.set_title('用户分层人数占比', fontsize=14)

    # 图2：各层消费贡献帕累托图
    ax2 = fig.add_subplot(2, 2, 2)
    monetary_sum = rfm.groupby('Segment')['Monetary'].sum().sort_values(ascending=False)
    ax2.bar(monetary_sum.index, monetary_sum.values, color='skyblue', alpha=0.7)
    ax2.set_ylabel('总消费额（元）', fontsize=12)
    ax2.tick_params(axis='x', rotation=30)
    ax2b = ax2.twinx()
    cum_pct = monetary_sum.cumsum() / monetary_sum.sum() * 100
    ax2b.plot(monetary_sum.index, cum_pct, color='red', marker='o', linewidth=2)
    ax2b.set_ylabel('累积占比 (%)', fontsize=12)
    ax2b.set_ylim(0, 110)
    ax2b.axhline(y=80, color='gray', linestyle='--', linewidth=1)
    ax2.set_title('各分层消费贡献与累积占比', fontsize=14)

    # 图3：RFM 散点图（R vs F，颜色/大小 = M）
    ax3 = fig.add_subplot(2, 2, 3)
    scatter = ax3.scatter(
        rfm['R_Score'], rfm['F_Score'],
        c=rfm['M_Score'], cmap='RdYlGn',
        s=rfm['M_Score'] * 30, alpha=0.7, edgecolors='k'
    )
    ax3.set_xlabel('R 得分（越高越活跃）', fontsize=12)
    ax3.set_ylabel('F 得分（购买频次）', fontsize=12)
    ax3.set_title('RFM 分布散点图（颜色/大小 = M 消费金额）', fontsize=14)
    ax3.grid(True)
    cbar = plt.colorbar(scatter, ax=ax3)
    cbar.set_label('M 得分', fontsize=10)

    # 图4：各层平均 RFM 得分
    ax4 = fig.add_subplot(2, 2, 4)
    seg_avg = rfm.groupby('Segment')[['R_Score', 'F_Score', 'M_Score']].mean()
    seg_avg.plot(kind='bar', ax=ax4, colormap='viridis')
    ax4.set_title('各分层平均 RFM 得分', fontsize=14)
    ax4.set_ylabel('平均得分')
    ax4.tick_params(axis='x', rotation=30)
    ax4.legend(['R（活跃度）', 'F（频次）', 'M（金额）'], fontsize=9)

    plt.tight_layout()
    path = OUTPUT_DIR / 'Ecommerce_RFM_Analysis.png'
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.show()
    print(f'图表已保存: {path}')
    return fig


def print_strategies(rfm):
    """打印各层级运营策略"""
    summary = summarize(rfm)
    print('=' * 55)
    for seg in summary.index:
        cnt = int(summary.loc[seg, '用户数'])
        print(f'\n【{seg}】（{cnt} 人）')
        print(f'  策略：{SEGMENT_LABELS.get(seg, "持续观察")}')
    print('\n' + '=' * 55)


if __name__ == '__main__':
    from mysql_connect import get_engine
    from data_clean import load_orders, load_users, load_products, overview

    engine = get_engine()
    df_orders = load_orders(engine)
    df_users = load_users(engine)
    df_products = load_products(engine)
    overview(df_orders, df_users, df_products)

    rfm, snapshot = compute_rfm(df_orders)
    rfm = score_rfm(rfm)
    rfm = segment_users(rfm)

    print('\n分层结果:')
    print(rfm['Segment'].value_counts())
    print('\n分层汇总:')
    print(summarize(rfm))

    plot_all(rfm)
    print_strategies(rfm)
