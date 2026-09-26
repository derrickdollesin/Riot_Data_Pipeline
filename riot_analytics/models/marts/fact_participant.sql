FROM {{ ref('stg_participants') }} AS p

JOIN {{ ref('stg_matches') }} AS m
    ON p.match_id = m.match_id

-- ============================================================
-- fact_participant
-- ============================================================
-- Grain:
--   One row represents one participant in one match.
--
-- Natural key:
--   match_id + participant_id
--
-- Purpose:
--   Combine cleaned participant-level data with match-level
--   information and calculate analytics-ready performance metrics.
-- ============================================================


-- TODO 1:
-- Reference stg_participants using dbt's ref() function.
--
-- This will be the primary source of participant-level data.
--
-- Example fields available:
--   match_id
--   participant_id
--   puuid
--   champion_id
--   champion_name
--   team_id
--   team_position
--   win
--   kills
--   deaths
--   assists
--   gold_earned
--   total_minions_killed
--   neutral_minions_killed
--   total_damage_dealt_to_champions
--   total_damage_taken
--   vision_score
--   wards_placed
--   wards_killed


-- TODO 2:
-- Reference stg_matches using dbt's ref() function.
--
-- This provides match-level information such as:
--   queue_id
--   game_duration
--   game_creation
--   game_start_timestamp
--   game_end_timestamp
--   game_version


-- TODO 3:
-- Join stg_participants to stg_matches.
--
-- Join key:
--   stg_participants.match_id = stg_matches.match_id
--
-- Be careful not to change the grain of the model.
-- There should still be exactly one row per participant per match.


-- TODO 4:
-- Select identifiers and descriptive attributes.
--
-- Include:
--   match_id
--   participant_id
--   puuid
--   champion_id
--   champion_name
--   team_id
--   team_position
--   queue_id
--   win


-- TODO 5:
-- Select the raw performance measures needed downstream.
--
-- Include:
--   kills
--   deaths
--   assists
--   gold_earned
--   total_minions_killed
--   neutral_minions_killed
--   total_damage_dealt_to_champions
--   total_damage_taken
--   vision_score
--   wards_placed
--   wards_killed
--   game_duration


-- TODO 6:
-- Calculate game_duration_minutes.
--
-- Riot game_duration is measured in seconds.
--
-- Convert:
--   game_duration / 60.0
--
-- Use 60.0 instead of 60 so PostgreSQL performs
-- decimal division rather than integer division.


-- TODO 7:
-- Calculate total_cs.
--
-- Use:
--   total_minions_killed + neutral_minions_killed


-- TODO 8:
-- Calculate KDA.
--
-- Basic formula:
--   (kills + assists) / deaths
--
-- Handle deaths = 0 so the query never attempts
-- to divide by zero.
--
-- Decide how you want zero-death games represented.


-- TODO 9:
-- Calculate CS per minute.
--
-- Formula:
--   total_cs / game_duration_minutes


-- TODO 10:
-- Calculate gold per minute.
--
-- Formula:
--   gold_earned / game_duration_minutes


-- TODO 11:
-- Calculate champion damage per minute.
--
-- Formula:
--   total_damage_dealt_to_champions / game_duration_minutes


-- TODO 12:
-- Calculate vision score per minute.
--
-- Formula:
--   vision_score / game_duration_minutes


-- TODO 13:
-- Run the model.
--
-- From the riot_analytics directory:
--
--   dbt run --select fact_participant


-- TODO 14:
-- Verify the model's grain in PostgreSQL.
--
-- Check for duplicate match/participant combinations:
--
--   SELECT
--       match_id,
--       participant_id,
--       COUNT(*)
--   FROM fact_participant
--   GROUP BY
--       match_id,
--       participant_id
--   HAVING COUNT(*) > 1;
--
-- Expected result:
--   0 rows


-- TODO 15:
-- Add fact_participant to models/marts/marts.yml.
--
-- Add data-quality tests for important columns:
--   match_id       -> not_null
--   participant_id -> not_null
--   puuid           -> not_null
--   champion_id     -> not_null
--   team_id         -> not_null
--   win             -> not_null
--
-- Also test that match_id + participant_id is unique.


-- TODO 16:
-- Run all dbt models and tests.
--
--   dbt run
--   dbt test
--
-- fact_participant is complete when:
--   1. The model builds successfully.
--   2. The grain is correct.
--   3. All dbt tests pass.