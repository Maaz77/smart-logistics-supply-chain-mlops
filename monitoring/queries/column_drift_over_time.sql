-- ============================================
-- Column Drift Score Over Time
-- ============================================
-- This query visualizes the average column drift score over time
-- Use this in Grafana with a Time Series visualization
-- ============================================

SELECT
    timestamp AS time,
    column_drift_score AS value
FROM
    monitoring_metrics
WHERE
    column_drift_score IS NOT NULL
ORDER BY
    timestamp ASC;

-- ============================================
-- Alternative: Group by date (daily average)
-- ============================================
-- If you want to see daily averages instead of individual data points:

-- SELECT
--     date AS time,
--     AVG(column_drift_score) AS value
-- FROM
--     monitoring_metrics
-- WHERE
--     column_drift_score IS NOT NULL
-- GROUP BY
--     date
-- ORDER BY
--     date ASC;

-- ============================================
-- With all metrics for comparison
-- ============================================
-- To see all drift metrics together:

-- SELECT
--     timestamp AS time,
--     column_drift_score AS "Column Drift",
--     dataset_drift_score AS "Dataset Drift",
--     prediction_drift_score AS "Prediction Drift",
--     missing_values_share AS "Missing Values"
-- FROM
--     monitoring_metrics
-- WHERE
--     column_drift_score IS NOT NULL
--     OR dataset_drift_score IS NOT NULL
--     OR prediction_drift_score IS NOT NULL
--     OR missing_values_share IS NOT NULL
-- ORDER BY
--     timestamp ASC;
