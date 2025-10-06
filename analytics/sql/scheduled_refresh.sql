-- Example scheduled query for daily refresh.
DECLARE project STRING DEFAULT '${project_id}';

EXECUTE IMMEDIATE FORMAT(
  "INSERT INTO `%s.zen_community_curated.fact_cost_daily`
   SELECT * FROM `%s.zen_community_curated.fact_cost_daily_temp`",
  project, project
);

