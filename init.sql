-- Tabela principal particionada por mês (histórico 12 meses)
CREATE TABLE IF NOT EXISTS traffic_decision (
    id          BIGSERIAL,
    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    intersection_id VARCHAR(50) NOT NULL,
    action      VARCHAR(50) NOT NULL,
    green_time  INTEGER NOT NULL,
    pressure    DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

-- Partições para os próximos 12 meses (ajuste o ano conforme necessário)
CREATE TABLE IF NOT EXISTS traffic_decision_2025_01 PARTITION OF traffic_decision
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
CREATE TABLE IF NOT EXISTS traffic_decision_2025_02 PARTITION OF traffic_decision
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');
CREATE TABLE IF NOT EXISTS traffic_decision_2025_03 PARTITION OF traffic_decision
    FOR VALUES FROM ('2025-03-01') TO ('2025-04-01');
CREATE TABLE IF NOT EXISTS traffic_decision_2025_04 PARTITION OF traffic_decision
    FOR VALUES FROM ('2025-04-01') TO ('2025-05-01');
CREATE TABLE IF NOT EXISTS traffic_decision_2025_05 PARTITION OF traffic_decision
    FOR VALUES FROM ('2025-05-01') TO ('2025-06-01');
CREATE TABLE IF NOT EXISTS traffic_decision_2025_06 PARTITION OF traffic_decision
    FOR VALUES FROM ('2025-06-01') TO ('2025-07-01');
CREATE TABLE IF NOT EXISTS traffic_decision_2025_07 PARTITION OF traffic_decision
    FOR VALUES FROM ('2025-07-01') TO ('2025-08-01');
CREATE TABLE IF NOT EXISTS traffic_decision_2025_08 PARTITION OF traffic_decision
    FOR VALUES FROM ('2025-08-01') TO ('2025-09-01');
CREATE TABLE IF NOT EXISTS traffic_decision_2025_09 PARTITION OF traffic_decision
    FOR VALUES FROM ('2025-09-01') TO ('2025-10-01');
CREATE TABLE IF NOT EXISTS traffic_decision_2025_10 PARTITION OF traffic_decision
    FOR VALUES FROM ('2025-10-01') TO ('2025-11-01');
CREATE TABLE IF NOT EXISTS traffic_decision_2025_11 PARTITION OF traffic_decision
    FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');
CREATE TABLE IF NOT EXISTS traffic_decision_2025_12 PARTITION OF traffic_decision
    FOR VALUES FROM ('2025-12-01') TO ('2026-01-01');

-- Índice para consultas por cruzamento e data
CREATE INDEX IF NOT EXISTS idx_decision_intersection_date
    ON traffic_decision (intersection_id, created_at DESC);
