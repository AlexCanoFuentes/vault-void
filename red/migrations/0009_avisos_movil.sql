-- Avisos en el móvil cuando te llega un mensaje (23-oct-2026).
-- Solo la dirección que da el navegador para avisarle (no sus claves: el aviso va vacío) y de qué espacio es.
-- Un mismo navegador puede estar en dos espacios. Se borra con el espacio, con «Dejar de avisarme» o al caducar (404/410).
CREATE TABLE IF NOT EXISTS avisos_movil (
  perfil_id INTEGER NOT NULL,
  endpoint TEXT NOT NULL,
  creado INTEGER NOT NULL,
  PRIMARY KEY (perfil_id, endpoint)
);
CREATE INDEX IF NOT EXISTS avisos_movil_endpoint ON avisos_movil (endpoint);
