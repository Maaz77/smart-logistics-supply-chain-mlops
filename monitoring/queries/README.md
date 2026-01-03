# Grafana SQL Queries

This directory contains SQL queries for visualizing monitoring metrics in Grafana.

## Available Queries

### 1. Column Drift Score Over Time
**File:** `column_drift_over_time.sql`

Visualizes the average column drift score over time. This shows how feature distributions change compared to the training data.

**Usage in Grafana:**
1. Create a new panel
2. Select "Evidently_Monitoring" datasource
3. Switch to "Code" mode (not Builder)
4. Paste the SQL query
5. Set visualization to "Time series"
6. The query returns `time` and `value` columns which Grafana will automatically use

**What it shows:**
- X-axis: Time (timestamp when metrics were logged)
- Y-axis: Column drift score (0-1, where higher = more drift detected)

**Interpretation:**
- **0.0-0.3**: Low drift (data similar to training)
- **0.3-0.7**: Moderate drift (some changes detected)
- **0.7-1.0**: High drift (significant distribution changes)

## Query Variations

The SQL file includes commented alternative queries:
- **Daily averages**: Groups data by date for smoother visualization
- **All metrics comparison**: Shows column drift, dataset drift, prediction drift, and missing values together

## Customizing Queries

You can modify the queries to:
- Filter by date range: Add `WHERE timestamp >= '2024-01-01' AND timestamp <= '2024-12-31'`
- Show specific date range: Use Grafana's time range picker (automatically applied to `$__timeFilter()`)
- Add aggregations: Use `AVG()`, `MAX()`, `MIN()`, etc.
- Group by different time intervals: Use `DATE_TRUNC('hour', timestamp)` or `DATE_TRUNC('day', timestamp)`

## Grafana Time Series Panel Setup

1. **Data Source**: Evidently_Monitoring (PostgreSQL)
2. **Visualization**: Time series
3. **Query Format**: Code (raw SQL)
4. **Time Column**: `time` (must be named `time` for Grafana to recognize it)
5. **Value Column**: `value` (or use aliases like `AS "Column Drift"`)

## Example: Using Grafana's Time Filter

For better integration with Grafana's time range picker, use:

```sql
SELECT
    timestamp AS time,
    column_drift_score AS value
FROM
    monitoring_metrics
WHERE
    $__timeFilter(timestamp)
    AND column_drift_score IS NOT NULL
ORDER BY
    timestamp ASC;
```

The `$__timeFilter(timestamp)` macro automatically applies Grafana's selected time range.
