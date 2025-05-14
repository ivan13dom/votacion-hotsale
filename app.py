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


# Lista de user agents típicos de bots o servicios de previsualización
BOTS_SOSPECHOSOS = [
    "bot", "crawler", "spider", "preview", "facebookexternalhit", "whatsapp",
    "telegrambot", "slackbot", "twitterbot", "linkedinbot", "embedly",
    "quora link preview", "pinterest", "discordbot", "vkshare", "skypeuripreview",
    "nuzzel", "outlook", "microsoft office", "applemail", "thunderbird",
    "googleimageproxy", "gmailimageproxy", "gmail", "outlook", "yahoo"
]

@app.route("/voto")
def voto():
    user_agent = request.headers.get("User-Agent", "").lower()

    # ⚠️ Si el User-Agent es sospechoso, ignorar la solicitud (no cuenta el voto)
    if any(bot in user_agent for bot in BOTS_SOSPECHOSOS):
        print(f"[IGNORADO] User-Agent sospechoso: {user_agent}")
        return "", 204  # No Content

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

    timestamp = datetime.now(ZoneInfo("America/Argentina/Buenos_Aires"))

    if sucursal and respuesta and envio:
        try:
            conn = psycopg2.connect(os.environ['DATABASE_URL'])
            cur = conn.cursor()

            # ✅ Verificar si ya existe un voto con el mismo envío e IP
            cur.execute("SELECT 1 FROM votos WHERE envio = %s AND ip = %s LIMIT 1", (envio, ip))
            voto_existente = cur.fetchone()

            if voto_existente:
                cur.close()
                conn.close()
                return render_template("ya_voto.html")

            # ✅ Registrar el nuevo voto
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
    votos_por_dia = defaultdict(int)
    ultimos_votos = []

    for envio, (sucursal, respuesta, timestamp) in votos_unicos.items():
        if respuesta.strip().lower() == "positivo":

            positivos_por_sucursal[sucursal] += 1
        fecha = timestamp.date()
        votos_por_dia[fecha] += 1
        ultimos_votos.append((envio, timestamp, sucursal, respuesta))

    votos_dia = sorted(votos_por_dia.items())
    ultimos_votos = sorted(ultimos_votos, key=lambda x: x[1], reverse=True)[:100]

    # Datos para el gráfico de votos por día
    labels = [fecha.strftime("%Y-%m-%d") for fecha, _ in votos_dia]
    data = [cantidad for _, cantidad in votos_dia]

   # Ordenar por cantidad de votos positivos (de mayor a menor)
    top_positivos = sorted(positivos_por_sucursal.items(), key=lambda x: x[1], reverse=True)

    return render_template("dashboard.html",
                       top_positivos=top_positivos,
                       votos_dia=votos_dia,
                       ultimos_votos=ultimos_votos,
                       labels=labels,
                       data=data)



if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
