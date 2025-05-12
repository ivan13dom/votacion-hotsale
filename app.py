from flask import Flask, request, redirect, render_template, Response
import psycopg2
import os
import csv
from datetime import datetime
from urllib.parse import parse_qs
from zoneinfo import ZoneInfo  # estándar desde Python 3.9
from collections import Counter, defaultdict


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

crear_tabla()

@app.route("/")
def home():
    return "Servidor activo"

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

    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ip:
        ip = ip.split(',')[0].strip()

    # Zona horaria Argentina
    timestamp = datetime.now(ZoneInfo("America/Argentina/Buenos_Aires"))

    if sucursal and respuesta and envio:
        try:
            conn = psycopg2.connect(os.environ['DATABASE_URL'])
            cur = conn.cursor()
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

        output = [['id', 'timestamp', 'sucursal', 'respuesta', 'envio', 'ip']]
        for row in rows:
            timestamp = row[1]
            formatted_timestamp = timestamp.strftime("%d/%m/%Y %H:%M:%S") if timestamp else ""
            output.append([row[0], formatted_timestamp, row[2], row[3], row[4], row[5]])

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

@app.route("/dashboard")
def dashboard():
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    cur = conn.cursor()
    cur.execute("SELECT sucursal, respuesta, envio, timestamp FROM votos")
    votos = cur.fetchall()
    cur.close()
    conn.close()

    votos_unicos = {}
    for sucursal, respuesta, envio, timestamp in votos:
        if envio not in votos_unicos:
            votos_unicos[envio] = (sucursal, respuesta, timestamp)

    positivos_por_sucursal = Counter()
    totales_por_sucursal = Counter()
    votos_por_dia = defaultdict(int)

    for sucursal, respuesta, timestamp in votos_unicos.values():
        totales_por_sucursal[sucursal] += 1
        if respuesta.lower() in ["si", "sí"]:
            positivos_por_sucursal[sucursal] += 1
        fecha = timestamp.date()
        votos_por_dia[fecha] += 1

    top_10 = positivos_por_sucursal.most_common(10)

    porcentajes = []
    for sucursal in totales_por_sucursal:
        total = totales_por_sucursal[sucursal]
        positivos = positivos_por_sucursal[sucursal]
        porcentaje = round((positivos / total) * 100, 2)
        porcentajes.append((sucursal, porcentaje))
    top_5_porcentaje = sorted(porcentajes, key=lambda x: x[1], reverse=True)[:5]

    votos_dia = sorted(votos_por_dia.items())

    return render_template("dashboard.html", top_10=top_10, top_5=top_5_porcentaje, votos_dia=votos_dia)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)