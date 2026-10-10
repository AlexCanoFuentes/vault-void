-- Las huellas que nacen en el cuento (vaultvoid.app/tu-huella), antes de que exista el vault [Alex, 10-oct: «cada huella
-- creada va de forma persistente y al dia al lienzo»]. Solo cifras, como las de los vaults: las palabras no salen del
-- navegador. Quien la creó guarda una contraseña (token) en su navegador para actualizarla, y su vault la reclama al
-- publicar la suya: entonces esta fila se borra y en el lienzo queda la del vault.
CREATE TABLE huellas_cuento (
  id           INTEGER PRIMARY KEY,
  token_hash   TEXT NOT NULL UNIQUE,   -- sha256 del token; el token solo lo tiene el navegador (y el vault, si lo reclama)
  datos        TEXT NOT NULL,          -- la huella ya validada y normalizada (JSON, solo cifras)
  creado       INTEGER NOT NULL,
  actualizado  INTEGER NOT NULL
);

-- La huella del cuento es el principio de la del vault [Alex, 10-oct: «la huella que sale del cuento es el inicio de la
-- del vault no? lo enlazamos directo»]: al reclamarla, el vault hereda su semilla (dónde nace y su forma de partida) y su
-- color, y desde ahí crece con sus cifras.
ALTER TABLE huellas ADD COLUMN semilla TEXT;   -- p. ej. 'cuento:12'; NULL: la semilla es el alias
