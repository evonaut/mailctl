PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS virtual_domains (
  id INTEGER PRIMARY KEY ASC,
  name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS virtual_users (
  id INTEGER PRIMARY KEY ASC,
  domain_id INTEGER NOT NULL,
  password TEXT NOT NULL,
  email TEXT NOT NULL,
  FOREIGN KEY (domain_id) REFERENCES virtual_domains(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS virtual_aliases (
  id INTEGER PRIMARY KEY ASC,
  domain_id INTEGER NOT NULL,
  source TEXT NOT NULL,
  destination TEXT NOT NULL,
  created TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
  description TEXT,
  enabled BOOLEAN DEFAULT 1,
  FOREIGN KEY (domain_id) REFERENCES virtual_domains(id) ON DELETE CASCADE
);
