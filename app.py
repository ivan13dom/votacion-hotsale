from flask import Flask, request, redirect, render_template, Response
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

# Llamar la función para crear la tabla al iniciar
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
            # Conectar a la base de datos PostgreSQL
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

@app.route("/descargar")
def descargar():
    try:
        # Conectar a la base de datos PostgreSQL
        conn = psycopg2.connect(os.environ['DATABASE_URL'])
        cur = conn.cursor()
        cur.execute("SELECT timestamp, sucursal, respuesta FROM votos")
        rows = cur.fetchall()
        cur.close()
        conn.close()

        # Convertir los resultados a formato CSV
        csv_data = "timestamp,sucursal,respuesta\n"
        csv_data += "\n".join([",".join(map(str, row)) for row in rows])

        # Devolver el archivo CSV como respuesta
        return Response(
            csv_data,
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=resultados.csv"}
        )
    except Exception as e:
        return f"Error al obtener los datos: {e}", 500

if __name__ == "__main__":
    app.run(debug=True)
