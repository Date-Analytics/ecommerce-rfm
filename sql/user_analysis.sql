-- ==========================================
-- 用户分层汇总与业务分析
-- 依赖 rfm_analysis.sql 在同一会话中创建的临时表 rfm_segmented，必须连跑：
--   cat sql/rfm_analysis.sql sql/user_analysis.sql sql/roi_analysis.sql | mysql -u root -p
-- ==========================================

USE ecommerce;

-- ==========================================
-- 1. 分层汇总统计
-- ==========================================
SELECT '===== 分层汇总统计 =====' AS info;

SELECT COUNT(*), SUM(monetary) INTO @total_u, @total_m FROM rfm_segmented;

SELECT
    segment                        AS 用户分层,
    COUNT(*)                       AS 用户数,
    ROUND(COUNT(*) * 100.0 / @total_u, 2) AS 用户占比_pct,
    ROUND(AVG(monetary), 2)        AS 人均消费金额,
    ROUND(SUM(monetary), 2)        AS 总消费贡献,
    ROUND(SUM(monetary) * 100.0 / @total_m, 2) AS 消费贡献占比_pct,
    ROUND(AVG(rfm_score), 2)       AS 平均RFM得分,
    ROUND(AVG(recency), 1)         AS 平均距上次购买天数
FROM rfm_segmented
GROUP BY segment
ORDER BY 总消费贡献 DESC;


-- ==========================================
-- 2. 需召回用户分析（90天未消费）
-- ==========================================
SELECT '===== 需召回用户分析 =====' AS info;

SELECT
    COUNT(*) AS 过去90天未消费用户数,
    ROUND(COUNT(*) * 100.0 / @total_u, 2) AS 占比_pct
FROM rfm_segmented
WHERE recency > 90;


-- ==========================================
-- 3. 核心客户贡献度（帕累托分析）
-- ==========================================
SELECT '===== 核心客户贡献 =====' AS info;

SELECT
    segment              AS 用户分层,
    COUNT(*)             AS 用户数,
    ROUND(SUM(monetary), 2) AS 消费总额,
    ROUND(SUM(monetary) * 100.0 / @total_m, 2) AS 消费占比_pct
FROM rfm_segmented
WHERE segment IN ('核心客户', '需挽留客户')
GROUP BY segment
ORDER BY 消费总额 DESC;
