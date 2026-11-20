-- REVIEW ONLY. Do not execute outside the reviewed migration workflow.

-- Review only: 0010_sampling_foundation
CREATE TABLE hotel_floors (
    id UUID NOT NULL,
    hotel_id UUID NOT NULL,
    name VARCHAR(100) NOT NULL,
    position INTEGER NOT NULL,
    default_sampling_count INTEGER DEFAULT '4' NOT NULL,
    version INTEGER DEFAULT '1' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    archived_at TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (id),
    CONSTRAINT ck_floor_name CHECK (btrim(name) <> ''),
    CONSTRAINT ck_floor_position CHECK (position >= 0),
    CONSTRAINT ck_floor_target CHECK (default_sampling_count > 0),
    CONSTRAINT ck_floor_version CHECK (version >= 1),
    FOREIGN KEY(hotel_id) REFERENCES hotels (id) ON DELETE RESTRICT
);

CREATE TABLE sampling_points (
    id UUID NOT NULL,
    floor_id UUID NOT NULL,
    name VARCHAR(200) NOT NULL,
    location TEXT,
    position INTEGER NOT NULL,
    device_id UUID,
    version INTEGER DEFAULT '1' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    archived_at TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (id),
    CONSTRAINT ck_point_name CHECK (btrim(name) <> ''),
    CONSTRAINT ck_point_position CHECK (position >= 0),
    CONSTRAINT ck_point_version CHECK (version >= 1),
    FOREIGN KEY(floor_id) REFERENCES hotel_floors (id) ON DELETE RESTRICT,
    FOREIGN KEY(device_id) REFERENCES devices (id) ON DELETE RESTRICT
);

CREATE TABLE sampling_coverages (
    id UUID NOT NULL,
    hotel_visit_id UUID NOT NULL,
    period DATE NOT NULL,
    hotel_snapshot JSONB NOT NULL,
    photo_policy_snapshot JSONB NOT NULL,
    schema_version INTEGER DEFAULT '1' NOT NULL,
    created_by UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_coverage_visit UNIQUE (hotel_visit_id),
    CONSTRAINT ck_coverage_period CHECK (EXTRACT(DAY FROM period) = 1),
    CONSTRAINT ck_coverage_schema_version CHECK (schema_version = 1),
    FOREIGN KEY(hotel_visit_id) REFERENCES hotel_visits (id) ON DELETE RESTRICT,
    FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE TABLE sampling_coverage_floors (
    id UUID NOT NULL,
    coverage_id UUID NOT NULL,
    floor_id UUID NOT NULL,
    name_snapshot VARCHAR(100) NOT NULL,
    position_snapshot INTEGER NOT NULL,
    target_count INTEGER NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_coverage_floor UNIQUE (coverage_id, floor_id),
    CONSTRAINT uq_coverage_floor_scope UNIQUE (id, coverage_id),
    CONSTRAINT ck_coverage_floor_name CHECK (btrim(name_snapshot) <> ''),
    CONSTRAINT ck_coverage_floor_position CHECK (position_snapshot >= 0),
    CONSTRAINT ck_coverage_floor_target CHECK (target_count > 0),
    FOREIGN KEY(coverage_id) REFERENCES sampling_coverages (id) ON DELETE RESTRICT,
    FOREIGN KEY(floor_id) REFERENCES hotel_floors (id) ON DELETE RESTRICT
);

CREATE TABLE sampling_sessions (
    id UUID NOT NULL,
    coverage_id UUID NOT NULL,
    coverage_floor_id UUID NOT NULL,
    sampling_point_id UUID NOT NULL,
    point_snapshot JSONB NOT NULL,
    position_snapshot INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'untested' NOT NULL,
    version INTEGER DEFAULT '1' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    observed_at TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (id),
    CONSTRAINT fk_session_coverage_floor FOREIGN KEY(coverage_floor_id, coverage_id) REFERENCES sampling_coverage_floors (id, coverage_id) ON DELETE RESTRICT,
    CONSTRAINT uq_session_point UNIQUE (coverage_id, sampling_point_id),
    CONSTRAINT ck_session_position CHECK (position_snapshot >= 0),
    CONSTRAINT ck_session_version CHECK (version >= 1),
    CONSTRAINT ck_session_status CHECK (status IN ('untested', 'good', 'attention', 'problem')),
    FOREIGN KEY(coverage_id) REFERENCES sampling_coverages (id) ON DELETE RESTRICT,
    FOREIGN KEY(sampling_point_id) REFERENCES sampling_points (id) ON DELETE RESTRICT
);

CREATE UNIQUE INDEX uq_hotel_floors_active_name ON hotel_floors (hotel_id, lower(btrim(name))) WHERE archived_at IS NULL;

CREATE INDEX ix_hotel_floors_active_order ON hotel_floors (hotel_id, position, id) WHERE archived_at IS NULL;

CREATE UNIQUE INDEX uq_sampling_points_active_name ON sampling_points (floor_id, lower(btrim(name))) WHERE archived_at IS NULL;

CREATE INDEX ix_sampling_points_active_order ON sampling_points (floor_id, position, id) WHERE archived_at IS NULL;

CREATE INDEX ix_hotel_floors_hotel_id ON hotel_floors (hotel_id);

CREATE INDEX ix_sampling_points_floor_id ON sampling_points (floor_id);

CREATE INDEX ix_sampling_points_device_id ON sampling_points (device_id);

CREATE INDEX ix_sampling_coverages_created_by ON sampling_coverages (created_by);

CREATE INDEX ix_sampling_coverage_floors_floor_id ON sampling_coverage_floors (floor_id);

CREATE INDEX ix_sampling_sessions_coverage_floor_id_coverage_id ON sampling_sessions (coverage_floor_id, coverage_id);

CREATE INDEX ix_sampling_sessions_sampling_point_id ON sampling_sessions (sampling_point_id);

CREATE INDEX ix_sampling_sessions_coverage_id_status ON sampling_sessions (coverage_id, status);


-- Review only: 0011_sampling_observations
CREATE TABLE sampling_observations (
    id UUID NOT NULL,
    session_id UUID NOT NULL,
    actor_id UUID NOT NULL,
    session_version INTEGER NOT NULL,
    visit_version INTEGER NOT NULL,
    captured_at TIMESTAMP WITH TIME ZONE NOT NULL,
    received_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    payload JSONB NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_observation_session_version UNIQUE (session_id, session_version),
    CONSTRAINT ck_observation_session_version CHECK (session_version >= 2),
    CONSTRAINT ck_observation_visit_version CHECK (visit_version >= 1),
    FOREIGN KEY(session_id) REFERENCES sampling_sessions (id) ON DELETE RESTRICT,
    FOREIGN KEY(actor_id) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE INDEX ix_sampling_observations_actor_id ON sampling_observations (actor_id);


-- Review only: 0012_sampling_speedtest_attempts
CREATE TABLE sampling_speedtest_attempts (
    id UUID NOT NULL,
    session_id UUID NOT NULL,
    run_id UUID,
    actor_id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    failure_reason TEXT,
    request_payload JSONB NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT ck_sampling_speedtest_evidence CHECK ((run_id IS NOT NULL AND failure_reason IS NULL) OR (run_id IS NULL AND failure_reason IS NOT NULL AND length(trim(failure_reason)) > 0)),
    FOREIGN KEY(session_id) REFERENCES sampling_sessions (id) ON DELETE RESTRICT,
    UNIQUE (run_id),
    FOREIGN KEY(run_id) REFERENCES network_speedtests (id) ON DELETE RESTRICT,
    FOREIGN KEY(actor_id) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE INDEX ix_sampling_speedtest_attempts_session_id ON sampling_speedtest_attempts (session_id);

CREATE INDEX ix_sampling_speedtest_attempts_actor_id ON sampling_speedtest_attempts (actor_id);
