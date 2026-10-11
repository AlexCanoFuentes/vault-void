-- 2026-10-11 · La identidad publicada no se duplica para abrir el plano humano.
ALTER TABLE web_vaults ADD COLUMN alojamiento_prueba TEXT;
CREATE TABLE web_enlaces (
  token_hash TEXT PRIMARY KEY,
  perfil_id INTEGER NOT NULL REFERENCES web_vaults(perfil_id) ON DELETE CASCADE,
  llave_hash TEXT NOT NULL,
  caduca INTEGER NOT NULL,
  usado INTEGER NOT NULL DEFAULT 0 CHECK(usado IN (0,1))
);
CREATE INDEX web_enlaces_caduca ON web_enlaces(caduca);
