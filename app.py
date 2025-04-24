from flask import Flask, request, redirect, render_template, Response
import psycopg2
import os
import csv
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

@app.route("/descargar")
def descargar():
    try:
        conn = psycopg2.connect(os.environ['DATABASE_URL'])
        cur = conn.cursor()
        cur.execute("SELECT * FROM votos")
        rows = cur.fetchall()
        conn.close()

        # Crear el archivo CSV en memoria
        output = []
        output.append(['id', 'timestamp', 'sucursal', 'respuesta'])  # Encabezado
        for row in rows:
            output.append([row[0], row[1], row[2], row[3]])

        # Convertir a CSV
        import io
        csv_output = io.StringIO()
        csv_writer = csv.writer(csv_output)
        csv_writer.writerows(output)
        csv_output.seek(0)

        return Response(
            csv_output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=resultados.csv"}
        )

    except Exception as e:
        return f"Error al acceder a los datos: {e}", 500

if __name__ == "__main__":
    # Usar el puerto que Render asigna, por defecto 10000
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
