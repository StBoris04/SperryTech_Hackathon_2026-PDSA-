begin;

-- Preserve partial-date text on projects; expand bounds only during analysis.
create or replace function public.partial_date_bound(value text, upper_bound boolean)
returns date
language plpgsql
immutable
strict
as $$
declare
    first_day date;
begin
    if not public.is_valid_partial_date(value) then
        return null;
    end if;
    if length(value) = 4 then
        if upper_bound then
            return make_date(value::integer, 12, 31);
        end if;
        return make_date(value::integer, 1, 1);
    elsif length(value) = 7 then
        first_day := make_date(substring(value, 1, 4)::integer,
                               substring(value, 6, 2)::integer, 1);
        if upper_bound then
            return (first_day + interval '1 month - 1 day')::date;
        end if;
        return first_day;
    end if;
    return value::date;
end;
$$;

create or replace view public.coordination_opportunities as
with candidate_pairs as (
    select
        project_a.project_id as project_id_a,
        project_b.project_id as project_id_b,
        project_a.utility_id as utility_id_a,
        project_b.utility_id as utility_id_b,
        project_a.project_name as project_name_a,
        project_b.project_name as project_name_b,
        -- Keep full precision so displayed rounding cannot change ranking order.
        (st_distance(project_a.location, project_b.location) / 1609.344)::numeric
            as distance_miles,
        (project_a.location_quality = 'approximate'
            or project_b.location_quality = 'approximate') as location_uncertain,
        public.partial_date_bound(project_a.construction_start, false) as start_a,
        public.partial_date_bound(project_a.construction_end, true) as end_a,
        public.partial_date_bound(project_b.construction_start, false) as start_b,
        public.partial_date_bound(project_b.construction_end, true) as end_b
    from public.projects as project_a
    join public.projects as project_b
        on project_a.project_id < project_b.project_id
        and project_a.utility_id <> project_b.utility_id
        and st_dwithin(project_a.location, project_b.location, 40233.6)
    where project_a.review_status = 'validated'
      and project_b.review_status = 'validated'
      and project_a.location is not null
      and project_b.location is not null
      and not exists (
          select 1 from public.project_sources as evidence
          where evidence.project_id in (project_a.project_id, project_b.project_id)
            and evidence.reference = 'synthetic-fixture'
      )
)
select
    project_id_a,
    project_id_b,
    utility_id_a,
    utility_id_b,
    project_name_a,
    project_name_b,
    distance_miles,
    'postgis_geography'::text as distance_method,
    location_uncertain,
    case
        when start_a is null or end_a is null or start_b is null or end_b is null
          or start_a > end_a or start_b > end_b then 'unknown'
        when start_a <= end_b and start_b <= end_a then 'overlap'
        else 'no_overlap'
    end as timeline_status
from candidate_pairs;

comment on view public.coordination_opportunities is
'Validated cross-utility pairs within <=25 miles, excluding synthetic-fixture evidence. Full-precision point distances; inclusive partial-date bounds only inside analysis. Consumers must explicitly order results.';

commit;
