CREATE TABLE runs (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 file_hash text UNIQUE NOT NULL, name text NOT NULL, started_at timestamptz NOT NULL,
 sample_rate double precision NOT NULL CHECK (sample_rate > 0),
 metadata jsonb NOT NULL, source_timezone text NOT NULL
);
CREATE TABLE channels (
 run_id bigint REFERENCES runs(id), name text NOT NULL, unit text NOT NULL,
 PRIMARY KEY (run_id, name)
);
CREATE TABLE samples (
 run_id bigint NOT NULL, channel text NOT NULL,
 elapsed_s double precision NOT NULL, recorded_at timestamptz NOT NULL,
 value double precision,
 FOREIGN KEY (run_id, channel) REFERENCES channels(run_id,name),
 PRIMARY KEY (run_id, channel, elapsed_s)
);
