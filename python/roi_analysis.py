"""
营销ROI预估 + 漏斗归因分析
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

fm._load_fontmanager(try_read_cache=False)
plt.rcParams['font.sans-serif'] = ['WenQuanYi Micro Hei']
plt.rcParams['axes.unicode_minus'] = False


def calc_roi(rfm, coupon_cost=20.00):
    """
    敏感性分析：不同转化率下的营销ROI
    目标用户：需挽留客户 + 需召回客户
    人均挽回额用客单价（单均消费），而非累计消费：一次营销挽回的是一笔订单
    """
    target = rfm[rfm['Segment'].isin(['需挽留客户', '需召回客户'])]
    n_target = len(target)
    avg_spend = target['avg_order_amount'].mean()

    rates = [3.0, 5.0, 8.0, 10.0, 12.0, 15.0]
    results = []
    for rate in rates:
        conversions = int(n_target * rate / 100)
        expected_gmv = conversions * avg_spend
        total_cost = n_target * coupon_cost
        roi = (expected_gmv - total_cost) / total_cost if total_cost > 0 else 0
        net_profit = expected_gmv - total_cost
        results.append({
            '转化率(%)': rate,
            '预计转化人数': conversions,
            '预期GMV(元)': round(expected_gmv, 2),
            '券成本(元)': round(total_cost, 2),
            '预期ROI': round(roi, 2),
            '净收益(元)': round(net_profit, 2),
        })

    df_roi = pd.DataFrame(results)
    print(f'目标用户数: {n_target}')
    print(f'人均历史消费: ¥{avg_spend:,.2f}')
    print(f'单券成本: ¥{coupon_cost:,.2f}')
    print(df_roi.to_string(index=False))
    return df_roi, n_target, avg_spend


def plot_roi(df_roi):
    """ROI敏感性分析折线图"""
    fig, ax1 = plt.subplots(figsize=(10, 5))

    ax1.plot(df_roi['转化率(%)'], df_roi['预期GMV(元)'], 'b-o', linewidth=2, label='预期GMV')
    ax1.set_xlabel('转化率 (%)', fontsize=12)
    ax1.set_ylabel('预期GMV (元)', fontsize=12, color='b')
    ax1.tick_params(axis='y', labelcolor='b')

    ax2 = ax1.twinx()
    ax2.plot(df_roi['转化率(%)'], df_roi['预期ROI'], 'r-s', linewidth=2, label='预期ROI')
    ax2.set_ylabel('预期ROI', fontsize=12, color='r')
    ax2.tick_params(axis='y', labelcolor='r')
    ax2.axhline(y=1, color='gray', linestyle='--', linewidth=1, label='ROI = 1 (盈亏平衡)')

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')

    ax1.set_title('营销ROI敏感性分析：转化率 vs GMV / ROI', fontsize=14)
    plt.tight_layout()
    path = PROJECT_ROOT / 'roi_sensitivity.png'
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.show()
    print(f'图表已保存: {path}')


def funnel_analysis(df_behavior, rfm=None):
    """
    漏斗分析：
    1. 总体漏斗转化率
    2. 各环节流失率
    3. RFM分层 × 漏斗交叉（如果提供了 rfm）
    """
    # 总体漏斗
    event_order = ['page_view', 'add_cart', 'checkout', 'pay_success']
    funnel = df_behavior[df_behavior['event_type'].isin(event_order)]
    funnel_sessions = funnel.groupby('event_type')['session_id'].nunique()

    print('===== 总体漏斗 =====')
    total_sessions = funnel_sessions.get('page_view', 1)
    for event in event_order:
        sessions = funnel_sessions.get(event, 0)
        rate = sessions / total_sessions * 100 if total_sessions > 0 else 0
        print(f'  {event}: {sessions} 会话 ({rate:.2f}%)')

    # 环节流失率
    print('\n===== 环节流失率 =====')
    steps = [
        ('浏览→加购', 'page_view', 'add_cart'),
        ('加购→发起支付', 'add_cart', 'checkout'),
        ('发起支付→支付成功', 'checkout', 'pay_success'),
    ]
    for label, from_evt, to_evt in steps:
        from_s = funnel_sessions.get(from_evt, 0)
        to_s = funnel_sessions.get(to_evt, 0)
        loss = (1 - to_s / from_s) * 100 if from_s > 0 else 0
        print(f'  {label}: 流失率 {loss:.2f}%')

    # RFM 分层 × 漏斗交叉
    if rfm is not None:
        print('\n===== RFM分层 × 漏斗交叉 =====')
        merged = df_behavior.merge(rfm[['user_id', 'Segment']], on='user_id', how='left')
        merged['Segment'] = merged['Segment'].fillna('未转化浏览用户')

        pivot = merged.pivot_table(
            index='Segment',
            columns='event_type',
            values='session_id',
            aggfunc='nunique',
            fill_value=0
        )
        # 计算转化率
        if 'page_view' in pivot.columns and 'add_cart' in pivot.columns:
            pivot['浏览→加购转化率'] = (
                pivot['add_cart'] / pivot['page_view'].replace(0, np.nan) * 100
            ).round(2)
        if 'add_cart' in pivot.columns and 'pay_success' in pivot.columns:
            pivot['加购→支付转化率'] = (
                pivot['pay_success'] / pivot['add_cart'].replace(0, np.nan) * 100
            ).round(2)

        # 只保留存在的 event_type 列
        keep_cols = [c for c in event_order if c in pivot.columns]
        rate_cols = [c for c in ['浏览→加购转化率', '加购→支付转化率'] if c in pivot.columns]
        print(pivot[keep_cols + rate_cols].sort_values(
            '加购→支付转化率' if '加购→支付转化率' in pivot.columns else keep_cols[0],
            ascending=False
        ).to_string())

        # 高价值 vs 普通用户对比
        print('\n===== 高价值用户 vs 普通用户 =====')
        merged['用户群'] = merged['Segment'].apply(
            lambda s: '高价值用户' if s in ['核心客户', '需挽留客户', '高潜力客户'] else '普通用户'
        )
        if 'pay_success' in merged['event_type'].values and 'add_cart' in merged['event_type'].values:
            compare = merged.pivot_table(
                index='用户群',
                columns='event_type',
                values='session_id',
                aggfunc='nunique',
                fill_value=0
            )
            compare_cols = [c for c in ['add_cart', 'pay_success'] if c in compare.columns]
            if compare_cols:
                compare['加购→支付转化率'] = (
                    compare.get('pay_success', 0) / compare.get('add_cart', 1).replace(0, np.nan) * 100
                ).round(2)
                print(compare[compare_cols + ['加购→支付转化率']].to_string())


def plot_funnel_comparison(rfm, df_behavior):
    """漏斗归因对比图"""
    merged = df_behavior.merge(rfm[['user_id', 'Segment']], on='user_id', how='left')
    merged['Segment'] = merged['Segment'].fillna('未转化浏览用户')
    merged['用户群'] = merged['Segment'].apply(
        lambda s: '高价值用户' if s in ['核心客户', '需挽留客户', '高潜力客户'] else '普通用户'
    )

    event_order = ['page_view', 'add_cart', 'checkout', 'pay_success']
    event_cn = ['浏览', '加购', '支付发起', '支付成功']

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    for ax, group in [(axes[0], '高价值用户'), (axes[1], '普通用户')]:
        subset = merged[merged['用户群'] == group]
        sessions = []
        for evt in event_order:
            sessions.append(subset[subset['event_type'] == evt]['session_id'].nunique())
        ax.bar(event_cn, sessions, color=['#5B9BD5', '#ED7D31', '#A5A5A5', '#70AD47'])
        for i, v in enumerate(sessions):
            if i > 0 and sessions[i - 1] > 0:
                cv = f'{v / sessions[i - 1] * 100:.1f}%'
                ax.annotate(cv, (i, v), textcoords="offset points", xytext=(0, 8), ha='center', fontsize=9)
        ax.set_title(f'{group} - 漏斗', fontsize=13)
        ax.set_ylabel('会话数')

    plt.tight_layout()
    path = PROJECT_ROOT / 'rfm_funnel_attribution.png'
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.show()
    print(f'图表已保存: {path}')


if __name__ == '__main__':
    from mysql_connect import get_engine, write_rfm_wide_table, write_marketing_roi
    from data_clean import load_orders, load_behavior_log
    from rfm_analysis import compute_rfm, score_rfm, segment_users

    engine = get_engine()
    df_orders = load_orders(engine)
    df_behavior = load_behavior_log(engine)

    rfm, _ = compute_rfm(df_orders)
    rfm = score_rfm(rfm)
    rfm = segment_users(rfm)

    df_roi, n_target, avg_spend = calc_roi(rfm)
    plot_roi(df_roi)

    funnel_analysis(df_behavior, rfm)
    plot_funnel_comparison(rfm, df_behavior)

    write_rfm_wide_table(engine, rfm)
    write_marketing_roi(engine, df_roi, n_target, avg_spend)
