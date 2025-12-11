CREATE TABLE IF NOT EXISTS Services (
    service_id INTEGER PRIMARY KEY,
    host TEXT NOT NULL,
    url TEXT UNIQUE NOT NULL,
    last_check_time TEXT,
    last_check_status INTEGER,
    last_check_info TEXT,
);

