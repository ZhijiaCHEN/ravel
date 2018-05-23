DROP TABLE IF EXISTS orch;

CREATE TABLE orch (
    app varchar,
    priority int,
    violated boolean,
    PRIMARY KEY (app,
    priority)
);

CREATE view orched_apps as select disdinct app from orch;

CREATE or replace function orch_run() returns void as
$$
declare
    nextApp varchar;
    nextClock int;
begin
    with select * from orch where violated as candidates select app into nextApp from candidates where priority = (select max(priority) from candidates) limit 1;
    select max(counts)+1 into nextClock from clock;
    insert into p_nextApp values (nextClock, true);
end;
$$
language plpgsql;

CREATE or replace function update_violation() returns trigger as
$$
#variable_conflict use_variable
declare
    app varchar;
    vioTable varchar;
    vioStatus boolean;
begin
    for app in (select app from orched_apps) loop
        vioStatus := false;
        if (select count(*) from app_violation where app_violation.app = app) > 0 then
            for vioTable in (select violation from app_violation where app_violation.app = app) loop
                if (select count(*) from vioTable) > 0 then
                    vioStatus := true;
                    break;
                end if;
            end loop;
        else
            if (select count(*) from app_violation) > 0 then
                vioStatus := true;
            end if;
        end if;
        update orch set violated = vioStatus;
    end loop;
end;
$$
language plpgsql;

CREATE or replace function app_action(app varchar) returns trigger as
$$
#variable_conflict use_variable
declare
    vioTable varchar
begin
    if (select count(*) from app_violation where app_violation.app = app) > 0 then
        for vioTable in (select violation from app_violation where app_violation.app = app) loop
            delete from vioTable;
        end loop;
    else
        delete from app_violation;
    end if;
    update p_app set active = false where counts = new.counts;
    perform update_violation();
    perform orch_run();
end;
$$
language plpgsql;

CREATE or replace function load_app() returns trigger as
$$
begin
    drop table if exists p_new.app cascade;
    CREATE table p_new.app
    (
        counts int,
        active boolean,
        PRIMARY KEY(counts)
    );
    
    CREATE trigger activate_new.app after insert on p_new.app
    where new.active
    execute function app_action(new.app);
end;
$$
language plpgsql;

drop trigger add_app if exists on orch;
CREATE trigger add_app after insert on orch
execute function load_app;

CREATE or replace function unload_app() returns trigger as
$$
begin
    drop table if exists p_old.app cascade;
end;
$$
language plpgsql;

drop trigger del_app if exists on orch;
CREATE trigger del_app after delete on orch
execute function unload_app;