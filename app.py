import streamlit as st
import sqlite3
from datetime import datetime
import json
import os
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Sistema de Pagos", layout="centered")

# =========================
# CONFIG GOOGLE SHEETS
# =========================
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]


creds_dict = json.loads(os.environ["GOOGLE_CREDS"])
creds = Credentials.from_service_account_info(creds_dict, scopes=scope)

client = gspread.authorize(creds)

sheet = client.open("Control_Pagos").sheet1

# =========================
# SQLITE
# =========================
conn = sqlite3.connect("pagos.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS pagos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha TEXT,
    descripcion TEXT,
    monto REAL,
    saldo REAL
)
""")
conn.commit()

# =========================
# CONFIG GENERAL
# =========================
MONTO_TOTAL = 20_000_000

st.title("💰 Sistema de Pagos - Control de Obra")

# =========================
# CALCULAR SALDO
# =========================
cursor.execute("SELECT SUM(monto) FROM pagos")
total_pagado = cursor.fetchone()[0] or 0
saldo_actual = MONTO_TOTAL - total_pagado

st.subheader("📊 Estado Actual")
st.write(f"💼 Monto pactado: $ {MONTO_TOTAL:,.0f}")
st.write(f"💸 Total pagado: $ {total_pagado:,.0f}")
st.write(f"✅ Saldo restante: $ {saldo_actual:,.0f}")

# =========================
# REGISTRAR PAGO
# =========================
st.subheader("➕ Registrar nuevo pago")

descripcion = st.text_input("Descripción (ej. Semana 1, Trabajo de muros)")
monto = st.number_input("Monto a pagar", min_value=0, step=10000)

if st.button("Registrar pago"):

    if monto <= 0:
        st.error("El monto debe ser mayor a cero")
    elif monto > saldo_actual:
        st.error("El monto supera el saldo restante")
    else:
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
        nuevo_saldo = saldo_actual - monto

        # Guardar en SQLite
        cursor.execute(
            "INSERT INTO pagos (fecha, descripcion, monto, saldo) VALUES (?, ?, ?, ?)",
            (fecha, descripcion, monto, nuevo_saldo)
        )
        conn.commit()

        # Guardar en Google Sheets (backup)
        sheet.append_row([fecha, descripcion, monto, nuevo_saldo])

        st.success("✅ Pago registrado y respaldado correctamente")

        recibo = f"""
RECIBO DE PAGO - CONSTRUCCION CARRERA 29 # 33 - 47 (Santa rita)

Fecha: {fecha}
Descripción: {descripcion}

Monto pagado: $ {monto:,.0f}
Saldo restante: $ {nuevo_saldo:,.0f}
"""

        st.download_button(
            "📄 Descargar recibo",
            recibo,
            file_name=f"recibo_{fecha.replace(':','-')}.txt"
        )

# =========================
# HISTORIAL
# =========================
st.subheader("📜 Historial")

cursor.execute("""
SELECT fecha, descripcion, monto, saldo, firmado
FROM pagos ORDER BY id DESC
""")

rows = cursor.fetchall()

if rows:
    for row in rows:
        st.write(
            f"📅 {row[0]} | {row[1]} | 💲 {row[2]:,.0f} | Saldo: $ {row[3]:,.0f} | {row[4]}"
        )
else:
    st.info("No hay pagos registrados")

