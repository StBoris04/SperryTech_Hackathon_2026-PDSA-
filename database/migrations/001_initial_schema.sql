begin;

create extension if not exists postgis;

create or replace function public.is_valid_partial_date(value text)
returns boolean
language plpgsql
immutable
strict
as $$
begin
    if value ~ '^\d{4}$' then
        perform make_date(value::integer, 1, 1);
    elsif value ~ '^\d{4}-\d{2}$' then
        perform make_date(
            substring(value, 1, 4)::integer,
            substring(value, 6, 2)::integer,
            1
        );
    elsif value ~ '^\d{4}-\d{2}-\d{2}$' then
        perform value::date;
    else
        return false;
    end if;

    return true;
exception
    when others then
        return false;
end;
$$;

create table if not exists public.utilities (
    utility_id text primary key,
    utility_name text not null,
    created_at timestamptz not null default now(),
    constraint utilities_id_not_blank check (btrim(utility_id) <> ''),
    constraint utilities_name_not_blank check (btrim(utility_name) <> '')
);

create table if not exists public.projects (
    project_id text primary key,
    utility_id text not null references public.utilities (utility_id),
    project_name text not null,
    project_type text not null default 'unknown',
    state char(2),
    description text,
    location_text text,
    location geography(point, 4326),
    location_quality text not null default 'unknown',
    location_method text,
    construction_start text,
    construction_end text,
    in_service_date text,
    schedule_text text,
    review_status text not null default 'needs_review',
    notes text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint projects_name_not_blank check (btrim(project_name) <> ''),
    constraint projects_type_allowed check (
        project_type in ('transmission_line', 'substation', 'other', 'unknown')
    ),
    constraint projects_state_format check (
        state is null or state ~ '^[A-Z]{2}$'
    ),
    constraint projects_location_quality_allowed check (
        location_quality in ('verified', 'approximate', 'unknown')
    ),
    constraint projects_location_consistent check (
        (
            location is null
            and location_quality = 'unknown'
        )
        or
        (
            location is not null
            and location_quality in ('verified', 'approximate')
            and nullif(btrim(location_method), '') is not null
        )
    ),
    constraint projects_construction_start_format check (
        construction_start is null
        or public.is_valid_partial_date(construction_start)
    ),
    constraint projects_construction_end_format check (
        construction_end is null
        or public.is_valid_partial_date(construction_end)
    ),
    constraint projects_in_service_date_format check (
        in_service_date is null
        or public.is_valid_partial_date(in_service_date)
    ),
    constraint projects_review_status_allowed check (
        review_status in ('needs_review', 'validated')
    )
);

create table if not exists public.project_sources (
    source_id bigint generated always as identity primary key,
    project_id text not null references public.projects (project_id) on delete cascade,
    reference text not null,
    locator text not null,
    supports text[] not null,
    created_at timestamptz not null default now(),
    constraint project_sources_reference_not_blank check (btrim(reference) <> ''),
    constraint project_sources_locator_not_blank check (btrim(locator) <> ''),
    constraint project_sources_supports_not_empty check (cardinality(supports) > 0),
    constraint project_sources_project_evidence_unique unique (
        project_id,
        reference,
        locator
    )
);

create index if not exists projects_utility_id_idx
    on public.projects (utility_id);

create index if not exists projects_validated_location_idx
    on public.projects using gist (location)
    where review_status = 'validated' and location is not null;

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists projects_set_updated_at on public.projects;

create trigger projects_set_updated_at
before update on public.projects
for each row
execute function public.set_updated_at();

insert into public.utilities (utility_id, utility_name)
values
    ('dominion_sc', 'Dominion Energy South Carolina'),
    ('georgia_power', 'Georgia Power')
on conflict (utility_id) do update
set utility_name = excluded.utility_name;

create or replace view public.coordination_opportunities as
with candidate_pairs as (
    select
        project_a.project_id as project_id_a,
        project_b.project_id as project_id_b,
        project_a.utility_id as utility_id_a,
        project_b.utility_id as utility_id_b,
        project_a.project_name as project_name_a,
        project_b.project_name as project_name_b,
        round(
            (
                st_distance(project_a.location, project_b.location)
                / 1609.344
            )::numeric,
            2
        ) as distance_miles,
        (
            project_a.location_quality = 'approximate'
            or project_b.location_quality = 'approximate'
        ) as location_uncertain,
        project_a.construction_start as construction_start_a,
        project_a.construction_end as construction_end_a,
        project_b.construction_start as construction_start_b,
        project_b.construction_end as construction_end_b
    from public.projects as project_a
    join public.projects as project_b
        on project_a.project_id < project_b.project_id
        and project_a.utility_id <> project_b.utility_id
        and st_dwithin(project_a.location, project_b.location, 40233.6)
    where project_a.review_status = 'validated'
      and project_b.review_status = 'validated'
      and project_a.location is not null
      and project_b.location is not null
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
        when construction_start_a ~ '^\d{4}-\d{2}-\d{2}$'
         and construction_end_a ~ '^\d{4}-\d{2}-\d{2}$'
         and construction_start_b ~ '^\d{4}-\d{2}-\d{2}$'
         and construction_end_b ~ '^\d{4}-\d{2}-\d{2}$'
        then case
            when daterange(
                construction_start_a::date,
                construction_end_a::date,
                '[]'
            ) && daterange(
                construction_start_b::date,
                construction_end_b::date,
                '[]'
            )
            then 'overlap'
            else 'no_overlap'
        end
        else 'unknown'
    end as timeline_status
from candidate_pairs;

comment on view public.coordination_opportunities is
'Validated cross-utility project pairs within 25 miles. Point distances are screening signals, not route-to-route distances.';

commit;
