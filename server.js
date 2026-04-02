const express = require('express');
const { Pool } = require('pg');
const cors = require('cors');
const app = express();
app.use(cors());
app.use(express.json());

const pool = new Pool({
  host: 'localhost',
  database: 'ubesol',
  user: 'postgres',
  password: 'ubesol2026',
  port: 5432
});

// ─── TRABAJADORES ─────────────────────────────────────────────────────────────
app.get('/api/trabajadores', async (req, res) => {
  try {
    const { dept } = req.query;
    let sql = 'SELECT * FROM trabajadores ORDER BY nombre';
    let params = [];
    if (dept) {
      sql = 'SELECT * FROM trabajadores WHERE departamento = $1 ORDER BY nombre';
      params = [dept];
    }
    const r = await pool.query(sql, params);
    res.json(r.rows);
  } catch(e) {
    res.status(500).json({ error: e.message });
  }
});

app.delete('/api/trabajadores/:id', async (req, res) => {
  try {
    await pool.query('DELETE FROM trabajadores WHERE id = $1', [req.params.id]);
    res.json({ ok: true });
  } catch(e) {
    res.status(500).json({ error: e.message });
  }
});

app.post('/api/trabajadores/batch', async (req, res) => {
  const { trabajadores, deletedDnis = [] } = req.body;
  if (!Array.isArray(trabajadores)) return res.status(400).json({ error: 'Faltan datos' });
  const client = await pool.connect();
  try {
    await client.query('BEGIN');
    if (deletedDnis.length > 0) {
      await client.query('DELETE FROM trabajadores WHERE dni = ANY($1::text[])', [deletedDnis]);
    }
    for (const t of trabajadores) {
      const dni  = (t.dni  || '').trim().toUpperCase();
      const nom  = (t.nombre || '').trim().toUpperCase();
      const dept = (t.departamento || 'Envasado').trim();
      if (!dni || !nom) continue;
      await client.query(`
        INSERT INTO trabajadores (dni, nombre, departamento)
        VALUES ($1, $2, $3)
        ON CONFLICT (dni) DO UPDATE
          SET nombre = EXCLUDED.nombre,
              departamento = EXCLUDED.departamento
      `, [dni, nom, dept]);
    }
    await client.query('COMMIT');
    res.json({ ok: true, total: trabajadores.length });
  } catch(e) {
    await client.query('ROLLBACK');
    res.status(500).json({ error: e.message });
  } finally {
    client.release();
  }
});

// ─── HORAS EXTRAS ─────────────────────────────────────────────────────────────
app.get('/api/horas_extras', async (req, res) => {
  try {
    const r = await pool.query(
      'SELECT fecha, responsable, datos FROM horas_extras ORDER BY fecha DESC LIMIT 60'
    );
    res.json(r.rows);
  } catch(e) {
    res.status(500).json({ error: e.message });
  }
});

app.get('/api/horas_extras/:fecha', async (req, res) => {
  try {
    const r = await pool.query(
      'SELECT datos FROM horas_extras WHERE fecha = $1',
      [req.params.fecha]
    );
    if (r.rows.length === 0) return res.json(null);
    res.json(r.rows[0].datos);
  } catch(e) {
    res.status(500).json({ error: e.message });
  }
});

app.post('/api/horas_extras', async (req, res) => {
  const { fecha, responsable, datos } = req.body;
  if (!fecha || !datos) return res.status(400).json({ error: 'Faltan datos' });
  try {
    await pool.query(`
      INSERT INTO horas_extras (fecha, responsable, datos)
      VALUES ($1, $2, $3)
      ON CONFLICT (fecha) DO UPDATE
        SET responsable  = EXCLUDED.responsable,
            datos        = EXCLUDED.datos,
            publicado_en = NOW()
    `, [fecha, responsable || '', JSON.stringify(datos)]);
    res.json({ ok: true });
  } catch(e) {
    res.status(500).json({ error: e.message });
  }
});

// ─── CONFIG ESTRUCTURA ────────────────────────────────────────────────────────
app.get('/api/config_estructura', async (req, res) => {
  try {
    const r = await pool.query("SELECT datos FROM config_estructura WHERE id = 'estructura'");
    if (!r.rows.length) return res.json(null);
    res.json(r.rows[0].datos);
  } catch(e) {
    res.status(500).json({ error: e.message });
  }
});

app.put('/api/config_estructura', async (req, res) => {
  try {
    await pool.query(`
      INSERT INTO config_estructura (id, datos)
      VALUES ('estructura', $1)
      ON CONFLICT (id) DO UPDATE SET datos = EXCLUDED.datos
    `, [JSON.stringify(req.body)]);
    res.json({ ok: true });
  } catch(e) {
    res.status(500).json({ error: e.message });
  }
});

// ─── CUADRANTES ───────────────────────────────────────────────────────────────
app.get('/api/cuadrantes', async (req, res) => {
  try {
    const { semKey } = req.query;
    let r;
    if (semKey) {
      r = await pool.query("SELECT id, semana, ano, dept, datos FROM cuadrantes WHERE id LIKE $1", ['%' + semKey + '%']);
    } else {
      r = await pool.query("SELECT id, semana, ano, dept, datos FROM cuadrantes ORDER BY ano DESC, semana DESC");
    }
    res.json(r.rows);
  } catch(e) {
    res.status(500).json({ error: e.message });
  }
});

app.put('/api/cuadrantes/:id', async (req, res) => {
  const { id } = req.params;
  const payload = req.body;
  try {
    await pool.query(`
      INSERT INTO cuadrantes (id, semana, ano, dept, datos)
      VALUES ($1, $2, $3, $4, $5)
      ON CONFLICT (id) DO UPDATE
        SET semana = EXCLUDED.semana,
            ano    = EXCLUDED.ano,
            dept   = EXCLUDED.dept,
            datos  = EXCLUDED.datos
    `, [
      id,
      String(payload.semana || ''),
      String(payload.ano || ''),
      payload.dept || '',
      JSON.stringify(payload)
    ]);
    res.json({ ok: true });
  } catch(e) {
    res.status(500).json({ error: e.message });
  }
});

app.delete('/api/cuadrantes/:id', async (req, res) => {
  try {
    await pool.query('DELETE FROM cuadrantes WHERE id = $1', [req.params.id]);
    res.json({ ok: true });
  } catch(e) {
    res.status(500).json({ error: e.message });
  }
});

// ─── BORRADO MASIVO (para limpiar.html) ──────────────────────────────────────
app.delete('/api/cuadrantes/all', async (req, res) => {
  try {
    const r = await pool.query('DELETE FROM cuadrantes RETURNING id');
    res.json({ ok: true, deleted: r.rowCount });
  } catch(e) {
    res.status(500).json({ error: e.message });
  }
});

app.delete('/api/horas_extras/all', async (req, res) => {
  try {
    const r = await pool.query('DELETE FROM horas_extras RETURNING id');
    res.json({ ok: true, deleted: r.rowCount });
  } catch(e) {
    res.status(500).json({ error: e.message });
  }
});

app.delete('/api/epis/all', async (req, res) => {
  try {
    const r = await pool.query('DELETE FROM epis RETURNING id');
    res.json({ ok: true, deleted: r.rowCount });
  } catch(e) {
    res.status(500).json({ error: e.message });
  }
});


// ─── INICIO ───────────────────────────────────────────────────────────────────
const PORT = 5000;
app.listen(PORT, () => console.log(`API Ubesol escuchando en puerto ${PORT}`));
