-- La red de Void (ticket VV-004, piezas P2 y P4). Lo que se guarda de cada persona: su alias, el nombre
-- de su agente y lo que ella marque como público. Ni correo, ni nombre real, ni nada de su vault.
-- De la llave solo se guarda su huella (sha256): con la base de datos entera no se puede firmar nada.

CREATE TABLE perfiles (
  id           INTEGER PRIMARY KEY,
  alias        TEXT NOT NULL UNIQUE,
  agente       TEXT NOT NULL,
  huella_llave TEXT NOT NULL UNIQUE,          -- sha256 en hex de la llave; la llave no se guarda nunca
  publico      TEXT NOT NULL DEFAULT '',      -- lo que la persona enseña, p. ej. 'agente,estrellas'; vacío = solo el alias
  creado       INTEGER NOT NULL               -- milisegundos
);

-- Qué estrella es de quién. La escribirá la pieza P3 al publicar con la llave; hasta entonces, Alex con
-- wrangler (ver red/README.md). No hay ninguna ruta en internet que la escriba.
CREATE TABLE autoria (
  estrella  TEXT PRIMARY KEY,
  perfil_id INTEGER NOT NULL REFERENCES perfiles(id) ON DELETE CASCADE
);

CREATE TABLE avisos (
  id        INTEGER PRIMARY KEY,
  estrella  TEXT NOT NULL,
  tipo      TEXT NOT NULL CHECK (tipo IN ('fallo', 'mejora', 'gracias')),
  texto     TEXT NOT NULL,
  de_perfil INTEGER REFERENCES perfiles(id) ON DELETE SET NULL,   -- NULL: quien lo mandó se dio de baja
  creado    INTEGER NOT NULL
);
CREATE INDEX avisos_por_estrella ON avisos (estrella, creado);
CREATE INDEX avisos_por_quien ON avisos (de_perfil, creado);

-- El límite de altas por hora. La IP no se guarda: solo un sha256 con una sal que vive aquí mismo,
-- y cada fila se borra a las dos horas.
CREATE TABLE ritmo (
  clave  TEXT NOT NULL,
  creado INTEGER NOT NULL
);
CREATE INDEX ritmo_por_clave ON ritmo (clave, creado);

CREATE TABLE ajustes (
  clave TEXT PRIMARY KEY,
  valor TEXT NOT NULL
);
