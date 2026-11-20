ALTER TABLE network_speedtests ADD COLUMN sampling_session_id UUID;

ALTER TABLE network_speedtests ADD CONSTRAINT fk_speedtest_sampling_session FOREIGN KEY(sampling_session_id) REFERENCES sampling_sessions (id) ON DELETE RESTRICT;

ALTER TABLE network_speedtests ALTER COLUMN visit_device_id DROP NOT NULL;

ALTER TABLE network_speedtests ADD CONSTRAINT ck_speedtest_one_scope CHECK ((visit_device_id IS NOT NULL AND sampling_session_id IS NULL) OR (visit_device_id IS NULL AND sampling_session_id IS NOT NULL));

CREATE INDEX ix_network_speedtests_sampling_session_id ON network_speedtests (sampling_session_id);
