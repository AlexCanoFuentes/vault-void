-- El vacío se llena (ticket VV-007, pieza C1). El planeta de cada vault: solo cifras y palabras de una lista cerrada,
-- nunca texto libre, así que no puede llevar nada del vault. Uno por perfil; se borra con la baja o al retirarlo.
CREATE TABLE planetas (
  perfil_id   INTEGER PRIMARY KEY REFERENCES perfiles(id) ON DELETE CASCADE,
  datos       TEXT NOT NULL,      -- el planeta ya validado y normalizado (JSON)
  actualizado INTEGER NOT NULL    -- milisegundos
);
