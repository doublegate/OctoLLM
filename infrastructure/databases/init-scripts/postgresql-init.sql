-- PostgreSQL Initialization Script
-- Run this after Cloud SQL instance is created

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For fuzzy text search
CREATE EXTENSION IF NOT EXISTS "btree_gin";  -- For indexed JSON queries

-- Create application user (if not created by Terraform)
-- CREATE USER octollm WITH PASSWORD '<secure-password>';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE octollm TO octollm;

-- Create schemas
CREATE SCHEMA IF NOT EXISTS memory;
CREATE SCHEMA IF NOT EXISTS tasks;
CREATE SCHEMA IF NOT EXISTS provenance;

-- Grant schema permissions
GRANT ALL ON SCHEMA memory TO octollm;
GRANT ALL ON SCHEMA tasks TO octollm;
GRANT ALL ON SCHEMA provenance TO octollm;

-- Create tables (from docs/implementation/memory-systems.md)

-- Global Knowledge Graph
CREATE TABLE IF NOT EXISTS memory.entities (
    entity_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_type VARCHAR(50) NOT NULL,  -- 'concept', 'tool', 'pattern', etc.
    name VARCHAR(255) NOT NULL,
    description TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS memory.relationships (
    relationship_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id UUID REFERENCES memory.entities(entity_id) ON DELETE CASCADE,
    target_id UUID REFERENCES memory.entities(entity_id) ON DELETE CASCADE,
    relationship_type VARCHAR(50) NOT NULL,  -- 'uses', 'requires', 'implements', etc.
    weight FLOAT DEFAULT 1.0,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Task History
CREATE TABLE IF NOT EXISTS tasks.task_history (
    task_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255),
    goal TEXT NOT NULL,
    constraints JSONB,
    context JSONB,
    status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'running', 'completed', 'failed'
    result JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_ms INTEGER
);

-- Action Log (provenance tracking)
CREATE TABLE IF NOT EXISTS provenance.action_log (
    action_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID REFERENCES tasks.task_history(task_id) ON DELETE CASCADE,
    arm_id VARCHAR(50) NOT NULL,
    action_type VARCHAR(50) NOT NULL,
    input JSONB,
    output JSONB,
    confidence FLOAT,
    execution_time_ms INTEGER,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_entities_type ON memory.entities(entity_type);
CREATE INDEX idx_entities_name ON memory.entities USING gin(name gin_trgm_ops);
CREATE INDEX idx_relationships_source ON memory.relationships(source_id);
CREATE INDEX idx_relationships_target ON memory.relationships(target_id);
CREATE INDEX idx_task_history_user ON tasks.task_history(user_id);
CREATE INDEX idx_task_history_status ON tasks.task_history(status);
CREATE INDEX idx_task_history_created ON tasks.task_history(created_at DESC);
CREATE INDEX idx_action_log_task ON provenance.action_log(task_id);
CREATE INDEX idx_action_log_arm ON provenance.action_log(arm_id);
CREATE INDEX idx_action_log_timestamp ON provenance.action_log(timestamp DESC);

-- Verify installation
SELECT version();
SELECT * FROM pg_extension WHERE extname IN ('uuid-ossp', 'pg_trgm', 'btree_gin');
