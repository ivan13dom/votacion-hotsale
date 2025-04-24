from flask import Flask, request, redirect, render_template
import psycopg2
import os
from datetime import datetime

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
            respuesta TEXT
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
    timestamp = datetime.now()

    if sucursal and respuesta:
        try:
            conn = psycopg2.connect(os.environ['DATABASE_URL'])
            cur = conn.cursor()
            cur.execute("INSERT INTO votos (timestamp, sucursal, respuesta) VALUES (%s, %s, %s)", (timestamp, sucursal, respuesta))
            conn.commit()
            cur.close()
            conn.close()
            return redirect("/gracias")
        except Exception as e:
            return f"Error al guardar en la base de datos: {e}", 500
    else:
        return "Datos incompletos", 400

@app.route("/gracias")
def gracias():
    return render_template("gracias.html")
from flask import Response

@app.route("/descargar")
def descargar():
    if not os.path.exists(CSV_FILE):
        return "No hay datos todavía", 404

    with open(CSV_FILE, encoding='utf-8') as f:
        csv_data = f.read()

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=resultados.csv"}
    )
