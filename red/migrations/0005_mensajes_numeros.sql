-- Revisión 2026-10-10: un mensaje recogido vive en el vault y se responde por su número.
-- INTEGER PRIMARY KEY reutilizaba el número al vaciar la bandeja. Conservamos las filas y sus números;
-- AUTOINCREMENT impide que otra persona reciba después un mensaje distinto con el mismo número.
CREATE TABLE mensajes_nuevos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  de_perfil INTEGER NOT NULL REFERENCES perfiles(id) ON DELETE CASCADE,
  para_perfil INTEGER NOT NULL REFERENCES perfiles(id) ON DELETE CASCADE,
  tipo TEXT NOT NULL CHECK (tipo IN ('PETICION', 'PROPUESTA', 'RESPUESTA', 'ESCALADA', 'AVISO')),
  enc TEXT NOT NULL CHECK (length(enc) BETWEEN 40 AND 48),
  sobre TEXT NOT NULL CHECK (length(sobre) BETWEEN 24 AND 12000),
  creado INTEGER NOT NULL,
  caduca INTEGER NOT NULL
);
INSERT INTO mensajes_nuevos SELECT * FROM mensajes;
DROP TABLE mensajes;
ALTER TABLE mensajes_nuevos RENAME TO mensajes;
CREATE INDEX mensajes_para ON mensajes (para_perfil, creado);
