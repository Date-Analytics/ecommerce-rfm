USE ecommerce;

-- 用户表
CREATE TABLE users (
    user_id       INT PRIMARY KEY,
    user_name     VARCHAR(50)  NOT NULL,
    age           TINYINT,
    city          VARCHAR(20),
    register_time DATE
) ENGINE=InnoDB;

-- 商品表
CREATE TABLE products (
    product_id   INT PRIMARY KEY,
    product_name VARCHAR(100) NOT NULL,
    category     VARCHAR(20),
    price        DECIMAL(10, 2)
) ENGINE=InnoDB;

-- 订单表
CREATE TABLE orders (
    order_id    BIGINT PRIMARY KEY,
    user_id     INT,
    product_id  INT,
    quantity    INT,
    amount      DECIMAL(12, 2),
    order_time  DATE,
    INDEX idx_user (user_id),
    INDEX idx_product (product_id),
    INDEX idx_order_time (order_time)
) ENGINE=InnoDB;

-- 用户行为日志表（漏斗分析数据源）
CREATE TABLE behavior_log (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT,
    event_type  VARCHAR(20) NOT NULL,
    product_id  INT,
    event_time  DATETIME,
    session_id  VARCHAR(50),
    INDEX idx_user (user_id),
    INDEX idx_event_type (event_type),
    INDEX idx_user_event (user_id, event_type),
    INDEX idx_event_time (event_time),
    INDEX idx_session (session_id)
) ENGINE=InnoDB;

-- RFM 分析宽表（Power BI 数据源）
CREATE TABLE user_rfm_analysis (
    user_id          INT PRIMARY KEY,
    last_order_date  DATE,
    order_count      INT,
    total_amount     DECIMAL(14, 2),
    avg_order_amount DECIMAL(12, 2),
    r_score          TINYINT,
    f_score          TINYINT,
    m_score          TINYINT,
    rfm_score        INT,
    segment          VARCHAR(20),
    INDEX idx_segment (segment)
) ENGINE=InnoDB;

-- 营销ROI预测结果表
CREATE TABLE marketing_roi (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    analysis_date       DATE NOT NULL,
    target_segment      VARCHAR(100) NOT NULL COMMENT '目标用户群',
    target_users        INT COMMENT '目标用户数',
    avg_spend_est       DECIMAL(12, 2) COMMENT '客单价估算',
    conversion_rate_pct DECIMAL(5, 1) COMMENT '假设转化率(%)',
    expected_conversions INT COMMENT '预计转化人数',
    expected_gmv        DECIMAL(16, 2) COMMENT '预期挽回GMV',
    coupon_cost_per_user DECIMAL(10, 2) COMMENT '单券成本',
    total_coupon_cost   DECIMAL(14, 2) COMMENT '总券成本',
    expected_roi        DECIMAL(6, 2) COMMENT '预期ROI（倍数）',
    net_profit          DECIMAL(14, 2) COMMENT '预期净收益',
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_segment (target_segment),
    INDEX idx_date (analysis_date)
) ENGINE=InnoDB;
