CREATE TABLE comunidad_publicaciones (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  perfil_id INTEGER NOT NULL REFERENCES perfiles(id) ON DELETE CASCADE,
  tipo TEXT NOT NULL CHECK(tipo IN ('plaza','oficial')),
  texto TEXT NOT NULL CHECK(length(texto) BETWEEN 1 AND 1500),
  creado INTEGER NOT NULL,
  aprobacion TEXT NOT NULL UNIQUE
);
CREATE INDEX comunidad_orden ON comunidad_publicaciones(tipo,id);
CREATE TABLE comunidad_ritmo (
  token TEXT PRIMARY KEY,
  perfil_id INTEGER NOT NULL REFERENCES perfiles(id) ON DELETE CASCADE,
  creado INTEGER NOT NULL
);
CREATE TABLE comunidad_aprobaciones (
  token TEXT PRIMARY KEY,
  perfil_id INTEGER NOT NULL REFERENCES perfiles(id) ON DELETE CASCADE,
  sha TEXT NOT NULL,
  caduca INTEGER NOT NULL
);
CREATE TABLE comunidad_lecturas (
  perfil_id INTEGER PRIMARY KEY REFERENCES perfiles(id) ON DELETE CASCADE,
  plaza INTEGER NOT NULL DEFAULT 0,
  oficial INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE mensajes_recibos (
  de_perfil INTEGER NOT NULL REFERENCES perfiles(id) ON DELETE CASCADE,
  nonce TEXT NOT NULL,
  sha TEXT NOT NULL,
  para_perfil INTEGER NOT NULL REFERENCES perfiles(id) ON DELETE CASCADE,
  creado INTEGER NOT NULL,
  caduca INTEGER NOT NULL,
  procesado INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY(de_perfil,nonce)
);
