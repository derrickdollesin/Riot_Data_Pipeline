SELECT
    -- Identifiers
    rm.match_id,

    -- Queue / Game Information
    (rm.payload->'info'->>'queueId')::INT AS queue_id,
    rm.payload->'info'->>'gameMode' AS game_mode,
    rm.payload->'info'->>'gameType' AS game_type,
    rm.payload->'info'->>'gameVersion' AS game_version,
    (rm.payload->'info'->>'mapId')::INT AS map_id,

    -- Time
    (rm.payload->'info'->>'gameCreation')::BIGINT AS game_creation,
    (rm.payload->'info'->>'gameStartTimestamp')::BIGINT AS game_start_timestamp,
    (rm.payload->'info'->>'gameEndTimestamp')::BIGINT AS game_end_timestamp,
    (rm.payload->'info'->>'gameDuration')::INT AS game_duration

FROM {{ source('riot', 'raw_matches') }} AS rm