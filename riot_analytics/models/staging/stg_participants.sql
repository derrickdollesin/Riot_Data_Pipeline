SELECT
    -- Identifiers
    rm.match_id,
    (participant->>'participantId')::INT AS participant_id,
    participant->>'puuid' AS puuid,

    -- Champion / Role
    (participant->>'championId')::INT AS champion_id,
    participant->>'championName' AS champion_name,
    (participant->>'champLevel')::INT AS champ_level,
    (participant->>'champExperience')::INT AS champ_experience,
    (participant->>'teamId')::INT AS team_id,
    participant->>'teamPosition' AS team_position,
    participant->>'individualPosition' AS individual_position,
    participant->>'positionAssignedByMatchmaking'
        AS position_assigned_by_matchmaking,

    -- Core Performance
    (participant->>'kills')::INT AS kills,
    (participant->>'deaths')::INT AS deaths,
    (participant->>'assists')::INT AS assists,
    (participant->>'goldEarned')::INT AS gold_earned,
    (participant->>'pentaKills')::INT AS penta_kills,
    (participant->>'win')::BOOLEAN AS win,

    -- Damage Dealt
    (participant->>'magicDamageDealt')::INT
        AS magic_damage_dealt,
    (participant->>'physicalDamageDealt')::INT
        AS physical_damage_dealt,
    (participant->>'trueDamageDealt')::INT
        AS true_damage_dealt,
    (participant->>'totalDamageDealt')::INT
        AS total_damage_dealt,

    -- Damage to Champions
    (participant->>'magicDamageDealtToChampions')::INT
        AS magic_damage_dealt_to_champions,
    (participant->>'physicalDamageDealtToChampions')::INT
        AS physical_damage_dealt_to_champions,
    (participant->>'trueDamageDealtToChampions')::INT
        AS true_damage_dealt_to_champions,
    (participant->>'totalDamageDealtToChampions')::INT
        AS total_damage_dealt_to_champions,

    -- Damage Taken
    (participant->>'magicDamageTaken')::INT
        AS magic_damage_taken,
    (participant->>'physicalDamageTaken')::INT
        AS physical_damage_taken,
    (participant->>'trueDamageTaken')::INT
        AS true_damage_taken,
    (participant->>'totalDamageTaken')::INT
        AS total_damage_taken,

    -- Farming
    (participant->>'totalMinionsKilled')::INT
        AS total_minions_killed,
    (participant->>'neutralMinionsKilled')::INT
        AS neutral_minions_killed,
    (participant->>'totalEnemyJungleMinionsKilled')::INT
        AS total_enemy_jungle_minions_killed,

    -- Items / Consumables
    (participant->>'consumablesPurchased')::INT
        AS consumables_purchased,

    -- Pings
    (participant->>'allInPings')::INT AS all_in_pings,
    (participant->>'assistMePings')::INT AS assist_me_pings,
    (participant->>'commandPings')::INT AS command_pings,
    (participant->>'dangerPings')::INT AS danger_pings,
    (participant->>'enemyMissingPings')::INT AS enemy_missing_pings,
    (participant->>'enemyVisionPings')::INT AS enemy_vision_pings,
    (participant->>'getBackPings')::INT AS get_back_pings,
    (participant->>'holdPings')::INT AS hold_pings,
    (participant->>'needVisionPings')::INT AS need_vision_pings,
    (participant->>'visionClearedPings')::INT AS vision_cleared_pings,
    (participant->>'pushPings')::INT AS push_pings,
    (participant->>'retreatPings')::INT AS retreat_pings,
    (participant->>'onMyWayPings')::INT AS on_my_way_pings,

    -- Objectives
    (participant->>'firstBloodKill')::BOOLEAN AS first_blood_kill,
    (participant->>'firstTowerKill')::BOOLEAN AS first_tower_kill,
    (participant->>'objectivesStolen')::INT AS objectives_stolen,
    (participant->>'turretKills')::INT AS turret_kills,
    (participant->>'turretTakedowns')::INT AS turret_takedowns,
    (participant->>'turretsLost')::INT AS turrets_lost,

    -- Vision
    (participant->>'visionScore')::INT AS vision_score,
    (participant->>'visionWardsBoughtInGame')::INT
        AS vision_wards_bought_in_game,
    (participant->>'sightWardsBoughtInGame')::INT
        AS sight_wards_bought_in_game,
    (participant->>'wardsKilled')::INT AS wards_killed,
    (participant->>'wardsPlaced')::INT AS wards_placed,

    -- Game Result
    (participant->>'gameEndedInSurrender')::BOOLEAN
        AS game_ended_in_surrender

FROM {{ source('riot', 'raw_matches') }} AS rm

CROSS JOIN LATERAL jsonb_array_elements(
    rm.payload->'info'->'participants'
) AS participant