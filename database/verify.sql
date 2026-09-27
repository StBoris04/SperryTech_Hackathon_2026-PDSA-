select extname, extversion
from pg_extension
where extname in ('postgis', 'timescaledb')
order by extname;

select
    table_name
from information_schema.tables
where table_schema = 'public'
  and table_name in ('utilities', 'projects', 'project_sources')
order by table_name;

select utility_id, utility_name
from public.utilities
order by utility_id;

select
    count(*) as project_count,
    count(*) filter (where review_status = 'validated') as validated_project_count
from public.projects;

select count(*) as opportunity_count
from public.coordination_opportunities;

select
    indexname,
    indexdef
from pg_indexes
where schemaname = 'public'
  and tablename in ('projects', 'project_sources')
order by tablename, indexname;
