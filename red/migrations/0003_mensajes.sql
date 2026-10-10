-- Mensajes de Void (ticket VV-008, M1). Van cifrados de extremo a extremo (HPKE, RFC 9180, en void.py): aquí solo se
-- guarda el sobre, que la red no puede abrir. La red sabe quién escribe a quién, cuándo y el tipo; nada más.
-- Un mensaje vive aquí solo hasta que el vault del destinatario lo recoge (entonces se borra) y, si nadie lo recoge,
-- como mucho 180 días [Alex, 10-oct: «o incluso un espacio específico dentro del vault»].

ALTER TABLE perfiles ADD COLUMN clave_publica TEXT;   -- X25519 en base64 (32 bytes); NULL hasta que la publica su vault

CREATE TABLE mensajes (
  id          INTEGER PRIMARY KEY,
  de_perfil   INTEGER NOT NULL REFERENCES perfiles(id) ON DELETE CASCADE,   -- lo pone la red desde la llave, nunca el cuerpo
  para_perfil INTEGER NOT NULL REFERENCES perfiles(id) ON DELETE CASCADE,
  tipo        TEXT NOT NULL CHECK (tipo IN ('PETICION', 'PROPUESTA', 'RESPUESTA', 'ESCALADA', 'AVISO')),   -- ninguno es ORDEN
  enc         TEXT NOT NULL CHECK (length(enc) BETWEEN 40 AND 48),          -- la clave efímera de HPKE, en base64
  sobre       TEXT NOT NULL CHECK (length(sobre) BETWEEN 24 AND 12000),     -- asunto y cuerpo, cifrados, en base64
  creado      INTEGER NOT NULL,
  caduca      INTEGER NOT NULL                                              -- creado + 180 días
);
CREATE INDEX mensajes_para ON mensajes (para_perfil, creado);

-- A quién has escrito alguna vez: solo para el tope de destinatarios nuevos al día. Se borra con la baja.
CREATE TABLE contactos (
  de_perfil   INTEGER NOT NULL REFERENCES perfiles(id) ON DELETE CASCADE,
  para_perfil INTEGER NOT NULL REFERENCES perfiles(id) ON DELETE CASCADE,
  primero     INTEGER NOT NULL,
  PRIMARY KEY (de_perfil, para_perfil)
);

CREATE TABLE bloqueos (
  perfil_id INTEGER NOT NULL REFERENCES perfiles(id) ON DELETE CASCADE,
  bloquea_a INTEGER NOT NULL REFERENCES perfiles(id) ON DELETE CASCADE,
  creado    INTEGER NOT NULL,
  PRIMARY KEY (perfil_id, bloquea_a)
);
