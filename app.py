from flask import Flask, request, redirect, render_template, Response
import psycopg2
import os
import csv
from datetime import datetime
from urllib.parse import parse_qs
from zoneinfo import ZoneInfo
from collections import Counter, defaultdict
import logging

app = Flask(__name__)

# Configuración del logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Crear tablas

def crear_tablas():
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS votos (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP,
            sucursal TEXT,
            respuesta TEXT,
            envio TEXT,
            ip TEXT,
            comentario TEXT
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS intentos (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMPTZ,
            sucursal TEXT,
            respuesta TEXT,
            envio TEXT,
            ip TEXT,
            motivo TEXT
        )
    ''')
    conn.commit()
    cur.close()
    conn.close()

crear_tablas()

@app.route("/")
def home():
    return "Servidor activo"

BOTS_SOSPECHOSOS = [
    # General bots
    "bot", "spider", "crawl", "crawler", "index", "scrapy",
    
    # Email clients que previsualizan
    "applemail", "thunderbird", "gmail", "outlook", "windowslive", "emailpreview",

    # Proxys de previsualización
    "googleimageproxy", "gmailimageproxy", "fetcher", "python-requests", "axios", "curl", "httpclient",

    # Redes sociales y apps de mensajería
    "facebookexternalhit", "facebot", "whatsapp", "telegrambot", "discordbot",
    "slackbot", "linkedinbot", "twitterbot", "pinterest", "vkshare", "skypeuripreview",
    "nuzzel", "embedly", "quora link preview",

    # Web scrapers o rastreadores comunes
    "headless", "phantomjs", "selenium", "puppeteer", "java", "go-http-client", "aiohttp",

    # Otras apps automatizadas
    "okhttp", "libwww", "w3c_validator", "preview", "feedfetcher", "postman", "insomnia"
]


@app.route("/voto")
def voto():
    user_agent = request.headers.get("User-Agent", "").lower()
    referer = request.headers.get("Referer", "N/A")
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ip:
        ip = ip.split(',')[0].strip()

    es_bot = any(bot in user_agent for bot in BOTS_SOSPECHOSOS)
    if es_bot:
        logging.info(f"[BLOQUEADO] Bot detectado. Voto descartado. IP={ip} Envio={envio}")
        return render_template("ya_voto.html")  # o una página de error más neutral

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

    logging.info(f"[INTENTO] IP={ip} BOT={es_bot} UA='{user_agent}' Referer='{referer}' Envio='{envio}' Sucursal='{sucursal}' Respuesta='{respuesta}'")

    timestamp = datetime.now(ZoneInfo("America/Argentina/Buenos_Aires"))

    if sucursal and respuesta and envio:
        try:
            conn = psycopg2.connect(os.environ['DATABASE_URL'])
            cur = conn.cursor()

            # Verificar IP+envío
            cur.execute("SELECT 1 FROM votos WHERE envio = %s AND ip = %s LIMIT 1", (envio, ip))
            if cur.fetchone():
                cur.execute("INSERT INTO intentos (timestamp, sucursal, respuesta, envio, ip, motivo) VALUES (%s, %s, %s, %s, %s, %s)",
                            (timestamp, sucursal, respuesta, envio, ip, "duplicado_envio_ip"))
                conn.commit()
                cur.close()
                conn.close()
                return render_template("ya_voto.html")

            # Verificar múltiples votos simultáneos
            cur.execute("""
                SELECT COUNT(*) FROM votos 
                WHERE envio = %s AND timestamp > NOW() - INTERVAL '1 second'
            """, (envio,))
            if cur.fetchone()[0] > 0:
                cur.execute("INSERT INTO intentos (timestamp, sucursal, respuesta, envio, ip, motivo) VALUES (%s, %s, %s, %s, %s, %s)",
                            (timestamp, sucursal, respuesta, envio, ip, "ventana_1s"))
                conn.commit()
                cur.close()
                conn.close()
                return render_template("ya_voto.html")

            # Registrar voto válido
            cur.execute("INSERT INTO votos (timestamp, sucursal, respuesta, envio, ip) VALUES (%s, %s, %s, %s, %s)",
                        (timestamp, sucursal, respuesta, envio, ip))
            conn.commit()
            cur.close()
            conn.close()
            return redirect(f"/gracias?envio={envio}&ip={ip}")

        except Exception as e:
            return f"Error al guardar en la base de datos: {e}", 500
    else:
        return "Datos incompletos", 400

@app.route("/gracias")
def gracias():
    envio = request.args.get("envio")
    ip = request.args.get("ip")
    return render_template("gracias.html", envio=envio, ip=ip)

@app.route("/comentario", methods=["POST"])
def comentario():
    comentario = request.form.get("comentario")
    envio = request.form.get("envio")
    ip = request.form.get("ip")

    if envio and ip:
        try:
            conn = psycopg2.connect(os.environ['DATABASE_URL'])
            cur = conn.cursor()
            cur.execute("UPDATE votos SET comentario = %s WHERE envio = %s AND ip = %s",
                        (comentario, envio, ip))
            conn.commit()
            cur.close()
            conn.close()
            return "¡Gracias por tu comentario!"
        except Exception as e:
            return f"Error al guardar el comentario: {e}", 500
    else:
        return "Datos incompletos", 400

@app.route("/descargar")
def descargar():
    try:
        conn = psycopg2.connect(os.environ['DATABASE_URL'])
        cur = conn.cursor()
        cur.execute("SELECT * FROM votos")
        rows = cur.fetchall()
        conn.close()

        output = [['id', 'timestamp', 'sucursal', 'respuesta', 'envio', 'ip', 'comentario']]
        for row in rows:
            ts = row[1]
            if isinstance(ts, datetime):
                formatted_ts = ts.strftime("%d/%m/%Y %H:%M:%S")
            elif isinstance(ts, str):
                try:
                    parsed = datetime.fromisoformat(ts)
                    formatted_ts = parsed.strftime("%d/%m/%Y %H:%M:%S")
                except ValueError:
                    formatted_ts = ts
            else:
                formatted_ts = ""
            output.append([row[0], formatted_ts, row[2], row[3], row[4], row[5], row[6]])

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

    labels = [fecha.strftime("%Y-%m-%d") for fecha, _ in votos_dia]
    data = [cantidad for _, cantidad in votos_dia]

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
