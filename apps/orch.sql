DROP TABLE IF EXISTS orch CASCADE;
CREATE TABLE orch (
    app varchar,
    priority int,
    PRIMARY KEY (app,
    priority)
);

CREATE OR REPLACE view orched_apps as select distinct app from orch;

CREATE OR REPLACE FUNCTION get_violation_status()
RETURNS TABLE (
    app VARCHAR,
    violated BOOLEAN
) AS
    $$
    #variable_conflict use_variable
    declare
        vioTable varchar;
    begin
        for app in (select orched_apps.app from orched_apps) loop
            violated := FALSE;
            if (select count(*) from app_violation where app_violation.app = app) > 0 then
                for vioTable in (select violation from app_violation where app_violation.app = app) loop
                    EXECUTE format('SELECT (SELECT COUNT(*) FROM %I) > 0', vioTable) INTO violated;
                    if violated then
                        EXIT;
                    end if;
                end loop;
            else
                EXECUTE format('SELECT (SELECT COUNT(*) FROM %I) > 0', app || '_violation') INTO violated;
            end if;
            RETURN NEXT;
        end loop;
    end;
    $$
LANGUAGE PLPGSQL;

CREATE OR REPLACE VIEW violation_status AS SELECT * FROM get_violation_status();


CREATE or replace function orch_run() returns void as
    $$
    declare
        nextApp varchar;
        nextClock int;
    begin
        with candidates as (select orch.app, priority, violated from orch INNER JOIN violation_status ON orch.app = violation_status.app where violated) select app into nextApp from candidates where priority = (select max(priority) from candidates) limit 1;
        IF nextApp IS NOT NULL THEN
            select max(counts)+1 into nextClock from clock;
            EXECUTE format('INSERT INTO %I VALUES ($1, $2)', 'p_'|| nextApp) USING nextClock, True;
        END IF;
    end;
    $$
language plpgsql;

CREATE or replace function app_action() returns trigger as
    $$
    declare
        vioTable varchar;
    begin
        if (select count(*) from app_violation where app = TG_ARGV[0]) > 0 then
            for vioTable in (select violation from app_violation where app = TG_ARGV[0]) loop
                EXECUTE format('delete from %I;', vioTable);
            end loop;
        else
            EXECUTE format('delete from %I;', TG_ARGV[0] || '_violation');
        end if;
        EXECUTE format('UPDATE %I set active = FALSE WHERE counts = %s', 'p_' || TG_ARGV[0], NEW.counts);
        INSERT INTO clock VALUES(NEW.counts);
        perform orch_run();
        RETURN NULL;
    end;
    $$
language plpgsql;

CREATE or replace function load_app() returns trigger as
    $$
    DECLARE
        loadSql VARCHAR;
    begin
        loadSql :=
            'DROP TABLE IF EXISTS %1$I CASCADE;' || 
            'CREATE TABLE %1$I
            (
                counts int,
                active boolean,
                PRIMARY KEY(counts)
            );' ||
            'CREATE trigger %2$s AFTER INSERT ON %1$I FOR EACH ROW WHEN (NEW.active) EXECUTE PROCEDURE app_action(%3$s);';
        EXECUTE format(loadSql, 'p_' || NEW.app, 'activate_' || NEW.app, NEW.app);
        RETURN NULL;
    end;
    $$
language plpgsql;

drop trigger if exists add_app on orch;
CREATE trigger add_app after insert on orch
FOR EACH ROW
execute PROCEDURE load_app();

CREATE or replace function unload_app() returns trigger as
    $$
    begin
        EXECUTE format('DROP TABLE IF EXISTS %I CASCADE;', 'p_' || OLD.app);
        RETURN NULL;
    end;
    $$
language plpgsql;

drop trigger if exists del_app on orch;
CREATE trigger del_app after delete on orch
execute PROCEDURE unload_app();