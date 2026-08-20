-- ==========================================
-- 营销ROI预估 + 漏斗归因分析
-- 依赖 rfm_analysis.sql 在同一会话中创建的临时表 rfm_segmented
-- 和变量 @snapshot_date，必须按顺序连跑：
--   cat sql/rfm_analysis.sql sql/user_analysis.sql sql/roi_analysis.sql | mysql -u root -p
-- ==========================================

USE ecommerce;

-- ==========================================
-- 1. 运营ROI预估（钱效验证）
-- ==========================================
SELECT '===== 运营ROI预估 =====' AS info;

-- 目标用户：高价值流失预警（需挽留客户 + 需召回客户）
-- GMV 口径与第 3 节一致：一次营销挽回的是一笔订单，用笔单价 × 转化人数
-- 转化人数取 FLOOR（与 Python 链路的 int() 截断一致）
SELECT
    COUNT(*)                                          AS 目标用户数,
    ROUND(AVG(monetary), 2)                           AS 人均历史消费,
    ROUND(AVG(frequency), 1)                          AS 人均购买次数,
    ROUND(FLOOR(COUNT(*) * 0.05) * ROUND(AVG(avg_order_amount), 2), 2) AS 预期挽回GMV_5pct转化率,
    ROUND(FLOOR(COUNT(*) * 0.08) * ROUND(AVG(avg_order_amount), 2), 2) AS 预期挽回GMV_8pct转化率,
    ROUND(FLOOR(COUNT(*) * 0.10) * ROUND(AVG(avg_order_amount), 2), 2) AS 预期挽回GMV_10pct转化率
FROM rfm_segmented
WHERE segment IN ('需挽留客户', '需召回客户');

-- 该类用户近30天活跃度
SELECT
    segment                                          AS 用户分层,
    COUNT(DISTINCT o.user_id)                        AS 近30天有下单人数,
    ROUND(AVG(o.amount), 2)                          AS 近30天人均消费,
    ROUND(SUM(o.amount), 2)                          AS 近30天总消费
FROM rfm_segmented r
LEFT JOIN orders o ON r.user_id = o.user_id
    AND o.order_time >= DATE_SUB(@snapshot_date, INTERVAL 30 DAY)
    AND o.amount > 0
WHERE r.segment IN ('需挽留客户', '需召回客户')
GROUP BY r.segment;


-- ==========================================
-- 2. 漏斗归因分析（RFM 反哺漏斗）
-- ==========================================
SELECT '===== 漏斗归因分析 =====' AS info;

-- 2.1 总体漏斗
SELECT
    event_type                    AS 事件类型,
    COUNT(DISTINCT session_id)    AS 会话数,
    ROUND(COUNT(DISTINCT session_id) * 100.0 /
        (SELECT COUNT(DISTINCT session_id) FROM behavior_log WHERE event_type = 'page_view'), 2
    ) AS 整体转化率_pct
FROM behavior_log
GROUP BY event_type
ORDER BY FIELD(event_type, 'page_view', 'add_cart', 'checkout', 'pay_success');

-- 2.2 环节间流失率
SELECT
    '浏览→加购' AS 环节,
    ROUND((1 - COUNT(DISTINCT CASE WHEN event_type = 'add_cart' THEN session_id END) * 1.0 /
           COUNT(DISTINCT CASE WHEN event_type = 'page_view' THEN session_id END)) * 100, 2) AS 流失率_pct
FROM behavior_log
UNION ALL
SELECT
    '加购→发起支付' AS 环节,
    ROUND((1 - COUNT(DISTINCT CASE WHEN event_type = 'checkout' THEN session_id END) * 1.0 /
           COUNT(DISTINCT CASE WHEN event_type = 'add_cart' THEN session_id END)) * 100, 2)
FROM behavior_log
UNION ALL
SELECT
    '发起支付→支付成功' AS 环节,
    ROUND((1 - COUNT(DISTINCT CASE WHEN event_type = 'pay_success' THEN session_id END) * 1.0 /
           COUNT(DISTINCT CASE WHEN event_type = 'checkout' THEN session_id END)) * 100, 2)
FROM behavior_log;

-- 2.3 RFM分层 × 漏斗交叉透视
SELECT
    COALESCE(r.segment, '未转化浏览用户')              AS 用户分层,
    COUNT(DISTINCT CASE WHEN b.event_type = 'page_view'   THEN b.session_id END) AS 浏览会话,
    COUNT(DISTINCT CASE WHEN b.event_type = 'add_cart'    THEN b.session_id END) AS 加购会话,
    COUNT(DISTINCT CASE WHEN b.event_type = 'checkout'    THEN b.session_id END) AS 支付发起会话,
    COUNT(DISTINCT CASE WHEN b.event_type = 'pay_success' THEN b.session_id END) AS 支付成功会话,
    ROUND(COUNT(DISTINCT CASE WHEN b.event_type = 'add_cart' THEN b.session_id END) * 100.0 /
          NULLIF(COUNT(DISTINCT CASE WHEN b.event_type = 'page_view' THEN b.session_id END), 0), 2) AS 浏览到加购转化率,
    ROUND(COUNT(DISTINCT CASE WHEN b.event_type = 'pay_success' THEN b.session_id END) * 100.0 /
          NULLIF(COUNT(DISTINCT CASE WHEN b.event_type = 'add_cart' THEN b.session_id END), 0), 2) AS 加购到支付转化率
FROM behavior_log b
LEFT JOIN rfm_segmented r ON b.user_id = r.user_id
GROUP BY r.segment
ORDER BY 加购到支付转化率 DESC;

-- 2.4 高价值 vs 普通用户支付环节转化率对比
SELECT
    CASE
        WHEN r.segment IN ('核心客户', '需挽留客户', '高潜力客户') THEN '高价值用户'
        ELSE '普通用户'
    END                                              AS 用户群,
    COUNT(DISTINCT CASE WHEN b.event_type = 'add_cart'    THEN b.session_id END) AS 加购会话,
    COUNT(DISTINCT CASE WHEN b.event_type = 'pay_success' THEN b.session_id END) AS 支付成功会话,
    ROUND(COUNT(DISTINCT CASE WHEN b.event_type = 'pay_success' THEN b.session_id END) * 100.0 /
          NULLIF(COUNT(DISTINCT CASE WHEN b.event_type = 'add_cart' THEN b.session_id END), 0), 2) AS 加购到支付转化率
FROM behavior_log b
LEFT JOIN rfm_segmented r ON b.user_id = r.user_id
WHERE r.segment IS NOT NULL
GROUP BY CASE
    WHEN r.segment IN ('核心客户', '需挽留客户', '高潜力客户') THEN '高价值用户'
    ELSE '普通用户'
END;


-- ==========================================
-- 3. 营销ROI预测表（敏感性分析）
-- ==========================================
SELECT '===== 营销ROI预测 =====' AS info;

SET @analysis_date = CURDATE();
SET @coupon_cost = 20.00;

SELECT COUNT(*) INTO @n_target
FROM rfm_segmented
WHERE segment IN ('需挽留客户', '需召回客户');

-- 客单价口径:目标用户历史单均消费(一次营销挽回的是一笔订单,不是累计消费)
SELECT ROUND(AVG(avg_order_amount), 2) INTO @avg_spend
FROM rfm_segmented
WHERE segment IN ('需挽留客户', '需召回客户');

TRUNCATE TABLE marketing_roi;

-- 转化人数取 FLOOR 截断(与 Python 链路的 int() 一致),保证两链路同口径
INSERT INTO marketing_roi
    (analysis_date, target_segment, target_users, avg_spend_est,
     conversion_rate_pct, expected_conversions, expected_gmv,
     coupon_cost_per_user, total_coupon_cost, expected_roi, net_profit)
SELECT
    @analysis_date,
    '高价值流失预警（需挽留+需召回客户）',
    @n_target,
    @avg_spend,
    rates.rate_pct,
    FLOOR(@n_target * rates.rate_pct / 100),
    ROUND(FLOOR(@n_target * rates.rate_pct / 100) * @avg_spend, 2),
    @coupon_cost,
    @n_target * @coupon_cost,
    ROUND((FLOOR(@n_target * rates.rate_pct / 100) * @avg_spend - @n_target * @coupon_cost)
          / (@n_target * @coupon_cost), 2),
    ROUND(FLOOR(@n_target * rates.rate_pct / 100) * @avg_spend - @n_target * @coupon_cost, 2)
FROM (
    SELECT 3.0 AS rate_pct UNION ALL
    SELECT 5.0 UNION ALL
    SELECT 8.0 UNION ALL
    SELECT 10.0 UNION ALL
    SELECT 12.0 UNION ALL
    SELECT 15.0
) rates;

SELECT
    target_segment       AS 目标用户群,
    target_users         AS 目标人数,
    avg_spend_est        AS 客单价估算,
    CONCAT(conversion_rate_pct, '%') AS 假设转化率,
    expected_conversions AS 预计转化人数,
    expected_gmv         AS 预期GMV,
    total_coupon_cost    AS 券成本,
    expected_roi         AS 预期ROI,
    net_profit           AS 净收益
FROM marketing_roi
ORDER BY conversion_rate_pct;
