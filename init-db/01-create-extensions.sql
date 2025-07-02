-- Enable required PostgreSQL extensions for the fast monitoring database
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Grant necessary permissions to the postgres user
GRANT ALL PRIVILEGES ON DATABASE swf_fastmonitoring TO postgres;