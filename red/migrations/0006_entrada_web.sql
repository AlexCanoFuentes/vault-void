-- 2026-10-11 · VV-010. Las palabras se guardan en el vault privado, nunca aquí.
CREATE TABLE cuento_vinculos (
  token_hash TEXT PRIMARY KEY,
  cuento_id INTEGER NOT NULL UNIQUE,
  perfil_id INTEGER NOT NULL UNIQUE REFERENCES perfiles(id) ON DELETE CASCADE
);
CREATE TABLE web_vaults (
  perfil_id INTEGER PRIMARY KEY REFERENCES perfiles(id) ON DELETE CASCADE,
  recuperacion_hash TEXT NOT NULL UNIQUE,
  listo INTEGER NOT NULL DEFAULT 0 CHECK(listo IN (0,1)),
  creado INTEGER NOT NULL
);
CREATE TABLE web_sesiones (
  token_hash TEXT PRIMARY KEY,
  perfil_id INTEGER NOT NULL REFERENCES web_vaults(perfil_id) ON DELETE CASCADE,
  caduca INTEGER NOT NULL
);
CREATE INDEX web_sesiones_caduca ON web_sesiones(caduca);
