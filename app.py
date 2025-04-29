from flask import Flask, request, redirect, render_template, Response
import psycopg2
import os
import csv
from datetime import datetime
import io

app = Flask(__name__)

# Crear la tabla si no existe al iniciar
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

crear_tabla()

@app.route("/")
def home():
    return "Servidor activo"

@app.route("/voto")
def voto():
    sucursal = request.args.get("sucursal")
    respuesta = request.args.get("respuesta")
    envio = request.args.get("envio")
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ip:
        ip = ip.split(',')[0].strip()
    timestamp = datetime.now()

    if not (sucursal and respuesta and envio):
        return "Datos incompletos", 400

    try:
        conn = psycopg2.connect(os.environ['DATABASE_URL'])
        cur = conn.cursor()

        # Guardar el voto
        cur.execute(
            "INSERT INTO votos (timestamp, sucursal, respuesta, envio, ip) VALUES (%s, %s, %s, %s, %s)",
            (timestamp, sucursal, respuesta, envio, ip)
        )
        conn.commit()
        cur.close()
        conn.close()
        return redirect("/gracias")

    except Exception as e:
        return f"Error al guardar en la base de datos: {e}", 500

@app.route("/gracias")
def gracias():
    return render_template("gracias.html")

@app.route("/descargar")
def descargar():
    try:
        conn = psycopg2.connect(os.environ['DATABASE_URL'])
        cur = conn.cursor()
        cur.execute("SELECT * FROM votos")
        rows = cur.fetchall()
        cur.close()
        conn.close()

        # Crear archivo CSV en memoria
        output = io.StringIO()
        csv_writer = csv.writer(output)
        csv_writer.writerow(['id', 'timestamp', 'sucursal', 'respuesta', 'envio', 'ip'])
        csv_writer.writerows(rows)
        output.seek(0)

        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=resultados.csv"}
        )

    except Exception as e:
        return f"Error al acceder a los datos: {e}", 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
