from flask import request, jsonify
import psycopg2
import psycopg2.extras

def register_epis(app, get_conn):

    # ─── TRABAJADORES ─────────────────────────────────────────────────────────
    # (estas rutas están también en api.py con upsert por batch,
    #  aquí mantenemos compatibilidad con POST individual)

    @app.route('/api/trabajadores', methods=['POST'])
    def save_trabajador():
        data = request.json
        conn = get_conn(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            INSERT INTO trabajadores (dni, nombre, departamento)
            VALUES (%s, %s, %s)
            ON CONFLICT (dni) DO UPDATE
              SET nombre=EXCLUDED.nombre,
                  departamento=EXCLUDED.departamento
            RETURNING *
        """, (data['dni'], data['nombre'], data.get('departamento', '')))
        row = cur.fetchone(); conn.commit(); cur.close(); conn.close()
        return jsonify(dict(row)), 201

    # ─── EPIS ─────────────────────────────────────────────────────────────────

    @app.route('/api/epis', methods=['GET'])
    def get_epis():
        """
        Devuelve las EPIs agrupadas por DNI en formato:
        { "12345678A": [{tipo, talla, nota, estado, fecha}, ...], ... }
        Este formato lo espera panel_epi.html
        """
        conn = get_conn(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM epis ORDER BY fecha DESC")
        rows = cur.fetchall(); cur.close(); conn.close()

        # Agrupar por DNI
        resultado = {}
        for row in rows:
            d = dict(row)
            dni = d.pop('dni')
            if dni not in resultado:
                resultado[dni] = []
            resultado[dni].append(d)
        return jsonify(resultado)

    @app.route('/api/epis', methods=['POST'])
    def save_epi():
        """Crear una nueva solicitud de EPI"""
        data = request.json
        conn = get_conn(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            INSERT INTO epis (dni, tipo, talla, nota, estado, fecha)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING *
        """, (
            data['dni'],
            data['tipo'],
            data.get('talla', ''),
            data.get('nota', ''),
            data.get('estado', 'pendiente'),
            data.get('fecha')
        ))
        row = cur.fetchone(); conn.commit(); cur.close(); conn.close()
        return jsonify(dict(row)), 201

    @app.route('/api/epis/estado', methods=['POST'])
    def update_epi_estado():
        """
        Cambia el estado de una solicitud concreta.
        Body: { dni: "12345678A", idx: 0, estado: "aprobado" }
        El idx es la posición en el array de EPIs de ese DNI (ordenado por fecha DESC).
        """
        data = request.json
        dni   = data.get('dni')
        idx   = data.get('idx')
        estado = data.get('estado')

        if dni is None or idx is None or not estado:
            return jsonify({'error': 'Faltan campos'}), 400

        conn = get_conn(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            # Obtener todas las EPIs de ese DNI ordenadas igual que en el GET
            cur.execute("SELECT id FROM epis WHERE dni=%s ORDER BY fecha DESC", (dni,))
            rows = cur.fetchall()
            if idx >= len(rows):
                return jsonify({'error': 'Índice fuera de rango'}), 404
            eid = rows[idx]['id']
            cur.execute("UPDATE epis SET estado=%s WHERE id=%s RETURNING *", (estado, eid))
            row = cur.fetchone(); conn.commit()
            cur.close(); conn.close()
            return jsonify(dict(row))
        except Exception as e:
            conn.rollback(); cur.close(); conn.close()
            return jsonify({'error': str(e)}), 500

    @app.route('/api/epis/<string:dni>/<int:idx>', methods=['DELETE'])
    def delete_epi(dni, idx):
        """
        Elimina una solicitud concreta.
        El idx es la posición en el array de EPIs de ese DNI (ordenado por fecha DESC).
        """
        conn = get_conn(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cur.execute("SELECT id FROM epis WHERE dni=%s ORDER BY fecha DESC", (dni,))
            rows = cur.fetchall()
            if idx >= len(rows):
                return jsonify({'error': 'Índice fuera de rango'}), 404
            eid = rows[idx]['id']
            cur.execute("DELETE FROM epis WHERE id=%s", (eid,))
            conn.commit(); cur.close(); conn.close()
            return jsonify({'ok': True})
        except Exception as e:
            conn.rollback(); cur.close(); conn.close()
            return jsonify({'error': str(e)}), 500

    @app.route('/api/epis/<int:eid>', methods=['PUT'])
    def update_epi(eid):
        """Actualizar EPI por ID (compatibilidad con recepcion_epi)"""
        data = request.json
        conn = get_conn(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            UPDATE epis
            SET estado=%s, firma=%s, fecha_entrega=%s, entregado_por=%s
            WHERE id=%s RETURNING *
        """, (
            data['estado'],
            data.get('firma'),
            data.get('fechaEntrega'),
            data.get('entregadoPor'),
            eid
        ))
        row = cur.fetchone(); conn.commit(); cur.close(); conn.close()
        return jsonify(dict(row)) if row else (jsonify({'ok': False}), 404)
