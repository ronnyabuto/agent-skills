CREATE UNIQUE INDEX normalized_code ON items (lower(trim(code)));
