# Riot Games Data Pipeline

A data engineering project that ingests League of Legends match data from the Riot Games API and stores it in PostgreSQL for downstream transformation and analysis.

The pipeline is designed to incrementally collect ranked match history for tracked players while avoiding duplicate API requests and database records. Raw Riot API responses are stored as JSONB so the original source data is preserved for future transformation into analytics-ready tables.

## Project Goals

This project is designed to demonstrate core data engineering concepts, including:

- REST API ingestion
- API rate limiting and retry handling
- Incremental data ingestion
- PostgreSQL data storage
- Raw JSON data preservation
- Many-to-many relational modeling
- Duplicate prevention and idempotent database operations
- Application logging
- Unit testing with mocked dependencies
- Separation of API, database, and ingestion responsibilities

## Architecture

The current ingestion flow is:

```text
                    Riot Games API
                          │
                          ▼
                    ┌───────────┐
                    │ RiotClient│
                    └─────┬─────┘
                          │
                  Match IDs / JSON
                          │
                          ▼
                 ┌────────────────┐
                 │ MatchIngestion │
                 └───────┬────────┘
                         │
                         ▼
                  ┌──────────────┐
                  │PostgresClient│
                  └───────┬──────┘
                          │
                          ▼
                     PostgreSQL
              ┌───────────┼───────────┐
              ▼           ▼           ▼
       tracked_players raw_matches player_matches
```

### RiotClient

`RiotClient` is responsible for communication with the Riot Games API.

Its responsibilities include:

- Riot ID account lookup
- PUUID retrieval
- Ranked match ID retrieval
- Match-V5 match-data retrieval
- Local API rate limiting
- Retry handling for temporary failures
- HTTP 429 handling
- Exponential backoff for server and connection failures

### MatchIngestion

`MatchIngestion` coordinates the API and database layers.

It determines:

- Which matches already exist globally
- Which matches are new and need to be downloaded
- Which player-match relationships already exist
- When incremental ingestion has reached previously processed data
- When additional API pages need to be requested

Raw match existence and player-match existence are intentionally handled separately. A match may already be stored because another tracked player participated in the same game, while still requiring a relationship to be created for the current player.

### PostgresClient

`PostgresClient` handles PostgreSQL operations, including:

- Database connections
- Raw match insertion
- Tracked-player upserts
- Player-match relationship insertion
- Existing match lookups
- Existing player-match relationship lookups

SQL statements are parameterized, and conflict handling is used to prevent duplicate records.

## Database Model

The current raw ingestion layer consists of three tables.

### `tracked_players`

Stores players being tracked by the pipeline.

| Column | Description |
| --- | --- |
| `puuid` | Riot's unique player identifier |
| `game_name` | Current Riot ID game name |
| `tag_line` | Current Riot ID tag line |
| `created_at` | Timestamp when the player was added |

The PUUID is used as the primary identifier because Riot IDs can change.

### `raw_matches`

Stores the original match payload returned by Riot.

| Column | Description |
| --- | --- |
| `match_id` | Unique Riot match identifier |
| `payload` | Complete Riot response stored as JSONB |

Each match is stored only once, even if multiple tracked players participated in it.

### `player_matches`

Junction table connecting tracked players to their matches.

| Column | Description |
| --- | --- |
| `puuid` | Tracked player identifier |
| `match_id` | Riot match identifier |

The composite key `(puuid, match_id)` prevents duplicate relationships.

This creates a many-to-many relationship:

```text
tracked_players
      │
      │ 1
      ▼
player_matches
      ▲
      │ many
      │
 raw_matches
```

A player can participate in many matches, and a match can contain multiple tracked players.

## Incremental Ingestion

The pipeline supports both incremental ingestion and full backfills.

### Incremental Mode

```python
ingestion.ingest_raw_matches(full_backfill=False)
```

The pipeline retrieves recent match IDs and compares them against matches already associated with the player.

When it reaches a page containing no new player-match relationships, ingestion stops instead of continuing through previously processed history.

This reduces unnecessary API requests during repeated pipeline runs.

### Full Backfill

```python
ingestion.ingest_raw_matches(full_backfill=True)
```

Full-backfill mode continues paginating through the player's available match history rather than stopping when previously processed matches are encountered.

## Rate Limiting and Retries

The Riot API client contains a local rate limiter to prevent the pipeline from intentionally exceeding configured request limits.

Temporary failures are handled separately from proactive rate limiting.

The client handles:

- HTTP `429` rate-limit responses
- HTTP `5xx` server errors
- Request timeouts
- Connection errors

For `429` responses, the client uses Riot's `Retry-After` response header when available.

Temporary server and network failures use exponential backoff with jitter before retrying.

Other HTTP errors such as `400`, `401`, and `403` are not automatically retried.

## Logging

The project uses Python's built-in `logging` module.

Logs provide visibility into:

- Ingestion startup
- Number of match IDs retrieved
- Number of new raw matches
- Number of new player-match relationships
- Individual match ingestion
- API retries
- Rate-limit events
- Server errors
- Ingestion completion

Console logging provides normal pipeline progress, while more detailed debugging information can be written to:

```text
logs/pipeline.log
```

Runtime log files should not be committed to source control.

## Unit Testing

Unit tests are implemented with `pytest` and `unittest.mock.MagicMock`.

External dependencies are mocked so tests do not require:

- A Riot API connection
- A valid Riot API key
- A PostgreSQL connection

The ingestion test suite currently verifies:

1. Only new raw matches are downloaded and inserted.
2. Existing raw matches can be linked to a new player without being downloaded again.
3. No unnecessary operations occur when all matches have already been processed.
4. All matches are correctly processed when every match is new.
5. Pagination advances using the correct Riot API offset.

Run the complete test suite from the project root:

```bash
python -m pytest -v
```

## Project Structure

```text
Riot_Data_Pipeline/
│
├── data/
│
├── logs/
│   └── pipeline.log
│
├── sql/
│
├── src/
│   ├── api/
│   │   └── riot_client.py
│   │
│   ├── database/
│   │   └── postgres.py
│   │
│   ├── ingestion/
│   │   └── match_ingestion.py
│   │
│   └── utils/
│       ├── logging_config.py
│       └── rate_limiter.py
│
├── tests/
│   └── test_match_ingestion.py
│
├── .env
├── .gitignore
├── README.md
└── requirements.txt
```

## Setup

### 1. Clone the repository

```bash
git clone <repository-url>
cd Riot_Data_Pipeline
```

### 2. Create a virtual environment

Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root:

```env
RIOT_API_KEY=your_riot_api_key

DB_HOST=localhost
DB_PORT=5432
DB_NAME=league
DB_USER=your_postgres_user
DB_PASSWORD=your_postgres_password
```

Do not commit `.env` or API/database credentials to Git.

Your `.gitignore` should include at minimum:

```gitignore
.env
logs/
__pycache__/
.pytest_cache/
.venv/
```

## Running the Pipeline

Run the ingestion module from the project root:

```bash
python -m src.ingestion.match_ingestion
```

The current entry point creates a Riot client for a configured player, initializes the PostgreSQL client, and performs incremental match ingestion.

## Technology Stack

- **Python** — ingestion and application logic
- **Requests** — Riot API communication
- **PostgreSQL** — persistent raw-data storage
- **Psycopg 3** — Python/PostgreSQL integration
- **JSONB** — storage of raw Riot API responses
- **pytest** — automated testing
- **unittest.mock** — dependency mocking
- **python-dotenv** — environment-variable management
- **Python logging** — pipeline observability

## Planned Development

The current implementation represents the raw ingestion layer of a larger data engineering pipeline.

Planned additions include:

```text
Riot API
   │
   ▼
Raw Ingestion
   │
   ▼
PostgreSQL Raw Layer
   │
   ▼
Staging / Transformation
   │
   ▼
dbt
   │
   ▼
Dimensional Data Model
   │
   ▼
Analytics / Visualization
```

Potential future work includes:

- PostgreSQL integration tests
- Participant-level transformation
- Match-level staging models
- dbt transformations and data-quality tests
- Dimensional modeling
- Champion dimension data
- Pipeline orchestration with Dagster
- Dockerized development environment
- Analytics dashboards
- Cloud deployment

## Data Source

Match and account data are retrieved from the Riot Games Developer API.

This project is an independent educational/data engineering project and is not endorsed by Riot Games.

## Author

Derrick Dollesin

Data Science graduate building data engineering projects focused on API ingestion, relational modeling, data transformation, testing, and analytics.