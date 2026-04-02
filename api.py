from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
import psycopg2.extras
import json

app = Flask(__name__)
CORS(app)

DB = {'host':'localhost','database':'ubesol','user':'ubesol_api','password':'ubesol2026api'}

def get_conn():
    return psycopg2.connect(**DB)

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS lineas (id SERIAL PRIMARY KEY, nombre TEXT NOT NULL, activa BOOLEAN DEFAULT TRUE, creada_en TIMESTAMP DEFAULT NOW());""")
    cur.execute("""CREATE TABLE IF NOT EXISTS revisiones_bombas (id SERIAL PRIMARY KEY, linea TEXT NOT NULL, fecha DATE NOT NULL, of TEXT, codigo TEXT, producto TEXT, hora TIME NOT NULL, ok INTEGER NOT NULL, ko INTEGER NOT NULL, operario TEXT, creada_en TIMESTAMP DEFAULT NOW());""")
    cur.execute("""CREATE TABLE IF NOT EXISTS rotaciones (id SERIAL PRIMARY KEY, linea TEXT NOT NULL, fecha DATE NOT NULL, of TEXT, codigo TEXT, producto TEXT, turno TEXT, resp_linea TEXT, oper_maquina TEXT, encargado TEXT, hora TIME NOT NULL, posicion TEXT NOT NULL, operario TEXT, creada_en TIMESTAMP DEFAULT NOW());""")
    cur.execute("""CREATE TABLE IF NOT EXISTS lyd_registros (id SERIAL PRIMARY KEY, tipo TEXT NOT NULL, linea TEXT, fecha DATE NOT NULL, hora TIME, responsable TEXT, datos JSONB, creada_en TIMESTAMP DEFAULT NOW());""")
    cur.execute("""CREATE TABLE IF NOT EXISTS trabajadores (id SERIAL PRIMARY KEY, dni VARCHAR(9) NOT NULL UNIQUE, nombre VARCHAR(120) NOT NULL, departamento VARCHAR(50) NOT NULL);""")
    cur.execute("""CREATE TABLE IF NOT EXISTS horas_extras (id SERIAL PRIMARY KEY, fecha DATE NOT NULL UNIQUE, responsable VARCHAR(120), datos JSONB NOT NULL DEFAULT '{}', publicado_en TIMESTAMP DEFAULT NOW());""")
    conn.commit(); cur.close(); conn.close()
    print("BD inicializada")

@app.route('/api/health')
def health():
    return jsonify({'status':'ok'})

@app.route('/api/lineas', methods=['GET'])
def get_lineas():
    conn=get_conn(); cur=conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM lineas WHERE activa=TRUE ORDER BY nombre")
    rows=cur.fetchall(); cur.close(); conn.close()
    return jsonify(list(rows))

@app.route('/api/lineas', methods=['POST'])
def add_linea():
    data=request.json; conn=get_conn(); cur=conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("INSERT INTO lineas (nombre) VALUES (%s) RETURNING *",(data['nombre'],))
    row=cur.fetchone(); conn.commit(); cur.close(); conn.close()
    return jsonify(dict(row)),201

@app.route('/api/bombas', methods=['POST'])
def save_bombas():
    data=request.json; conn=get_conn(); cur=conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    for r in data.get('registros',[]):
        cur.execute("INSERT INTO revisiones_bombas (linea,fecha,of,codigo,producto,hora,ok,ko,operario) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",(data['linea'],data['fecha'],data.get('of'),data.get('codigo'),data.get('producto'),r['hora'],r['ok'],r['ko'],r.get('operario')))
    conn.commit(); cur.close(); conn.close()
    return jsonify({'ok':True}),201

@app.route('/api/bombas', methods=['GET'])
def get_bombas():
    conn=get_conn(); cur=conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    q="SELECT * FROM revisiones_bombas WHERE 1=1"; params=[]
    if request.args.get('linea'): q+=" AND linea=%s"; params.append(request.args['linea'])
    if request.args.get('desde'): q+=" AND fecha>=%s"; params.append(request.args['desde'])
    if request.args.get('hasta'): q+=" AND fecha<=%s"; params.append(request.args['hasta'])
    q+=" ORDER BY fecha DESC,hora DESC"
    cur.execute(q,params); rows=cur.fetchall(); cur.close(); conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/rotaciones', methods=['POST'])
def save_rotacion():
    data=request.json; conn=get_conn(); cur=conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    for p in data.get('posiciones',[]):
        cur.execute("INSERT INTO rotaciones (linea,fecha,of,codigo,producto,turno,resp_linea,oper_maquina,encargado,hora,posicion,operario) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",(data['linea'],data['fecha'],data.get('of'),data.get('codigo'),data.get('producto'),data.get('turno'),data.get('resp_linea'),data.get('oper_maquina'),data.get('encargado'),p['hora'],p['posicion'],p.get('operario')))
    conn.commit(); cur.close(); conn.close()
    return jsonify({'ok':True}),201

@app.route('/api/rotaciones', methods=['GET'])
def get_rotaciones():
    conn=get_conn(); cur=conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    q="SELECT * FROM rotaciones WHERE 1=1"; params=[]
    if request.args.get('linea'): q+=" AND linea=%s"; params.append(request.args['linea'])
    if request.args.get('desde'): q+=" AND fecha>=%s"; params.append(request.args['desde'])
    if request.args.get('hasta'): q+=" AND fecha<=%s"; params.append(request.args['hasta'])
    q+=" ORDER BY fecha DESC,hora DESC"
    cur.execute(q,params); rows=cur.fetchall(); cur.close(); conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/lyd', methods=['POST'])
def save_lyd():
    data=request.json; conn=get_conn(); cur=conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("INSERT INTO lyd_registros (tipo,linea,fecha,hora,responsable,datos) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",(data['tipo'],data.get('linea'),data['fecha'],data.get('hora'),data.get('responsable'),psycopg2.extras.Json(data.get('datos',{}))))
    row=cur.fetchone(); conn.commit(); cur.close(); conn.close()
    return jsonify({'ok':True,'id':row['id']}),201

@app.route('/api/lyd', methods=['GET'])
def get_lyd():
    conn=get_conn(); cur=conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    q="SELECT * FROM lyd_registros WHERE 1=1"; params=[]
    if request.args.get('tipo'): q+=" AND tipo=%s"; params.append(request.args['tipo'])
    if request.args.get('desde'): q+=" AND fecha>=%s"; params.append(request.args['desde'])
    if request.args.get('hasta'): q+=" AND fecha<=%s"; params.append(request.args['hasta'])
    q+=" ORDER BY fecha DESC,hora DESC"
    cur.execute(q,params); rows=cur.fetchall(); cur.close(); conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/televisiones', methods=['GET'])
def get_televisiones():
    conn=get_conn(); cur=conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM televisiones ORDER BY tv_id")
    rows=cur.fetchall(); cur.close(); conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/televisiones/<tv_id>', methods=['GET'])
def get_television(tv_id):
    conn=get_conn(); cur=conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM televisiones WHERE tv_id=%s",(tv_id,))
    row=cur.fetchone(); cur.close(); conn.close()
    if not row: return jsonify({'urls':[]})
    return jsonify(dict(row))

@app.route('/api/televisiones/<tv_id>', methods=['POST'])
def save_television(tv_id):
    data=request.json; conn=get_conn(); cur=conn.cursor()
    cur.execute("""INSERT INTO televisiones (tv_id, nombre, urls) VALUES (%s,%s,%s)
        ON CONFLICT (tv_id) DO UPDATE SET nombre=EXCLUDED.nombre, urls=EXCLUDED.urls""",
        (tv_id, data.get('nombre','TV'), psycopg2.extras.Json(data.get('urls',[]))))
    conn.commit(); cur.close(); conn.close()
    return jsonify({'ok':True})

@app.route('/api/ts/projects', methods=['GET'])
def get_ts_projects():
    conn=get_conn(); cur=conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM ts_projects ORDER BY created_at")
    rows=cur.fetchall(); cur.close(); conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/ts/projects', methods=['POST'])
def add_ts_project():
    data=request.json; conn=get_conn(); cur=conn.cursor()
    import uuid, time
    id=str(uuid.uuid4())
    cur.execute("INSERT INTO ts_projects (id,name,dept,type,unit,mins,descr,created_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
        (id,data['name'],data.get('dept',''),data['type'],data['unit'],data['mins'],data.get('desc',''),int(time.time()*1000)))
    conn.commit(); cur.close(); conn.close()
    return jsonify({'ok':True,'id':id}),201

@app.route('/api/ts/projects/<pid>', methods=['PUT'])
def update_ts_project(pid):
    data=request.json; conn=get_conn(); cur=conn.cursor()
    cur.execute("UPDATE ts_projects SET name=%s,dept=%s,type=%s,unit=%s,mins=%s,descr=%s WHERE id=%s",
        (data['name'],data.get('dept',''),data['type'],data['unit'],data['mins'],data.get('desc',''),pid))
    conn.commit(); cur.close(); conn.close()
    return jsonify({'ok':True})

@app.route('/api/ts/projects/<pid>', methods=['DELETE'])
def delete_ts_project(pid):
    conn=get_conn(); cur=conn.cursor()
    cur.execute("DELETE FROM ts_records WHERE pid=%s",(pid,))
    cur.execute("DELETE FROM ts_projects WHERE id=%s",(pid,))
    conn.commit(); cur.close(); conn.close()
    return jsonify({'ok':True})

@app.route('/api/ts/records', methods=['GET'])
def get_ts_records():
    conn=get_conn(); cur=conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM ts_records ORDER BY period DESC")
    rows=cur.fetchall(); cur.close(); conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/ts/records', methods=['POST'])
def add_ts_record():
    data=request.json; conn=get_conn(); cur=conn.cursor()
    import uuid, time
    id=str(uuid.uuid4())
    cur.execute("INSERT INTO ts_records (id,pid,type,period,units,prev_year,curr_year,diff,usuario,saved_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (id,data['pid'],data['type'],data['period'],data.get('units'),data.get('prevYear'),data.get('currYear'),data.get('diff'),data.get('user','Anonimo'),int(time.time()*1000)))
    conn.commit(); cur.close(); conn.close()
    return jsonify({'ok':True,'id':id}),201

@app.route('/api/ts/records/<rid>', methods=['DELETE'])
def delete_ts_record(rid):
    conn=get_conn(); cur=conn.cursor()
    cur.execute("DELETE FROM ts_records WHERE id=%s",(rid,))
    conn.commit(); cur.close(); conn.close()
    return jsonify({'ok':True})

import uuid

def new_id():
    return str(uuid.uuid4())[:8]

@app.route('/api/lyd/equip', methods=['GET'])
def get_lyd_equip():
    conn = get_conn(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    tipo = request.args.get('tipo')
    if tipo:
        cur.execute("SELECT * FROM lyd_equip WHERE activo=TRUE AND tipo=%s ORDER BY nombre", (tipo,))
    else:
        cur.execute("SELECT * FROM lyd_equip WHERE activo=TRUE ORDER BY tipo, nombre")
    rows = cur.fetchall(); cur.close(); conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/lyd/equip', methods=['POST'])
def add_lyd_equip():
    data = request.json
    conn = get_conn(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    eid = data.get('id') or new_id()
    cur.execute(
        "INSERT INTO lyd_equip (id, tipo, nombre, codigo, activo) VALUES (%s,%s,%s,%s,%s) RETURNING *",
        (eid, data['tipo'], data['nombre'], data.get('codigo', data['nombre']), data.get('activo', True))
    )
    row = cur.fetchone(); conn.commit(); cur.close(); conn.close()
    return jsonify(dict(row)), 201

@app.route('/api/lyd/equip/<eid>', methods=['DELETE'])
def del_lyd_equip(eid):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("DELETE FROM lyd_equip WHERE id=%s", (eid,))
    conn.commit(); cur.close(); conn.close()
    return jsonify({'ok': True})

@app.route('/api/lyd/steps', methods=['GET'])
def get_lyd_steps():
    conn = get_conn(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM lyd_steps ORDER BY orden")
    rows = cur.fetchall(); cur.close(); conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/lyd/steps', methods=['POST'])
def add_lyd_step():
    data = request.json
    conn = get_conn(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    sid = data.get('id') or new_id()
    cur.execute(
        """INSERT INTO lyd_steps (id, step_id, nombre, seccion, descripcion, req_op, req_time, activo, orden)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
           ON CONFLICT (id) DO UPDATE SET
             step_id=EXCLUDED.step_id, nombre=EXCLUDED.nombre, seccion=EXCLUDED.seccion,
             descripcion=EXCLUDED.descripcion, req_op=EXCLUDED.req_op, req_time=EXCLUDED.req_time,
             activo=EXCLUDED.activo, orden=EXCLUDED.orden
           RETURNING *""",
        (sid, data.get('stepId',''), data['nombre'], data.get('seccion',''),
         data.get('desc',''), data.get('reqOp', True), data.get('reqTime', False),
         data.get('activo', True), data.get('orden', 99))
    )
    row = cur.fetchone(); conn.commit(); cur.close(); conn.close()
    return jsonify(dict(row)), 201

@app.route('/api/lyd/steps/<sid>', methods=['PUT'])
def update_lyd_step(sid):
    data = request.json
    conn = get_conn(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        """UPDATE lyd_steps SET step_id=%s, nombre=%s, seccion=%s, descripcion=%s,
           req_op=%s, req_time=%s, activo=%s, orden=%s WHERE id=%s RETURNING *""",
        (data.get('stepId',''), data['nombre'], data.get('seccion',''),
         data.get('desc',''), data.get('reqOp', True), data.get('reqTime', False),
         data.get('activo', True), data.get('orden', 99), sid)
    )
    row = cur.fetchone(); conn.commit(); cur.close(); conn.close()
    return jsonify(dict(row) if row else {'ok': False})

@app.route('/api/lyd/steps/<sid>', methods=['DELETE'])
def del_lyd_step(sid):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("DELETE FROM lyd_steps WHERE id=%s", (sid,))
    conn.commit(); cur.close(); conn.close()
    return jsonify({'ok': True})

@app.route('/api/lyd/steps/reorder', methods=['POST'])
def reorder_lyd_steps():
    items = request.json
    conn = get_conn(); cur = conn.cursor()
    for item in items:
        cur.execute("UPDATE lyd_steps SET orden=%s WHERE id=%s", (item['orden'], item['id']))
    conn.commit(); cur.close(); conn.close()
    return jsonify({'ok': True})

@app.route('/api/lyd/users', methods=['GET'])
def get_lyd_users():
    conn = get_conn(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM lyd_users ORDER BY nombre")
    rows = cur.fetchall(); cur.close(); conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/lyd/users', methods=['POST'])
def add_lyd_user():
    data = request.json
    conn = get_conn(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    uid = data.get('id') or new_id()
    try:
        cur.execute(
            "INSERT INTO lyd_users (id, nombre, usuario, pass, rol) VALUES (%s,%s,%s,%s,%s) RETURNING *",
            (uid, data['nombre'], data['user'], data['pass'], data.get('rol', 'viewer'))
        )
        row = cur.fetchone(); conn.commit(); cur.close(); conn.close()
        return jsonify(dict(row)), 201
    except Exception as e:
        conn.rollback(); cur.close(); conn.close()
        return jsonify({'ok': False, 'error': str(e)}), 409

@app.route('/api/lyd/users/<uid>', methods=['DELETE'])
def del_lyd_user(uid):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("DELETE FROM lyd_users WHERE id=%s", (uid,))
    conn.commit(); cur.close(); conn.close()
    return jsonify({'ok': True})

@app.route('/api/fab/ordenes', methods=['GET'])
def get_fab_ordenes():
    conn = get_conn(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    estado = request.args.get('estado')
    if estado:
        cur.execute("SELECT * FROM fab_ordenes WHERE estado=%s ORDER BY fecha DESC, creado_en DESC", (estado,))
    else:
        cur.execute("SELECT * FROM fab_ordenes ORDER BY fecha DESC, creado_en DESC")
    rows = cur.fetchall(); cur.close(); conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/fab/ordenes', methods=['POST'])
def add_fab_orden():
    data = request.json
    conn = get_conn(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    oid = data.get('id') or new_id()
    cur.execute(
        """INSERT INTO fab_ordenes (id, n_orden, reactor, formula, descripcion, cantidad,
           observaciones, fecha, estado, creado_en)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *""",
        (oid, data.get('nOrden',''), data.get('reactor',''), data.get('formula',''),
         data.get('descripcion',''), data.get('cantidad',''), data.get('observaciones',''),
         data.get('fecha',''), data.get('estado','pendiente'), data.get('creadoEn',''))
    )
    row = cur.fetchone(); conn.commit(); cur.close(); conn.close()
    return jsonify(dict(row)), 201

@app.route('/api/fab/ordenes/<oid>', methods=['PUT'])
def update_fab_orden(oid):
    data = request.json
    conn = get_conn(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    mapping = {
        'estado':'estado', 'iniciadoEn':'iniciado_en', 'finalizadoEn':'finalizado_en',
        'reactor':'reactor', 'formula':'formula', 'descripcion':'descripcion',
        'cantidad':'cantidad', 'nOrden':'n_orden', 'observaciones':'observaciones', 'fecha':'fecha'
    }
    fields = []; values = []
    for js_key, sql_col in mapping.items():
        if js_key in data:
            fields.append(f"{sql_col}=%s"); values.append(data[js_key])
    if not fields:
        return jsonify({'ok': False, 'error': 'nada que actualizar'}), 400
    values.append(oid)
    cur.execute(f"UPDATE fab_ordenes SET {', '.join(fields)} WHERE id=%s RETURNING *", values)
    row = cur.fetchone(); conn.commit(); cur.close(); conn.close()
    return jsonify(dict(row) if row else {'ok': False})

@app.route('/api/fab/ordenes/<oid>', methods=['DELETE'])
def del_fab_orden(oid):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("DELETE FROM fab_ordenes WHERE id=%s", (oid,))
    conn.commit(); cur.close(); conn.close()
    return jsonify({'ok': True})

@app.route('/api/fab/registros', methods=['GET'])
def get_fab_registros():
    conn = get_conn(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    estado  = request.args.get('estado')
    reactor = request.args.get('reactor')
    limit   = request.args.get('limit', 200)
    q = "SELECT * FROM fab_registros WHERE 1=1"; params = []
    if estado:  q += " AND estado=%s";  params.append(estado)
    if reactor: q += " AND reactor=%s"; params.append(reactor)
    q += " ORDER BY creado_en DESC LIMIT %s"; params.append(limit)
    cur.execute(q, params)
    rows = cur.fetchall(); cur.close(); conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/fab/registros', methods=['POST'])
def add_fab_registro():
    data = request.json
    conn = get_conn(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    rid = data.get('id') or new_id()
    cur.execute(
        """INSERT INTO fab_registros (id, reactor, producto_actual, producto_siguiente,
           operario, inicio_hora, estado, creado_en, n_orden, cantidad, descripcion, orden_id)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *""",
        (rid, data.get('reactor',''), data.get('productoActual',''), data.get('productoSiguiente',''),
         data.get('operario',''), data.get('inicioHora',''), data.get('estado','en_curso'),
         data.get('creadoEn',''), data.get('nOrden',''), data.get('cantidad',''),
         data.get('descripcion',''), data.get('ordenId',''))
    )
    row = cur.fetchone(); conn.commit(); cur.close(); conn.close()
    return jsonify(dict(row)), 201

@app.route('/api/fab/registros/<rid>', methods=['PUT'])
def update_fab_registro(rid):
    data = request.json
    conn = get_conn(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    mapping = {
        'estado':'estado', 'finHora':'fin_hora',
        'productoSiguiente':'producto_siguiente', 'operario':'operario'
    }
    fields = []; values = []
    for js_key, sql_col in mapping.items():
        if js_key in data:
            fields.append(f"{sql_col}=%s"); values.append(data[js_key])
    if not fields:
        return jsonify({'ok': False, 'error': 'nada que actualizar'}), 400
    values.append(rid)
    cur.execute(f"UPDATE fab_registros SET {', '.join(fields)} WHERE id=%s RETURNING *", values)
    row = cur.fetchone(); conn.commit(); cur.close(); conn.close()
    return jsonify(dict(row) if row else {'ok': False})

@app.route('/api/lyd/tv-config', methods=['GET'])
def get_tv_config():
    conn = get_conn(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT tv1, tv2 FROM lyd_tv_config WHERE id='default'")
    row = cur.fetchone(); cur.close(); conn.close()
    if row:
        return jsonify({'tv1': row['tv1'] or [], 'tv2': row['tv2'] or []})
    return jsonify({'tv1': [], 'tv2': []})

@app.route('/api/lyd/tv-config', methods=['POST'])
def save_tv_config():
    data = request.json
    conn = get_conn(); cur = conn.cursor()
    cur.execute(
        """INSERT INTO lyd_tv_config (id, tv1, tv2) VALUES ('default', %s, %s)
           ON CONFLICT (id) DO UPDATE SET tv1=EXCLUDED.tv1, tv2=EXCLUDED.tv2""",
        (psycopg2.extras.Json(data.get('tv1', [])),
         psycopg2.extras.Json(data.get('tv2', [])))
    )
    conn.commit(); cur.close(); conn.close()
    return jsonify({'ok': True})

# ─── TRABAJADORES ─────────────────────────────────────────────────────────────

@app.route('/api/trabajadores', methods=['GET'])
def get_trabajadores():
    conn = get_conn(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    dept = request.args.get('dept')
    if dept:
        cur.execute("SELECT * FROM trabajadores WHERE departamento=%s ORDER BY nombre", (dept,))
    else:
        cur.execute("SELECT * FROM trabajadores ORDER BY nombre")
    rows = cur.fetchall(); cur.close(); conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/trabajadores/batch', methods=['POST'])
def batch_trabajadores():
    data = request.json
    trabajadores = data.get('trabajadores', [])
    deleted_dnis = data.get('deletedDnis', [])
    conn = get_conn(); cur = conn.cursor()
    try:
        if deleted_dnis:
            cur.execute("DELETE FROM trabajadores WHERE dni = ANY(%s)", (deleted_dnis,))
        for t in trabajadores:
            dni  = (t.get('dni') or '').strip().upper()
            nom  = (t.get('nombre') or '').strip().upper()
            dept = (t.get('departamento') or 'Envasado').strip()
            if not dni or not nom: continue
            cur.execute("""
                INSERT INTO trabajadores (dni, nombre, departamento)
                VALUES (%s, %s, %s)
                ON CONFLICT (dni) DO UPDATE
                  SET nombre=EXCLUDED.nombre, departamento=EXCLUDED.departamento
            """, (dni, nom, dept))
        conn.commit(); cur.close(); conn.close()
        return jsonify({'ok': True, 'total': len(trabajadores)})
    except Exception as e:
        conn.rollback(); cur.close(); conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/trabajadores/<int:tid>', methods=['DELETE'])
def delete_trabajador(tid):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("DELETE FROM trabajadores WHERE id=%s", (tid,))
    conn.commit(); cur.close(); conn.close()
    return jsonify({'ok': True})

# ─── HORAS EXTRAS ─────────────────────────────────────────────────────────────

@app.route('/api/horas_extras', methods=['GET'])
def get_horas_extras():
    conn = get_conn(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT fecha, responsable, datos FROM horas_extras ORDER BY fecha DESC LIMIT 60")
    rows = cur.fetchall(); cur.close(); conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/horas_extras/<fecha>', methods=['GET'])
def get_horas_extras_fecha(fecha):
    conn = get_conn(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT datos FROM horas_extras WHERE fecha=%s", (fecha,))
    row = cur.fetchone(); cur.close(); conn.close()
    if not row: return jsonify(None)
    return jsonify(row['datos'])

@app.route('/api/horas_extras', methods=['POST'])
def save_horas_extras():
    data = request.json
    fecha      = data.get('fecha')
    responsable = data.get('responsable', '')
    datos      = data.get('datos')
    if not fecha or datos is None:
        return jsonify({'error': 'Faltan datos'}), 400
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO horas_extras (fecha, responsable, datos)
            VALUES (%s, %s, %s)
            ON CONFLICT (fecha) DO UPDATE
              SET responsable=EXCLUDED.responsable,
                  datos=EXCLUDED.datos,
                  publicado_en=NOW()
        """, (fecha, responsable, psycopg2.extras.Json(datos)))
        conn.commit(); cur.close(); conn.close()
        return jsonify({'ok': True})
    except Exception as e:
        conn.rollback(); cur.close(); conn.close()
        return jsonify({'error': str(e)}), 500

# ─── EPIs ─────────────────────────────────────────────────────────────────────
from epis_routes import register_epis
register_epis(app, get_conn)

if __name__=='__main__':
    init_db()
    app.run(host='0.0.0.0',port=5000,debug=False)
