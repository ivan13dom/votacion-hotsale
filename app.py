from flask import Flask, request, render_template, redirect
import psycopg2
import os
from datetime import datetime

app = Flask(__name__)

def crear_tabla():
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    cur = conn.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS votos (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP,
            sucursal TEXT,
            respuesta TEXT,
            envio TEXT,
            ip TEXT
        )
    ''')

    conn.commit()
    cur.close()
    conn.close()

@app.route("/voto")
def voto():
    raw_query = request.query_string.decode()
    if ";" in raw_query and "&" not in raw_query:
        params = parse_qs(raw_query.replace(";", "&"))
        sucursal = params.get("sucursal", [None])[0]
        respuesta = params.get("respuesta", [None])[0]
        envio = params.get("envio", [None])[0]
    else:
        sucursal = request.args.get("sucursal")
        respuesta = request.args.get("respuesta")
        envio = request.args.get("envio")

    # Validar parámetros requeridos
    if not sucursal or not respuesta or not envio:
        return "Faltan parámetros", 400

    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    cur = conn.cursor()

    # Verificar si ya existe un voto con el mismo número de envío
    cur.execute("SELECT 1 FROM votos WHERE envio = %s", (envio,))
    if cur.fetchone():
        cur.close()
        conn.close()
        return render_template('ya_voto.html')

    # Insertar nuevo voto
    cur.execute('''
        INSERT INTO votos (timestamp, sucursal, respuesta, envio, ip)
        VALUES (%s, %s, %s, %s, %s)
    ''', (datetime.now(), sucursal, respuesta, envio, ip))

    conn.commit()
    cur.close()
    conn.close()

    return redirect('/gracias')

@app.route('/gracias')
def gracias():
    return render_template('gracias.html')

@app.route('/dashboard')
def dashboard():
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    cur = conn.cursor()

    cur.execute('SELECT timestamp, sucursal, respuesta, envio, ip FROM votos ORDER BY timestamp DESC')
    votos = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('dashboard.html', votos=votos)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)



