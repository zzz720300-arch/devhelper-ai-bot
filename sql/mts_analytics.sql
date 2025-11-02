CREATE TABLE IF NOT EXISTS mts_analytics_logs (
    id SERIAL PRIMARY KEY,
    trace_id UUID,
    session_id VARCHAR(128),
    user_query TEXT,
    answer TEXT,
    used_tools TEXT,
    duration_ms INT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS mts_analytics_prompts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(128) UNIQUE NOT NULL,
    text TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS mts_analytics_memory (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(128) NOT NULL,
    role VARCHAR(16) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

