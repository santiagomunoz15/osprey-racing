CREATE USER grafana_reader WITH PASSWORD :'reader_password';
GRANT CONNECT ON DATABASE osprey TO grafana_reader;
GRANT USAGE ON SCHEMA public TO grafana_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO grafana_reader;
