-- Toronto 311 service requests, 2023-2025
-- Source: City of Toronto Open Data (Open Government Licence - Toronto)
-- Table: requests (1,351,594 rows)

-- name: q1_monthly_volume
-- Question 1: how does request volume move month to month?
SELECT month,
       COUNT(*) AS requests,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_of_total
FROM requests
GROUP BY month
ORDER BY month;

-- name: q2_top_types
-- Question 2: which request types dominate, and how concentrated is the mix?
WITH ranked AS (
    SELECT request_type,
           COUNT(*) AS requests,
           RANK() OVER (ORDER BY COUNT(*) DESC) AS rnk
    FROM requests
    GROUP BY request_type
)
SELECT request_type,
       requests,
       ROUND(100.0 * requests / (SELECT COUNT(*) FROM requests), 2) AS pct_of_total,
       ROUND(100.0 * SUM(requests) OVER (ORDER BY rnk) /
             (SELECT COUNT(*) FROM requests), 2) AS cumulative_pct
FROM ranked
ORDER BY rnk
LIMIT 15;

-- name: q3_volume_by_ward
-- Question 3: which wards generate the most requests per year?
SELECT ward_code,
       ward,
       COUNT(*) AS requests,
       ROUND(COUNT(*) * 1.0 / COUNT(DISTINCT year), 0) AS avg_per_year
FROM requests
WHERE ward_code IS NOT NULL
GROUP BY ward_code, ward
ORDER BY requests DESC
LIMIT 15;

-- name: q4_status_by_division
-- Question 4: how often are requests cancelled rather than completed, by division?
SELECT division,
       COUNT(*) AS requests,
       ROUND(100.0 * SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) / COUNT(*), 1) AS completed_pct,
       ROUND(100.0 * SUM(CASE WHEN status = 'Cancelled' THEN 1 ELSE 0 END) / COUNT(*), 1) AS cancelled_pct,
       ROUND(100.0 * SUM(CASE WHEN status IN ('New', 'In Progress') THEN 1 ELSE 0 END) / COUNT(*), 1) AS open_pct
FROM requests
WHERE division IS NOT NULL
GROUP BY division
HAVING COUNT(*) > 20000
ORDER BY requests DESC;

-- name: q5_seasonality
-- Question 5: is there a seasonal pattern? Average volume by calendar month.
SELECT CAST(substr(month, 6, 2) AS INTEGER) AS month_number,
       ROUND(AVG(monthly), 0) AS avg_requests_per_month,
       MIN(monthly) AS lowest_year,
       MAX(monthly) AS highest_year
FROM (
    SELECT month, COUNT(*) AS monthly
    FROM requests
    GROUP BY month
)
GROUP BY month_number
ORDER BY month_number;

-- name: q6_hour_of_day
-- Question 6: when during the day do requests arrive?
SELECT hour,
       COUNT(*) AS requests,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct
FROM requests
WHERE hour IS NOT NULL
GROUP BY hour
ORDER BY hour;

-- name: q7_data_quality
-- Question 7: which fields are missing, and how unevenly?
SELECT 'status' AS field, COUNT(*) AS missing, ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM requests), 2) AS pct FROM requests WHERE status IS NULL
UNION ALL SELECT 'ward_code', COUNT(*), ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM requests), 2) FROM requests WHERE ward_code IS NULL
UNION ALL SELECT 'division', COUNT(*), ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM requests), 2) FROM requests WHERE division IS NULL
UNION ALL SELECT 'street_1', COUNT(*), ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM requests), 2) FROM requests WHERE street_1 IS NULL
ORDER BY missing DESC;

-- name: q8_growth_by_division
-- Question 8: which services grew or shrank between 2023 and 2025?
WITH yearly AS (
    SELECT division,
           SUM(CASE WHEN year = 2023 THEN 1 ELSE 0 END) AS y2023,
           SUM(CASE WHEN year = 2025 THEN 1 ELSE 0 END) AS y2025
    FROM requests
    WHERE division IS NOT NULL
    GROUP BY division
)
SELECT division,
       y2023,
       y2025,
       y2025 - y2023 AS change,
       ROUND(100.0 * (y2025 - y2023) / NULLIF(y2023, 0), 1) AS pct_change
FROM yearly
WHERE y2023 >= 1000
ORDER BY pct_change DESC;
