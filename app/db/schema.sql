-- PRD section 15: Data Model

CREATE TABLE IF NOT EXISTS books (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    version TEXT NOT NULL DEFAULT '0.1',
    config_path TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PLANNED'
);

CREATE TABLE IF NOT EXISTS page_specs (
    id TEXT PRIMARY KEY,
    book_id TEXT NOT NULL REFERENCES books(id),
    sequence INTEGER NOT NULL,
    element TEXT NOT NULL,
    composition TEXT NOT NULL,
    density INTEGER NOT NULL,
    symmetry TEXT NOT NULL,
    scale TEXT NOT NULL,
    border TEXT NOT NULL,
    prompt TEXT,
    status TEXT NOT NULL DEFAULT 'PLANNED',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_page_specs_book ON page_specs(book_id);

CREATE TABLE IF NOT EXISTS assets (
    id TEXT PRIMARY KEY,
    page_spec_id TEXT REFERENCES page_specs(id),
    source_path TEXT NOT NULL,
    original_path TEXT NOT NULL,
    normalized_path TEXT,
    thumbnail_path TEXT,
    width INTEGER,
    height INTEGER,
    dpi INTEGER,
    file_size INTEGER,
    sha256 TEXT,
    phash TEXT,
    status TEXT NOT NULL DEFAULT 'INGESTED',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_assets_page_spec ON assets(page_spec_id);
CREATE INDEX IF NOT EXISTS idx_assets_sha256 ON assets(sha256);

CREATE TABLE IF NOT EXISTS qc_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id TEXT NOT NULL REFERENCES assets(id),
    resolution_score REAL,
    line_art_score REAL,
    text_detected INTEGER,
    gray_detected INTEGER,
    color_detected INTEGER,
    black_fill_score REAL,
    edge_quality_score REAL,
    duplicate_score REAL,
    overall_score REAL,
    machine_decision TEXT,
    notes TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_qc_results_asset ON qc_results(asset_id);

CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id TEXT NOT NULL REFERENCES assets(id),
    decision TEXT NOT NULL,
    quality INTEGER,
    complexity INTEGER,
    uniqueness INTEGER,
    notes TEXT,
    reviewed_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_reviews_asset ON reviews(asset_id);

CREATE TABLE IF NOT EXISTS book_pages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id TEXT NOT NULL REFERENCES books(id),
    asset_id TEXT NOT NULL REFERENCES assets(id),
    final_sequence INTEGER,
    page_role TEXT NOT NULL DEFAULT 'interior',
    status TEXT NOT NULL DEFAULT 'ORDERED'
);

CREATE INDEX IF NOT EXISTS idx_book_pages_book ON book_pages(book_id);
