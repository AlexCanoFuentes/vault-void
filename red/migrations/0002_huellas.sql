-- El vacío se llena (ticket VV-007, pieza C1). La huella de cada vault: solo cifras, nunca texto libre, así que no puede
-- llevar nada del vault. Una por perfil; se borra con la baja o al retirarla. (9-oct: de «planeta» a «huella», sin desplegar.)
CREATE TABLE huellas (
  perfil_id   INTEGER PRIMARY KEY REFERENCES perfiles(id) ON DELETE CASCADE,
  datos       TEXT NOT NULL,      -- la huella ya validada y normalizada (JSON)
  actualizado INTEGER NOT NULL    -- milisegundos
);
