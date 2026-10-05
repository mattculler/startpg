CREATE TABLE IF NOT EXISTS Services (
    service_id INTEGER PRIMARY KEY,
    host TEXT NOT NULL,
    url TEXT UNIQUE NOT NULL,
    last_check_time TEXT,
    last_check_status INTEGER,
    last_check_info TEXT
);

-- Drive health from a drivecanary hub, when the config names one: a row for
-- each host it watches.
CREATE TABLE IF NOT EXISTS Drives (
    host TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    problems TEXT NOT NULL,
    url TEXT NOT NULL
);
