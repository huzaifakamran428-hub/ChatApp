-- ============================================================
-- ChatApp — MySQL Database Setup Script
-- Run this in MySQL Workbench or MySQL command line FIRST
-- before running Django migrations
-- ============================================================

-- 1. Create the database with full Unicode support (emojis work!)
CREATE DATABASE IF NOT EXISTS chatapp_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

-- 2. (Optional) Create a dedicated user instead of using root
--    Replace 'your_password' with a real password
-- CREATE USER IF NOT EXISTS 'chatapp_user'@'localhost' IDENTIFIED BY 'your_password';
-- GRANT ALL PRIVILEGES ON chatapp_db.* TO 'chatapp_user'@'localhost';
-- FLUSH PRIVILEGES;

-- 3. Verify
SHOW DATABASES LIKE 'chatapp_db';
