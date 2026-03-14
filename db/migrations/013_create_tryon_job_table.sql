-- ============================================================
-- Try-On Job Tracking Table
-- ============================================================
-- Stores all try-on generation jobs for status tracking,
-- result caching, and billing purposes.

CREATE TABLE tryon_job (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Job identification
    shop_id INTEGER NOT NULL,
    celery_task_id VARCHAR(255),
    
    -- Job status and timing
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    -- Status: pending, processing, completed, failed
    
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    
    -- Input data
    product_id VARCHAR(255) NOT NULL,
    user_image_url TEXT,
    garment_image_url TEXT,
    category VARCHAR(100) DEFAULT 'upper_body',
    
    -- Result data
    result_image_url TEXT,
    generation_time_ms INTEGER,  -- Time to generate in milliseconds
    
    -- Error handling
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    
    -- Metadata
    ip_address INET,
    user_agent TEXT,
    
    -- Indexes for common queries
    INDEX idx_shop_id (shop_id),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at),
    INDEX idx_shop_status (shop_id, status),
    INDEX idx_completed (created_at DESC) WHERE status = 'completed'
);

-- ============================================================
-- Billing/Plan Tracking Table
-- ============================================================
-- Stores monthly generation limits and usage tracking

CREATE TABLE store_plans (
    shop_id INTEGER PRIMARY KEY,
    
    -- Plan info
    plan_name VARCHAR(100) DEFAULT 'free',  -- free, starter, pro, enterprise
    generation_limit INTEGER DEFAULT 50,    -- Monthly generations allowed
    
    -- Usage tracking
    used_generations INTEGER DEFAULT 0,
    billing_cycle_type VARCHAR(20) DEFAULT 'monthly',
    
    -- Dates
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    cycle_start_date DATE,
    cycle_end_date DATE,
    
    -- Metadata
    payment_status VARCHAR(50),  -- trial, active, overdue, cancelled
    stripe_subscription_id VARCHAR(255),
    
    INDEX idx_plan_name (plan_name),
    INDEX idx_payment_status (payment_status)
);

-- ============================================================
-- Job Queue Status Table
-- ============================================================
-- Tracks overall queue health and metrics

CREATE TABLE queue_metrics (
    id SERIAL PRIMARY KEY,
    
    recorded_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Queue stats
    pending_jobs INTEGER DEFAULT 0,
    processing_jobs INTEGER DEFAULT 0,
    completed_today INTEGER DEFAULT 0,
    failed_today INTEGER DEFAULT 0,
    
    -- Performance
    average_generation_time_ms INTEGER,
    p95_generation_time_ms INTEGER,
    p99_generation_time_ms INTEGER,
    
    -- Infrastructure
    queue_depth INTEGER DEFAULT 0,
    worker_count INTEGER DEFAULT 0,
    
    INDEX idx_recorded_at (recorded_at DESC)
);

-- ============================================================
-- Cleanup Job History
-- ============================================================
-- Archive completed/failed jobs after 30 days

CREATE TABLE tryon_job_archive (
    LIKE tryon_job INCLUDING ALL
);

-- Trigger to archive old jobs (runs daily)
-- SELECT cron.schedule('archive_old_tryon_jobs', '0 2 * * *', 
--     'INSERT INTO tryon_job_archive SELECT * FROM tryon_job 
--      WHERE status IN (''completed'', ''failed'')
--        AND updated_at < NOW() - INTERVAL ''30 days''');

-- ============================================================
-- Audit Trail
-- ============================================================
-- Track all try-on generation attempts for compliance

CREATE TABLE tryon_audit_log (
    id SERIAL PRIMARY KEY,
    
    job_id UUID NOT NULL REFERENCES tryon_job(id) ON DELETE SET NULL,
    shop_id INTEGER NOT NULL,
    
    action VARCHAR(100),  -- created, started, completed, failed, retried
    details JSONB,
    
    created_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_job_id (job_id),
    INDEX idx_shop_id (shop_id),
    INDEX idx_created_at (created_at DESC)
);
