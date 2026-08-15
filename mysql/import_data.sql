
USE ecommerce;

-- 导入用户数据
LOAD DATA INFILE 'data/users.csv'
INTO TABLE users
FIELDS TERMINATED BY ','
IGNORE 1 ROWS;

-- 导入商品数据
LOAD DATA INFILE 'data/products.csv'
INTO TABLE products
FIELDS TERMINATED BY ','
IGNORE 1 ROWS;

-- 导入订单数据
LOAD DATA INFILE 'data/orders.csv'
INTO TABLE orders
FIELDS TERMINATED BY ','
IGNORE 1 ROWS;

-- 导入行为日志数据
LOAD DATA INFILE 'data/behavior_log.csv'
INTO TABLE behavior_log
FIELDS TERMINATED BY ','
IGNORE 1 ROWS;
