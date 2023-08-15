-- sqlite
CREATE TABLE IF NOT EXISTS
  subjects (
    subject_id INT PRIMARY KEY,
    sex CHAR(1) CHECK (sex IN ('M', 'F', 'U')) DEFAULT NULL,
    date_of_birth DATE DEFAULT NULL,
    genotype TEXT DEFAULT NULL,
    description TEXT DEFAULT NULL,
    strain TEXT DEFAULT NULL,
    notes TEXT DEFAULT NULL
  );

CREATE TABLE IF NOT EXISTS
  devices (
    device_id INTEGER PRIMARY KEY, -- serial number
    name TEXT DEFAULT 'Neuropixels 1.0',
    description TEXT DEFAULT NULL,
    manufacturer TEXT DEFAULT 'IMEC'
  );

CREATE TABLE IF NOT EXISTS
  ccf_regions (ccf_region_id TEXT PRIMARY KEY);

CREATE TABLE IF NOT EXISTS
  sessions (
    session_id VARCHAR(30) PRIMARY KEY,
    subject_id INTEGER NOT NULL,
    session_start_time DATETIME DEFAULT NULL, --
    stimulus_notes TEXT DEFAULT NULL, -- task name
    experimenter TEXT DEFAULT NULL,
    experiment_description TEXT DEFAULT NULL, -- < add rig here
    epoch_tags JSON DEFAULT NULL,
    source_script TEXT DEFAULT NULL,
    identifier VARCHAR(36) DEFAULT NULL, -- uuid4 w hyphens
    notes TEXT DEFAULT NULL,
    -- pharmacology TEXT DEFAULT NULL,
    -- invalid_times JSON DEFAULT NULL,
    FOREIGN KEY (subject_id) REFERENCES subjects (subject_id)
  );

CREATE TABLE IF NOT EXISTS
  data_assets (
    data_asset_id VARCHAR(36) PRIMARY KEY NOT NULL, -- uuid4
    session_id VARCHAR(30) NOT NULL,
    description TEXT DEFAULT NULL -- e.g. 'raw ephys data'
  );

CREATE TABLE IF NOT EXISTS
  files (
    file_id INTEGER PRIMARY KEY,
    session_id VARCHAR(30) NOT NULL,
    name TEXT NOT NULL,
    suffix TEXT NOT NULL,
    size INTEGER NOT NULL,
    timestamp DATETIME NOT NULL,
    s3_path TEXT DEFAULT NULL,
    allen_path TEXT DEFAULT NULL,
    data_asset_id TEXT DEFAULT NULL,
    notes TEXT DEFAULT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions (session_id),
    FOREIGN KEY (data_asset_id) REFERENCES data_assets (data_asset_id),
    UNIQUE (session_id, name, suffix, timestamp)
  );

CREATE TABLE IF NOT EXISTS
  folders (
    folder_id INTEGER PRIMARY KEY,
    session_id VARCHAR(30) NOT NULL,
    name TEXT NOT NULL,
    timestamp DATETIME NOT NULL,
    s3_path TEXT NOT NULL,
    allen_path TEXT DEFAULT NULL,
    data_asset_id TEXT NOT NULL,
    notes TEXT DEFAULT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions (session_id),
    FOREIGN KEY (data_asset_id) REFERENCES data_assets (data_asset_id),
    UNIQUE (session_id, name, timestamp)
  );

CREATE TABLE IF NOT EXISTS
  epochs (
    epoch_id INTEGER PRIMARY KEY,
    session_id VARCHAR(30) NOT NULL,
    tags JSON NOT NULL,
    start_time TIME NOT NULL,
    stop_time TIME NOT NULL,
    notes TEXT DEFAULT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions (session_id)
  );

CREATE TABLE IF NOT EXISTS
  electrode_groups (
    -- electrode_group_id INTEGER PRIMARY KEY, --session + probe
    session_id VARCHAR(30) NOT NULL,
    electrode_group_name TEXT CHECK (electrode_group_name LIKE 'probe%') NOT NULL, -- probeA
    device_id INTEGER NOT NULL,
    implant_location TEXT DEFAULT NULL, -- e.g. 2002 A2
    FOREIGN KEY (session_id) REFERENCES sessions (session_id),
    FOREIGN KEY (device_id) REFERENCES devices (device_id),
    -- UNIQUE (session_id, electrode_group_name)
    PRIMARY KEY (session_id, electrode_group_name)
  );

CREATE TABLE IF NOT EXISTS
  electrodes (
    session_id VARCHAR(30) NOT NULL,
    electrode_group_name TEXT CHECK (electrode_group_name LIKE 'probe%') NOT NULL, -- probeA
    channel_index INTEGER NOT NULL, -- channel number on probe
    ccf_region_id TEXT DEFAULT NULL,
    ccf_x NUMERIC DEFAULT NULL,
    ccf_y NUMERIC DEFAULT NULL,
    ccf_z NUMERIC DEFAULT NULL,
    -- FOREIGN KEY (session_id) REFERENCES sessions (session_id),
    FOREIGN KEY (session_id, electrode_group_name) REFERENCES electrode_groups (session_id, electrode_group_name),
    FOREIGN KEY (ccf_region_id) REFERENCES ccf_regions (ccf_region_id),
    PRIMARY KEY (session_id, electrode_group_name, channel_index)
    -- PRIMARY KEY (session_id, electrode_group_name, channel_index)
  );

CREATE TABLE IF NOT EXISTS
  sorters (
    sorter_id INTEGER PRIMARY KEY,
    pipeline TEXT NOT NULL,
    name TEXT DEFAULT 'kilosort',
    version NUMERIC DEFAULT NULL
  );

CREATE TABLE IF NOT EXISTS
  sorted_groups (
    sorted_group_id INTEGER PRIMARY KEY,
    session_id VARCHAR(30) NOT NULL,
    sorter_id INTEGER NOT NULL,
    spike_times_path TEXT NOT NULL,
    start_time TIME NOT NULL,
    sample_rate NUMERIC NOT NULL,
    FOREIGN KEY (sorter_id) REFERENCES sorters (sorter_id),
    FOREIGN KEY (session_id) REFERENCES sessions (session_id)
  );

-- data to add: 'spike_times', 'waveform_mean', 'waveform_sd', 
CREATE TABLE IF NOT EXISTS
  units (
    unit_id VARCHAR(36) NOT NULL PRIMARY KEY, --uuid
    sorted_group_id INTEGER NOT NULL,
    session_id VARCHAR(30) NOT NULL,
    sorter_id INTEGER DEFAULT NULL,
    electrode_group_name TEXT NOT NULL, --probeA
    peak_channel_index INTEGER NOT NULL, -- channel number on probe
    ccf_region_id TEXT DEFAULT NULL,
    obs_intervals JSON DEFAULT NULL,
    peak_to_valley NUMERIC DEFAULT NULL,
    d_prime NUMERIC DEFAULT NULL,
    l_ratio NUMERIC DEFAULT NULL,
    peak_trough_ratio NUMERIC DEFAULT NULL,
    half_width NUMERIC DEFAULT NULL,
    sliding_rp_violation NUMERIC DEFAULT NULL,
    num_spikes INTEGER DEFAULT NULL,
    repolarization_slope NUMERIC DEFAULT NULL,
    device_name TEXT DEFAULT NULL,
    isi_violations_ratio NUMERIC DEFAULT NULL,
    rp_violations NUMERIC DEFAULT NULL,
    ks_unit_id INTEGER DEFAULT NULL,
    rp_contamination NUMERIC DEFAULT NULL,
    drift_mad NUMERIC DEFAULT NULL,
    drift_ptp NUMERIC DEFAULT NULL,
    amplitude_cutoff NUMERIC DEFAULT NULL,
    isolation_distance NUMERIC DEFAULT NULL,
    amplitude NUMERIC DEFAULT NULL,
    default_qc TEXT DEFAULT NULL,
    snr NUMERIC DEFAULT NULL,
    drift_std NUMERIC DEFAULT NULL,
    firing_rate NUMERIC DEFAULT NULL,
    presence_ratio NUMERIC DEFAULT NULL,
    recovery_slope NUMERIC DEFAULT NULL,
    cluster_id INTEGER DEFAULT NULL,
    nn_hit_rate NUMERIC DEFAULT NULL,
    nn_miss_rate NUMERIC DEFAULT NULL,
    silhouette_score NUMERIC DEFAULT NULL,
    max_drift NUMERIC DEFAULT NULL,
    cumulative_drift NUMERIC DEFAULT NULL,
    peak_channel INTEGER DEFAULT NULL,
    duration NUMERIC DEFAULT NULL,
    halfwidth NUMERIC DEFAULT NULL,
    PT_ratio NUMERIC DEFAULT NULL,
    spread INTEGER DEFAULT NULL,
    velocity_above NUMERIC DEFAULT NULL,
    velocity_below NUMERIC DEFAULT NULL,
    quality TEXT DEFAULT NULL,
    -- FOREIGN KEY (session_id) REFERENCES sessions (session_id),
    FOREIGN KEY (sorter_id) REFERENCES sorters (sorter_id),
    -- FOREIGN KEY (electrode_group_name) REFERENCES electrode_groups (electrode_group_name),
    FOREIGN KEY (
      session_id,
      electrode_group_name,
      peak_channel_index
    ) REFERENCES electrodes (session_id, electrode_group_name, channel_index),
    FOREIGN KEY (ccf_region_id) REFERENCES ccf_regions (ccf_region_id),
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
    aud_stim_id INTEGER DEFAULT NULL,
    vis_stim_id INTEGER DEFAULT NULL,
    opto_stim_id INTEGER DEFAULT NULL,
    FOREIGN KEY (aud_stim_id) REFERENCES aud_stims (aud_stim_id),
    FOREIGN KEY (vis_stim_id) REFERENCES vis_stims (vis_stim_id),
    FOREIGN KEY (opto_stim_id) REFERENCES opto_stims (opto_stim_id),
    UNIQUE (aud_stim_id, vis_stim_id, opto_stim_id)
  );

CREATE TABLE IF NOT EXISTS
  _trials_template (
    trial_id INTEGER PRIMARY KEY,
    session_id VARCHAR(30) NOT NULL,
    trial_index INTEGER NOT NULL,
    start_time DATETIME NOT NULL,
    stop_time DATETIME NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions (session_id),
    UNIQUE (session_id, trial_index)
  );

CREATE TABLE IF NOT EXISTS
  trials_dynamicrouting_task (
    trial_id INTEGER PRIMARY KEY,
    session_id VARCHAR(30) NOT NULL,
    trial_index INTEGER NOT NULL,
    start_time TIME NOT NULL,
    stop_time TIME NOT NULL,
    -- stim_id INTEGER DEFAULT NULL, -- FOREIGN KEY
    -- aud_stim_id INTEGER DEFAULT NULL, -- FOREIGN KEY
    -- vis_stim_id INTEGER DEFAULT NULL, -- FOREIGN KEY
    -- opto_stim_id INTEGER DEFAULT NULL, -- FOREIGN KEY
    quiescent_window_start_time TIME DEFAULT NULL,
    quiescent_window_stop_time TIME DEFAULT NULL,
    stim_start_time TIME DEFAULT NULL,
    stim_stop_time TIME DEFAULT NULL,
    opto_start_time TIME DEFAULT NULL,
    opto_stop_time TIME DEFAULT NULL,
    response_window_start_time TIME DEFAULT NULL,
    response_window_stop_time TIME DEFAULT NULL,
    response_time TIME DEFAULT NULL,
    timeout_start_time TIME DEFAULT NULL,
    timeout_stop_time TIME DEFAULT NULL,
    post_response_window_start_time TIME DEFAULT NULL,
    post_response_window_stop_time TIME DEFAULT NULL,
    context_name TEXT DEFAULT NULL,
    stim_name TEXT DEFAULT NULL,
    block_index INTEGER DEFAULT NULL,
    trial_index_in_block INTEGER DEFAULT NULL,
    repeat_index INTEGER DEFAULT NULL,
    -- opto_location_name TEXT DEFAULT NULL,
    -- opto_location_index INTEGER DEFAULT NULL, -- FOREIGN KEY
    -- opto_location_bregma_x NUMERIC DEFAULT NULL,
    -- opto_location_bregma_y NUMERIC DEFAULT NULL,
    opto_power NUMERIC DEFAULT NULL,
    is_response BOOLEAN DEFAULT NULL,
    is_correct BOOLEAN DEFAULT NULL,
    is_incorrect BOOLEAN DEFAULT NULL,
    is_hit BOOLEAN DEFAULT NULL,
    is_false_alarm BOOLEAN DEFAULT NULL,
    is_correct_reject BOOLEAN DEFAULT NULL,
    is_miss BOOLEAN DEFAULT NULL,
    is_go BOOLEAN DEFAULT NULL,
    is_nogo BOOLEAN DEFAULT NULL,
    is_rewarded BOOLEAN DEFAULT NULL,
    is_noncontingent_reward BOOLEAN DEFAULT NULL,
    is_contingent_reward BOOLEAN DEFAULT NULL,
    is_reward_scheduled BOOLEAN DEFAULT NULL,
    is_aud_stim BOOLEAN DEFAULT NULL,
    is_vis_stim BOOLEAN DEFAULT NULL,
    is_catch BOOLEAN DEFAULT NULL,
    is_aud_target BOOLEAN DEFAULT NULL,
    is_vis_target BOOLEAN DEFAULT NULL,
    is_vis_nontarget BOOLEAN DEFAULT NULL,
    is_aud_nontarget BOOLEAN DEFAULT NULL,
    is_vis_context BOOLEAN DEFAULT NULL,
    is_aud_context BOOLEAN DEFAULT NULL,
    is_context_switch BOOLEAN DEFAULT NULL,
    is_repeat BOOLEAN DEFAULT NULL,
    is_opto BOOLEAN DEFAULT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions (session_id),
    -- FOREIGN KEY (aud_stim_id) REFERENCES aud_stims (aud_stim_id),
    -- FOREIGN KEY (vis_stim_id) REFERENCES vis_stims (vis_stim_id),
    -- FOREIGN KEY (opto_stim_id) REFERENCES opto_stims (opto_stim_id),
    -- FOREIGN KEY (stim_id) REFERENCES stimuli (stim_id),
    UNIQUE (session_id, trial_index)
  );

CREATE TABLE IF NOT EXISTS
  vis_mapping_trials (
    trial_id INTEGER PRIMARY KEY,
    session_id VARCHAR(30) NOT NULL,
    trial_index INTEGER NOT NULL,
    stim_id INTEGER DEFAULT NULL, -- FOREIGN KEY
    start_time TIME NOT NULL,
    stop_time TIME NOT NULL,
    is_small_field_grating BOOLEAN DEFAULT NULL,
    grating_orientation NUMERIC DEFAULT NULL,
    grating_x NUMERIC DEFAULT NULL,
    grating_y NUMERIC DEFAULT NULL,
    is_full_field_flash BOOLEAN DEFAULT NULL,
    flash_contrast NUMERIC DEFAULT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions (session_id),
    FOREIGN KEY (stim_id) REFERENCES stimuli (stim_id),
    UNIQUE (session_id, trial_index)
  );

CREATE TABLE IF NOT EXISTS
  aud_mapping_trials (
    trial_id INTEGER PRIMARY KEY,
    session_id VARCHAR(30) NOT NULL,
    trial_index INTEGER NOT NULL,
    stim_id INTEGER DEFAULT NULL, -- FOREIGN KEY
    start_time TIME NOT NULL,
    stop_time TIME NOT NULL,
    is_AM_noise BOOLEAN DEFAULT NULL,
    is_pure_tone BOOLEAN DEFAULT NULL,
    freq NUMERIC DEFAULT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions (session_id),
    FOREIGN KEY (stim_id) REFERENCES stimuli (stim_id),
    UNIQUE (session_id, trial_index)
  );

CREATE TABLE IF NOT EXISTS
  optotagging_trials (
    trial_id INTEGER PRIMARY KEY,
    session_id VARCHAR(30) NOT NULL,
    trial_index INTEGER NOT NULL,
    stim_id TEXT DEFAULT NULL,
    start_time TIME NOT NULL,
    stop_time TIME NOT NULL,
    -- location_name TEXT DEFAULT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions (session_id),
    FOREIGN KEY (stim_id) REFERENCES stimuli (stim_id),
    UNIQUE (session_id, trial_index)
  );

CREATE INDEX idx_sessions_subject_id ON sessions (subject_id);

-- CREATE VIEW
--     view_electrodes AS
-- SELECT
--     electrode_id AS id,
--     ccf_x AS x,
--     ccf_y AS y,
--     ccf_z AS z,
--     ccf_region_id AS location,
--     groups.name AS group_name, -- probeA
-- FROM
--     electrodes, groups
-- INNER JOIN
--     electrode_groups AS groups
-- ON
--     electrodes.electrode_group_id = groups.electrode_group_id;