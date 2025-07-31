# SWF Fast Monitoring Client

**`swf-fastmon-client`** for the ePIC streaming workflow testbed.

Client application that receives information about Time Frames (TFs) from the `swf-fastmon-agent` to monitor the ePIC data acquisition.

The client is designed to be executed anywhere, with minimal infrastructure requirements, allowing users to 
monitor the ePIC data acquisition remotely.

**Note: it will become a standalone application in the near future, but for now it is a part of the `swf-fastmon-agent` repository.**

## Architecture Overview

The client is designed to receive metadata from the `swf-fastmon-agent` and display it in a user-friendly format/web interface. 

* It uses ActiveMQ to receive TFs metadata via STOMP protocol.
* Store the metadata in a configurable database backend using Django ORM (SQLite, PostgreSQL, or MySQL).
* Uses Typer for command-line interface.
* Django ORM provides flexibility for database backend selection and future migrations.
* It can be extended to provide a web interface for monitoring

## Installation and Setup

### Dependencies

The client requires the following Python packages:
- `django` - Web framework with ORM for database operations
- `typer` - Command-line interface framework
- `stomp.py` - STOMP protocol client for ActiveMQ

**Database Drivers** (choose based on your backend):
- SQLite: Built-in support (no additional packages needed)
- PostgreSQL: `psycopg2-binary` or `psycopg`
- MySQL: `mysqlclient` or `PyMySQL`

Install core dependencies:
```bash
pip install django typer stomp.py
```

For PostgreSQL support:
```bash
pip install psycopg2-binary
```

For MySQL support:
```bash
pip install mysqlclient
```

### Database Initialization

Before first use, initialize the database. The client now supports multiple database backends:

**SQLite (default):**
```bash
python main.py init-db --db-engine sqlite --db-name /path/to/fastmon.db
```

**PostgreSQL:**
```bash
python main.py init-db --db-engine postgresql --db-name fastmon_db --db-user admin --db-password your_password --db-host localhost
```

**MySQL:**
```bash
python main.py init-db --db-engine mysql --db-name fastmon_db --db-user admin --db-password your_password --db-host localhost
```

## Usage Examples

### Basic Usage

Start the monitoring client with default settings (SQLite):
```bash
python main.py start
```

Start with custom SQLite database:
```bash
python main.py start --db-engine sqlite --db-name /path/to/my_fastmon.db
```

Start with PostgreSQL:
```bash
python main.py start --db-engine postgresql --db-name fastmon_db --db-user admin --db-password your_password
```

### Remote ActiveMQ Connection

Connect to a remote ActiveMQ broker with SSL and PostgreSQL:
```bash
python main.py start \
  --db-engine postgresql \
  --db-name fastmon_db \
  --db-user db_admin \
  --db-password db_password \
  --host pandaserver02.sdcc.bnl.gov \
  --port 61612 \
  --ssl \
  --ca-certs /path/to/ca-certificates.pem \
  --user your_username \
  --password your_password
```

### Monitoring Status

Check overall monitoring status (SQLite default):
```bash
python main.py status
```

View details for a specific run:
```bash
python main.py status --run 12345
```

Check status with custom database backend:
```bash
python main.py status --db-engine postgresql --db-name fastmon_db --db-user admin --db-password password --run 12345
```

Check status with SQLite database:
```bash
python main.py status --db-engine sqlite --db-name /path/to/fastmon.db --run 12345
```

### Advanced Configuration

Start with verbose logging and custom topic:
```bash
python main.py start \
  --verbose \
  --topic epic.fastmon.tf.custom \
  --host localhost \
  --port 61613
```

### Command Reference

#### `start` - Launch monitoring client
- `--config, -c`: Configuration file path (future feature)
- `--db-engine`: Database engine (sqlite, postgresql, mysql) (default: `sqlite`)
- `--db-name`: Database name or SQLite file path (default: `fastmon_client.db`)
- `--db-host`: Database host (default: `localhost`)
- `--db-port`: Database port (default: auto-detected)
- `--db-user`: Database username
- `--db-password`: Database password
- `--host`: ActiveMQ host (default: `localhost`)
- `--port`: ActiveMQ port (default: `61613`)
- `--topic`: ActiveMQ topic for TF metadata (default: `epic.fastmon.tf`)
- `--user`: ActiveMQ username (default: `admin`)
- `--password`: ActiveMQ password (default: `admin`)
- `--ssl`: Use SSL connection
- `--ca-certs`: Path to CA certificates file
- `--verbose, -v`: Enable verbose logging

#### `status` - Display statistics
- `--db-engine`: Database engine (sqlite, postgresql, mysql) (default: `sqlite`)
- `--db-name`: Database name or SQLite file path (default: `fastmon_client.db`)
- `--db-host`: Database host (default: `localhost`)
- `--db-port`: Database port (default: auto-detected)
- `--db-user`: Database username
- `--db-password`: Database password
- `--run`: Specific run number to show details

#### `init-db` - Initialize database
- `--db-engine`: Database engine (sqlite, postgresql, mysql) (default: `sqlite`)
- `--db-name`: Database name or SQLite file path (default: `fastmon_client.db`)
- `--db-host`: Database host (default: `localhost`)
- `--db-port`: Database port (default: auto-detected)
- `--db-user`: Database username
- `--db-password`: Database password

## Database Schema

The client uses Django ORM models to manage database schema across different backends. Two main tables are created:

### `tf_metadata`
Django model: `TfMetadata`
Stores Time Frame metadata received from ActiveMQ:
- `id`: Auto-incrementing primary key
- `file_id`: Unique identifier for the TF file (unique constraint)
- `run_number`: Run number associated with the TF
- `tf_number`: Time Frame number within the run
- `file_url`: URL/path to the TF file
- `file_size_bytes`: Size of the TF file in bytes
- `checksum`: File checksum for integrity verification
- `status`: Processing status of the TF
- `created_at`: Timestamp when TF was created
- `received_at`: Timestamp when message was received by client (auto-generated)
- `metadata_json`: Full JSON metadata from ActiveMQ message

**Indexes:**
- `run_number` - for efficient run-based queries
- `created_at` - for time-based queries

### `runs`
Django model: `Run`
Stores run-level information and statistics:
- `run_number`: Unique run identifier (primary key)
- `start_time`: When the run started
- `end_time`: When the run ended (if applicable)
- `total_tfs`: Total number of TFs received for this run (auto-calculated)
- `run_conditions`: Text field for run configuration/conditions

**Database Backend Compatibility:**
The Django ORM automatically handles SQL dialect differences between SQLite, PostgreSQL, and MySQL, ensuring consistent behavior across all supported database backends.

## Configuration

The client supports both command-line arguments and configuration files (future feature). ActiveMQ connection parameters can be customized for different deployment environments.

### Security Considerations

- Use SSL connections for production deployments
- Store credentials securely (avoid command-line passwords in production)
- Consider using certificate-based authentication for ActiveMQ
- Database files should have appropriate file permissions
- For PostgreSQL/MySQL: Use dedicated database users with minimal required privileges
- Consider using environment variables or configuration files for sensitive database credentials

## Future Enhancements

- Configuration file support for easier deployment
- Web interface for monitoring visualization using Django views
- Real-time dashboard with statistics and charts
- Integration with existing monitoring systems
- Export capabilities for monitoring data (CSV, JSON)
- Database migration support for schema evolution
- Connection pooling for improved database performance
- Automated database backup and recovery tools



