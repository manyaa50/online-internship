-- =====================================================================
-- Database Schema for Smart Online Internship Management System
-- with Automated Scam Prevention
-- Compatible with MySQL 5.7+ / 8.0+ (XAMPP / WAMP / Standalone MySQL)
-- =====================================================================

CREATE DATABASE IF NOT EXISTS `smart_internship_db` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `smart_internship_db`;

SET FOREIGN_KEY_CHECKS = 0;

-- Drop tables in reverse dependency order if recreating
DROP TABLE IF EXISTS `notifications`;
DROP TABLE IF EXISTS `scam_reports`;
DROP TABLE IF EXISTS `applications`;
DROP TABLE IF EXISTS `scam_checks`;
DROP TABLE IF EXISTS `internships`;
DROP TABLE IF EXISTS `internship_categories`;
DROP TABLE IF EXISTS `company_verifications`;
DROP TABLE IF EXISTS `companies`;
DROP TABLE IF EXISTS `resumes`;
DROP TABLE IF EXISTS `student_profiles`;
DROP TABLE IF EXISTS `admins`;
DROP TABLE IF EXISTS `users`;

SET FOREIGN_KEY_CHECKS = 1;

-- -----------------------------------------------------
-- 1. Users Table (Core Auth for all roles)
-- -----------------------------------------------------
CREATE TABLE `users` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `email` VARCHAR(150) NOT NULL UNIQUE,
    `password_hash` VARCHAR(255) NOT NULL,
    `role` ENUM('student', 'company', 'admin') NOT NULL,
    `is_active` BOOLEAN NOT NULL DEFAULT TRUE,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_user_email` (`email`),
    INDEX `idx_user_role` (`role`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------
-- 2. Admin Table
-- -----------------------------------------------------
CREATE TABLE `admins` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL UNIQUE,
    `full_name` VARCHAR(100) NOT NULL,
    `phone` VARCHAR(20) DEFAULT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_admin_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------
-- 3. Student Profile Table
-- -----------------------------------------------------
CREATE TABLE `student_profiles` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL UNIQUE,
    `full_name` VARCHAR(120) NOT NULL,
    `phone` VARCHAR(20) NOT NULL,
    `college_name` VARCHAR(200) DEFAULT NULL,
    `degree` VARCHAR(100) DEFAULT NULL,
    `graduation_year` INT DEFAULT NULL,
    `cgpa` DECIMAL(4,2) DEFAULT NULL,
    `skills` TEXT DEFAULT NULL,
    `bio` TEXT DEFAULT NULL,
    `linkedin_url` VARCHAR(255) DEFAULT NULL,
    `github_url` VARCHAR(255) DEFAULT NULL,
    `preferred_domain` VARCHAR(100) DEFAULT NULL,
    `preferred_location` VARCHAR(100) DEFAULT NULL,
    `preferred_duration` VARCHAR(50) DEFAULT NULL,
    `profile_pic` VARCHAR(255) DEFAULT 'default_avatar.png',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_student_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------
-- 4. Resumes Table
-- -----------------------------------------------------
CREATE TABLE `resumes` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `student_id` INT NOT NULL,
    `filename` VARCHAR(255) NOT NULL,
    `original_name` VARCHAR(255) NOT NULL,
    `file_path` VARCHAR(255) NOT NULL,
    `file_size` INT NOT NULL,
    `is_primary` BOOLEAN DEFAULT TRUE,
    `uploaded_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_resume_student` FOREIGN KEY (`student_id`) REFERENCES `student_profiles` (`id`) ON DELETE CASCADE,
    INDEX `idx_resume_student` (`student_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------
-- 5. Companies Table
-- -----------------------------------------------------
CREATE TABLE `companies` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL UNIQUE,
    `company_name` VARCHAR(150) NOT NULL,
    `website` VARCHAR(255) DEFAULT NULL,
    `official_email` VARCHAR(150) NOT NULL,
    `phone` VARCHAR(20) NOT NULL,
    `address` TEXT DEFAULT NULL,
    `city` VARCHAR(100) DEFAULT NULL,
    `state` VARCHAR(100) DEFAULT NULL,
    `country` VARCHAR(100) DEFAULT 'India',
    `registration_gst_number` VARCHAR(50) DEFAULT NULL,
    `description` TEXT DEFAULT NULL,
    `contact_person_name` VARCHAR(100) DEFAULT NULL,
    `contact_person_designation` VARCHAR(100) DEFAULT NULL,
    `logo` VARCHAR(255) DEFAULT 'default_company.png',
    `verification_status` ENUM('pending', 'approved', 'rejected') DEFAULT 'pending',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_company_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    INDEX `idx_company_verification` (`verification_status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------
-- 6. Company Verification Logs Table
-- -----------------------------------------------------
CREATE TABLE `company_verifications` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `company_id` INT NOT NULL,
    `admin_id` INT DEFAULT NULL,
    `status` ENUM('pending', 'approved', 'rejected') DEFAULT 'pending',
    `review_notes` TEXT DEFAULT NULL,
    `rejection_reason` TEXT DEFAULT NULL,
    `reviewed_at` TIMESTAMP NULL DEFAULT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_verification_company` FOREIGN KEY (`company_id`) REFERENCES `companies` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_verification_admin` FOREIGN KEY (`admin_id`) REFERENCES `admins` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------
-- 7. Internship Categories Table
-- -----------------------------------------------------
CREATE TABLE `internship_categories` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(100) NOT NULL UNIQUE,
    `description` TEXT DEFAULT NULL,
    `icon_class` VARCHAR(50) DEFAULT 'bi bi-briefcase'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------
-- 8. Internships Table
-- -----------------------------------------------------
CREATE TABLE `internships` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `company_id` INT NOT NULL,
    `category_id` INT NOT NULL,
    `title` VARCHAR(150) NOT NULL,
    `description` TEXT NOT NULL,
    `responsibilities` TEXT DEFAULT NULL,
    `eligibility` TEXT NOT NULL,
    `skills_required` TEXT NOT NULL,
    `duration_weeks` INT DEFAULT 8,
    `duration_text` VARCHAR(50) NOT NULL,
    `location_type` ENUM('remote', 'on-site', 'hybrid') DEFAULT 'remote',
    `location_city` VARCHAR(100) DEFAULT NULL,
    `stipend_type` ENUM('paid', 'unpaid', 'performance-based') DEFAULT 'paid',
    `stipend_amount` DECIMAL(10,2) DEFAULT 0.00,
    `stipend_currency` VARCHAR(10) DEFAULT 'INR',
    `openings_count` INT DEFAULT 1,
    `application_deadline` DATE NOT NULL,
    `contact_email` VARCHAR(150) NOT NULL,
    `contact_phone` VARCHAR(20) DEFAULT NULL,
    `status` ENUM('active', 'flagged', 'closed', 'rejected') DEFAULT 'active',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_internship_company` FOREIGN KEY (`company_id`) REFERENCES `companies` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_internship_category` FOREIGN KEY (`category_id`) REFERENCES `internship_categories` (`id`),
    INDEX `idx_internship_status` (`status`),
    INDEX `idx_internship_category` (`category_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------
-- 9. Scam Checks Table (Core AI / Rule Engine Results)
-- -----------------------------------------------------
CREATE TABLE `scam_checks` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `internship_id` INT NOT NULL UNIQUE,
    `risk_score` INT NOT NULL DEFAULT 0,
    `risk_level` ENUM('Low', 'Medium', 'High') NOT NULL DEFAULT 'Low',
    `triggered_rules` LONGTEXT NOT NULL,
    `summary_notes` TEXT DEFAULT NULL,
    `is_reviewed_by_admin` BOOLEAN DEFAULT FALSE,
    `admin_verdict` ENUM('pending', 'approved', 'rejected') DEFAULT 'pending',
    `admin_notes` TEXT DEFAULT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_scam_internship` FOREIGN KEY (`internship_id`) REFERENCES `internships` (`id`) ON DELETE CASCADE,
    INDEX `idx_scam_risk_level` (`risk_level`),
    INDEX `idx_scam_admin_verdict` (`admin_verdict`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------
-- 10. Applications Table
-- -----------------------------------------------------
CREATE TABLE `applications` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `internship_id` INT NOT NULL,
    `student_id` INT NOT NULL,
    `resume_id` INT NOT NULL,
    `cover_letter` TEXT DEFAULT NULL,
    `status` ENUM('Applied', 'Under Review', 'Selected', 'Rejected', 'Completed') DEFAULT 'Applied',
    `company_feedback` TEXT DEFAULT NULL,
    `applied_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY `unique_student_internship_app` (`student_id`, `internship_id`),
    CONSTRAINT `fk_app_internship` FOREIGN KEY (`internship_id`) REFERENCES `internships` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_app_student` FOREIGN KEY (`student_id`) REFERENCES `student_profiles` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_app_resume` FOREIGN KEY (`resume_id`) REFERENCES `resumes` (`id`),
    INDEX `idx_app_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------
-- 11. Scam Reports Table
-- -----------------------------------------------------
CREATE TABLE `scam_reports` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `reported_by_student_id` INT NOT NULL,
    `internship_id` INT DEFAULT NULL,
    `company_id` INT DEFAULT NULL,
    `reason` VARCHAR(150) NOT NULL,
    `description` TEXT NOT NULL,
    `evidence_link` VARCHAR(255) DEFAULT NULL,
    `status` ENUM('open', 'investigating', 'resolved', 'dismissed') DEFAULT 'open',
    `admin_resolution` TEXT DEFAULT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `resolved_at` TIMESTAMP NULL DEFAULT NULL,
    CONSTRAINT `fk_report_student` FOREIGN KEY (`reported_by_student_id`) REFERENCES `student_profiles` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_report_internship` FOREIGN KEY (`internship_id`) REFERENCES `internships` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_report_company` FOREIGN KEY (`company_id`) REFERENCES `companies` (`id`) ON DELETE CASCADE,
    INDEX `idx_report_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------
-- 12. Notifications Table
-- -----------------------------------------------------
CREATE TABLE `notifications` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `user_id` INT NOT NULL,
    `title` VARCHAR(150) NOT NULL,
    `message` TEXT NOT NULL,
    `category` ENUM('application', 'verification', 'scam_alert', 'report', 'admin', 'general') DEFAULT 'general',
    `link_url` VARCHAR(255) DEFAULT NULL,
    `is_read` BOOLEAN DEFAULT FALSE,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_notification_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    INDEX `idx_notification_user_read` (`user_id`, `is_read`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
