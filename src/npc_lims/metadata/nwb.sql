-- sqlite
CREATE TABLE IF NOT EXISTS
  subjects (
    subject_id INT PRIMARY KEY,
    sex CHAR(1) CHECK (sex IN ('M', 'F', 'U')),
    date_of_birth DATE,
    genotype TEXT,
    description TEXT,
    strain TEXT,
    notes TEXT
  );

CREATE TABLE IF NOT EXISTS
  devices (
    device_id INTEGER PRIMARY KEY, -- serial number
    description TEXT DEFAULT 'Neuropixels 1.0',
    manufacturer TEXT DEFAULT 'IMEC'
  );

CREATE TABLE IF NOT EXISTS
  ccf_regions (ccf_region_id TEXT PRIMARY KEY);

CREATE TABLE IF NOT EXISTS
  sessions (
    session_id VARCHAR(30) PRIMARY KEY,
    subject_id INTEGER,
    session_start_time DATETIME, --
    stimulus_notes TEXT, -- task name
    experimenter TEXT,
    experiment_description TEXT, -- < add rig here
    epoch_tags JSON,
    source_script TEXT,
    identifier VARCHAR(36), -- uuid4 w hyphens
    notes TEXT,
    -- pharmacology TEXT,
    -- invalid_times JSON,
    FOREIGN KEY (subject_id) REFERENCES subjects (subject_id)
  );

CREATE TABLE IF NOT EXISTS
  data_assets (
    data_asset_id VARCHAR(36) PRIMARY KEY, -- uuid4
    session_id VARCHAR(30),
    name TEXT,
    description TEXT -- e.g. 'raw ephys data'
  );

CREATE TABLE IF NOT EXISTS
  files (
    session_id VARCHAR(30),
    name TEXT,
    suffix TEXT,
    size INTEGER,
    timestamp DATETIME,
    s3_path TEXT,
    allen_path TEXT,
    data_asset_id TEXT,
    notes TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions (session_id),
    FOREIGN KEY (data_asset_id) REFERENCES data_assets (data_asset_id),
    UNIQUE (session_id, name, suffix, timestamp)
  );

CREATE TABLE IF NOT EXISTS
  folders (
    session_id VARCHAR(30),
    name TEXT,
    timestamp DATETIME,
    s3_path TEXT,
    allen_path TEXT,
    data_asset_id TEXT,
    notes TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions (session_id),
    FOREIGN KEY (data_asset_id) REFERENCES data_assets (data_asset_id),
    UNIQUE (session_id, name, timestamp)
  );

CREATE TABLE IF NOT EXISTS
  epochs (
    session_id VARCHAR(30),
    tags JSON,
    start_time TIME,
    stop_time TIME,
    notes TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions (session_id),
    UNIQUE (session_id, start_time, stop_time)
  );

CREATE TABLE IF NOT EXISTS
  electrode_groups (
    -- electrode_group_id INTEGER PRIMARY KEY, --session + probe
    session_id VARCHAR(30),
    name TEXT CHECK (name LIKE 'probe%'), -- probeA
    description TEXT DEFAULT 'Neuropixels 1.0 lower channels (1:384)',
    device INTEGER,
    location TEXT, -- e.g. 2002 A2
    -- position TEXT, -- stereotaxic coordinates
    FOREIGN KEY (session_id) REFERENCES sessions (session_id),
    FOREIGN KEY (device) REFERENCES devices (device_id),
    -- UNIQUE (session_id, electrode_group_name)
    PRIMARY KEY (session_id, name)
  );

CREATE TABLE IF NOT EXISTS
  electrodes (
    session_id VARCHAR(30),
    'group' TEXT, -- probeA
    channel_index INTEGER CHECK (channel_index > 0), -- channel number on probe, 1-indexed
    id INTEGER GENERATED ALWAYS AS (channel_index),
    x NUMERIC, -- +x is posterior
    y NUMERIC, -- +y is inferior
    z NUMERIC, -- +z is right
    imp NUMERIC, -- ohms
    location TEXT DEFAULT '', -- ccf region
    filtering TEXT,
    reference TEXT 'tip',
    -- FOREIGN KEY (session_id) REFERENCES sessions (session_id),
    FOREIGN KEY (session_id, 'group') REFERENCES electrode_groups (session_id, name),
    FOREIGN KEY (location) REFERENCES ccf_regions (ccf_region_id),
    PRIMARY KEY (session_id, 'group', channel_index)
  );

CREATE TABLE IF NOT EXISTS
  sorters (
    sorter_id INTEGER PRIMARY KEY,
    pipeline TEXT,
    name TEXT DEFAULT 'kilosort',
    version NUMERIC
  );

CREATE TABLE IF NOT EXISTS
  sorted_groups (
    sorted_group_id INTEGER PRIMARY KEY,
    session_id VARCHAR(30),
    sorter_id INTEGER,
    spike_times_path TEXT,
    start_time TIME,
    sample_rate NUMERIC,
    FOREIGN KEY (sorter_id) REFERENCES sorters (sorter_id),
    FOREIGN KEY (session_id) REFERENCES sessions (session_id)
  );

-- data to add: 'spike_times', 'waveform_mean', 'waveform_sd', 
CREATE TABLE IF NOT EXISTS
  units (
    unit_id VARCHAR(36) PRIMARY KEY, --uuid
    sorted_group_id INTEGER,
    session_id VARCHAR(30),
    sorter_id INTEGER,
    peak_channel_index INTEGER, -- channel number on probe
    location TEXT,
    ------------------
    id TEXT GENERATED ALWAYS AS (unit_id),
    spike_times JSON,
    electrodes JSON GENERATED ALWAYS AS ('[' || peak_channel_index || ']'),
    electrode_group TEXT, --probeA
    waveform_mean JSON,
    waveform_sd JSON,
    obs_intervals JSON,
    ------------------ metrics from SpikeInterface/Allen Ecephys pipeline 
    peak_to_valley NUMERIC,
    d_prime NUMERIC,
    l_ratio NUMERIC,
    peak_trough_ratio NUMERIC,
    half_width NUMERIC,
    sliding_rp_violation NUMERIC,
    num_spikes INTEGER,
    repolarization_slope NUMERIC,
    device_name TEXT,
    isi_violations_ratio NUMERIC,
    rp_violations NUMERIC,
    ks_unit_id INTEGER,
    rp_contamination NUMERIC,
    drift_mad NUMERIC,
    drift_ptp NUMERIC,
    amplitude_cutoff NUMERIC,
    isolation_distance NUMERIC,
    amplitude NUMERIC,
    default_qc TEXT,
    snr NUMERIC,
    drift_std NUMERIC,
    firing_rate NUMERIC,
    presence_ratio NUMERIC,
    recovery_slope NUMERIC,
    cluster_id INTEGER,
    nn_hit_rate NUMERIC,
    nn_miss_rate NUMERIC,
    silhouette_score NUMERIC,
    max_drift NUMERIC,
    cumulative_drift NUMERIC,
    peak_channel INTEGER,
    duration NUMERIC,
    halfwidth NUMERIC,
    PT_ratio NUMERIC,
    spread INTEGER,
    velocity_above NUMERIC,
    velocity_below NUMERIC,
    quality TEXT,
    -- FOREIGN KEY (session_id) REFERENCES sessions (session_id),
    FOREIGN KEY (sorter_id) REFERENCES sorters (sorter_id),
    -- FOREIGN KEY (electrode_group) REFERENCES electrode_groups (electrode_group),
    FOREIGN KEY (session_id, electrode_group, peak_channel_index) REFERENCES electrodes (session_id, 'group', channel_index),
    FOREIGN KEY (location) REFERENCES ccf_regions (ccf_region_id),
    FOREIGN KEY (sorted_group_id) REFERENCES sorted_groups (sorted_group_id),
    UNIQUE (sorted_group_id, unit_id)
  );

CREATE TABLE IF NOT EXISTS
  aud_stims (aud_stim_id INTEGER PRIMARY KEY);

CREATE TABLE IF NOT EXISTS
  vis_stims (vis_stim_id INTEGER PRIMARY KEY);

CREATE TABLE IF NOT EXISTS
  opto_stims (opto_stim_id INTEGER PRIMARY KEY);

CREATE TABLE IF NOT EXISTS
  stims (
    stim_id INTEGER PRIMARY KEY,
    aud_stim_id INTEGER,
    vis_stim_id INTEGER,
    opto_stim_id INTEGER,
    FOREIGN KEY (aud_stim_id) REFERENCES aud_stims (aud_stim_id),
    FOREIGN KEY (vis_stim_id) REFERENCES vis_stims (vis_stim_id),
    FOREIGN KEY (opto_stim_id) REFERENCES opto_stims (opto_stim_id),
    UNIQUE (aud_stim_id, vis_stim_id, opto_stim_id)
  );

CREATE TABLE IF NOT EXISTS
  _trials_template (
    session_id VARCHAR(30),
    trial_index INTEGER,
    start_time DATETIME,
    stop_time DATETIME,
    FOREIGN KEY (session_id) REFERENCES sessions (session_id),
    UNIQUE (session_id, trial_index)
  );

CREATE TABLE IF NOT EXISTS
  trials_dynamicrouting_task (
    session_id VARCHAR(30),
    trial_index INTEGER,
    start_time TIME,
    stop_time TIME,
    -- stim_id INTEGER, -- FOREIGN KEY
    -- aud_stim_id INTEGER, -- FOREIGN KEY
    -- vis_stim_id INTEGER, -- FOREIGN KEY
    -- opto_stim_id INTEGER, -- FOREIGN KEY
    quiescent_window_start_time TIME,
    quiescent_window_stop_time TIME,
    stim_start_time TIME,
    stim_stop_time TIME,
    opto_start_time TIME,
    opto_stop_time TIME,
    response_window_start_time TIME,
    response_window_stop_time TIME,
    response_time TIME,
    timeout_start_time TIME,
    timeout_stop_time TIME,
    post_response_window_start_time TIME,
    post_response_window_stop_time TIME,
    context_name TEXT,
    stim_name TEXT,
    block_index INTEGER,
    trial_index_in_block INTEGER,
    repeat_index INTEGER,
    -- opto_location_name TEXT,
    -- opto_location_index INTEGER, -- FOREIGN KEY
    -- opto_location_bregma_x NUMERIC,
    -- opto_location_bregma_y NUMERIC,
    opto_power NUMERIC,
    is_response BOOLEAN,
    is_correct BOOLEAN,
    is_incorrect BOOLEAN,
    is_hit BOOLEAN,
    is_false_alarm BOOLEAN,
    is_correct_reject BOOLEAN,
    is_miss BOOLEAN,
    is_go BOOLEAN,
    is_nogo BOOLEAN,
    is_rewarded BOOLEAN,
    is_noncontingent_reward BOOLEAN,
    is_contingent_reward BOOLEAN,
    is_reward_scheduled BOOLEAN,
    is_aud_stim BOOLEAN,
    is_vis_stim BOOLEAN,
    is_catch BOOLEAN,
    is_aud_target BOOLEAN,
    is_vis_target BOOLEAN,
    is_vis_nontarget BOOLEAN,
    is_aud_nontarget BOOLEAN,
    is_vis_context BOOLEAN,
    is_aud_context BOOLEAN,
    is_context_switch BOOLEAN,
    is_repeat BOOLEAN,
    is_opto BOOLEAN,
    FOREIGN KEY (session_id) REFERENCES sessions (session_id),
    -- FOREIGN KEY (aud_stim_id) REFERENCES aud_stims (aud_stim_id),
    -- FOREIGN KEY (vis_stim_id) REFERENCES vis_stims (vis_stim_id),
    -- FOREIGN KEY (opto_stim_id) REFERENCES opto_stims (opto_stim_id),
    -- FOREIGN KEY (stim_id) REFERENCES stimuli (stim_id),
    UNIQUE (session_id, trial_index)
  );

CREATE TABLE IF NOT EXISTS
  trials_vis_mapping (
    session_id VARCHAR(30),
    trial_index INTEGER,
    stim_id INTEGER, -- FOREIGN KEY
    start_time TIME,
    stop_time TIME,
    is_small_field_grating BOOLEAN,
    grating_orientation NUMERIC,
    grating_x NUMERIC,
    grating_y NUMERIC,
    is_full_field_flash BOOLEAN,
    flash_contrast NUMERIC,
    FOREIGN KEY (session_id) REFERENCES sessions (session_id),
    FOREIGN KEY (stim_id) REFERENCES stimuli (stim_id),
    UNIQUE (session_id, trial_index)
  );

CREATE TABLE IF NOT EXISTS
  trials_aud_mapping (
    session_id VARCHAR(30),
    trial_index INTEGER,
    stim_id INTEGER, -- FOREIGN KEY
    start_time TIME,
    stop_time TIME,
    is_AM_noise BOOLEAN,
    is_pure_tone BOOLEAN,
    freq NUMERIC,
    FOREIGN KEY (session_id) REFERENCES sessions (session_id),
    FOREIGN KEY (stim_id) REFERENCES stimuli (stim_id),
    UNIQUE (session_id, trial_index)
  );

CREATE TABLE IF NOT EXISTS
  trials_optotagging (
    session_id VARCHAR(30),
    trial_index INTEGER,
    stim_id INTEGER,
    start_time TIME,
    stop_time TIME,
    -- location_name TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions (session_id),
    FOREIGN KEY (stim_id) REFERENCES stimuli (stim_id),
    UNIQUE (session_id, trial_index)
  );

CREATE INDEX idx_sessions_subject_id ON sessions (subject_id);

-- CREATE VIEW
--     view_electrodes AS
-- SELECT
--     electrode_id AS id,
--     x AS x,
--     y AS y,
--     z AS z,
--     ccf_region_id AS location,
--     groups.name AS group_name, -- probeA
-- FROM
--     electrodes, groups
-- INNER JOIN
--     electrode_groups AS groups
-- ON
--     electrodes.electrode_group_id = groups.electrode_group_id;

---------
-- epoch duration in minutes
-- SELECT session_id, tags, round((strftime('%s', stop_time) - strftime('%s', start_time)) / 60.0, 2) AS 'duration (min)'  FROM epochs;

----------
-- subject age in days
--SELECT sessions.session_start_time, ROUND(JULIANDAY(sessions.session_start_time) - JULIANDAY(subjects.date_of_birth), 0) AS age_in_days FROM sessions, subjects WHERE sessions.subject_id = subjects.subject_id