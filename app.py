
from flask import Flask, request, redirect, render_template
import csv
import os
from datetime import datetime

app = Flask(__name__)

CSV_FILE = "respuestas.csv"

@app.route("/")
def home():
    return "Servidor activo"

@app.route("/voto")
def voto():
    sucursal = request.args.get("sucursal")
    respuesta = request.args.get("respuesta")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if sucursal and respuesta:
        with open(CSV_FILE, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([timestamp, sucursal, respuesta])
        return redirect("/gracias")
    else:
        return "Datos incompletos", 400

@app.route("/gracias")
def gracias():
    return render_template("gracias.html")
