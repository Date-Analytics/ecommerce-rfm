-- ==========================================
-- RFM 用户价值分析 SQL（完整版）
-- 运行方式：mysql -u root -p < sql/rfm_analysis.sql
-- ==========================================

USE ecommerce;

-- ==========================================
-- 1. 企业核心指标
-- ==========================================
SELECT '===== 企业核心指标 =====' AS info;

SELECT
    COUNT(DISTINCT user_id)              AS 总用户数,
    SUM(amount)                          AS 总销售额,
    ROUND(AVG(amount), 2)                AS 平均客单价,
    COUNT(DISTINCT order_id)             AS 总订单数,
    ROUND(SUM(amount) / COUNT(DISTINCT order_id), 2) AS 笔单价
FROM orders
WHERE amount > 0;

-- 用户复购率
SELECT
    ROUND(
        SUM(CASE WHEN order_cnt > 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*),
        2
    ) AS 复购率_pct
FROM (
    SELECT user_id, COUNT(DISTINCT order_id) AS order_cnt
    FROM orders
    WHERE amount > 0
    GROUP BY user_id
) t;


-- ==========================================
-- 2. RFM 基础指标计算
-- ==========================================
SELECT '===== RFM 基础指标 =====' AS info;

-- 快照日期：数据最新订单日期 + 1 天
SET @snapshot_date = (SELECT DATE_ADD(MAX(order_time), INTERVAL 1 DAY) FROM orders WHERE amount > 0);
SELECT @snapshot_date AS 快照日期;

-- 计算每个用户的 R/F/M 原始值
DROP TABLE IF EXISTS rfm_base;
CREATE TEMPORARY TABLE rfm_base AS
SELECT
    user_id,
    DATEDIFF(@snapshot_date, MAX(order_time)) AS recency,
    COUNT(DISTINCT order_id)                   AS frequency,
    SUM(amount)                                AS monetary,
    MAX(order_time)                            AS last_order_date,
    ROUND(AVG(amount), 2)                      AS avg_order_amount
FROM orders
WHERE amount > 0
GROUP BY user_id;

SELECT COUNT(*) AS 有购买行为用户数 FROM rfm_base;


-- ==========================================
-- 3. RFM 打分（MySQL 5.7 无窗口函数：先物化排序结果，再顺序扫描打分）
--   R: 越低越好 → 反向打分
--   F: 越高越好 → 正向打分
--   M: 越高越好 → 正向打分
--   注意：用户变量赋值依赖行扫描顺序。若在同一条 SELECT 里用
--   ORDER BY + 用户变量，排序是否生效无保证。必须先落盘排序（两段式），
--   再对已排序的临时表顺序扫描打分。
-- ==========================================
SELECT '===== RFM 打分 =====' AS info;

SELECT COUNT(*) INTO @n FROM rfm_base;

-- R score：recency 升序，排第 1 名的 recency 最小 = 最好，得 5 分
DROP TEMPORARY TABLE IF EXISTS rfm_sorted;
CREATE TEMPORARY TABLE rfm_sorted AS
SELECT user_id, recency FROM rfm_base ORDER BY recency, user_id;
SET @rn := 0;
DROP TEMPORARY TABLE IF EXISTS rfm_r;
CREATE TEMPORARY TABLE rfm_r AS
SELECT user_id, 6 - CEIL((@rn := @rn + 1) * 5.0 / @n) AS r_score
FROM rfm_sorted;

-- F score：frequency 升序，排最后的 frequency 最大 = 最好，得 5 分
DROP TEMPORARY TABLE IF EXISTS rfm_sorted;
CREATE TEMPORARY TABLE rfm_sorted AS
SELECT user_id, frequency FROM rfm_base ORDER BY frequency, user_id;
SET @rn := 0;
DROP TEMPORARY TABLE IF EXISTS rfm_f;
CREATE TEMPORARY TABLE rfm_f AS
SELECT user_id, CEIL((@rn := @rn + 1) * 5.0 / @n) AS f_score
FROM rfm_sorted;

-- M score：monetary 升序，同上
DROP TEMPORARY TABLE IF EXISTS rfm_sorted;
CREATE TEMPORARY TABLE rfm_sorted AS
SELECT user_id, monetary FROM rfm_base ORDER BY monetary, user_id;
SET @rn := 0;
DROP TEMPORARY TABLE IF EXISTS rfm_m;
CREATE TEMPORARY TABLE rfm_m AS
SELECT user_id, CEIL((@rn := @rn + 1) * 5.0 / @n) AS m_score
FROM rfm_sorted;

DROP TEMPORARY TABLE IF EXISTS rfm_sorted;

-- 合并三张 score 表
DROP TEMPORARY TABLE IF EXISTS rfm_scored;
CREATE TEMPORARY TABLE rfm_scored AS
SELECT
    b.user_id,
    b.last_order_date,
    b.recency,
    b.frequency,
    b.monetary,
    b.avg_order_amount,
    r.r_score,
    f.f_score,
    m.m_score
FROM rfm_base b
JOIN rfm_r r ON b.user_id = r.user_id
JOIN rfm_f f ON b.user_id = f.user_id
JOIN rfm_m m ON b.user_id = m.user_id;

SELECT
    MIN(r_score) AS r_min, MAX(r_score) AS r_max,
    MIN(f_score) AS f_min, MAX(f_score) AS f_max,
    MIN(m_score) AS m_min, MAX(m_score) AS m_max
FROM rfm_scored;


-- ==========================================
-- 4. 用户分层
-- ==========================================
SELECT '===== 用户分层 =====' AS info;

DROP TABLE IF EXISTS rfm_segmented;
CREATE TEMPORARY TABLE rfm_segmented AS
SELECT
    user_id,
    last_order_date,
    recency,
    frequency,
    monetary,
    avg_order_amount,
    r_score,
    f_score,
    m_score,
    r_score + f_score + m_score AS rfm_score,
    CASE
        WHEN r_score >= 3 AND f_score >= 3 AND m_score >= 3 THEN '核心客户'
        WHEN r_score >= 3 AND f_score <  3 AND m_score >= 3 THEN '高潜力客户'
        WHEN r_score <  3 AND f_score >= 3 AND m_score >= 3 THEN '需挽留客户'
        WHEN r_score <  3 AND f_score <  3 AND m_score >= 3 THEN '需召回客户'
        WHEN r_score >= 3 AND f_score >= 3 AND m_score <  3 THEN '活跃用户'
        WHEN r_score >= 3 AND f_score <  3 AND m_score <  3 THEN '新晋用户'
        WHEN r_score <  3 AND f_score >= 3 AND m_score <  3 THEN '沉睡用户'
        ELSE '流失用户'
    END AS segment
FROM rfm_scored;

SELECT segment AS 分层, COUNT(*) AS 用户数
FROM rfm_segmented
GROUP BY segment
ORDER BY 用户数 DESC;


-- ==========================================
-- 5. 构建分析宽表（Power BI 数据源）
-- ==========================================
SELECT '===== 构建分析宽表 =====' AS info;

TRUNCATE TABLE user_rfm_analysis;

INSERT INTO user_rfm_analysis
    (user_id, last_order_date, order_count, total_amount,
     avg_order_amount, r_score, f_score, m_score, rfm_score, segment)
SELECT
    user_id,
    last_order_date,
    frequency,
    monetary,
    avg_order_amount,
    r_score,
    f_score,
    m_score,
    rfm_score,
    segment
FROM rfm_segmented;

SELECT COUNT(*) AS 宽表记录数 FROM user_rfm_analysis;

SELECT '===== RFM分析完成 =====' AS info;
