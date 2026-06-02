import streamlit as st
import sqlite3
from datetime import datetime
import json
import os
import gspread
from google.oauth2.service_account import Credentials
from streamlit_drawable_canvas import st_canvas
from PIL import Image, ImageDraw
import io

st.set_page_config(page_title="Sistema de Pagos", layout="centered")

# =========================
# GOOGLE SHEETS
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
    saldo REAL,
    firmado TEXT
)
""")
conn.commit()

# =========================
# CONFIG
# =========================
MONTO_TOTAL = 20_000_000

st.title("💰 Sistema de Pagos - Control de Obra")

# =========================
# CALCULO
# =========================
cursor.execute("SELECT SUM(monto) FROM pagos")
total_pagado = cursor.fetchone()[0] or 0
saldo_actual = MONTO_TOTAL - total_pagado

st.subheader("📊 Estado Actual")
st.write(f"💼 Monto pactado: $ {MONTO_TOTAL:,.0f}")
st.write(f"💸 Total pagado: $ {total_pagado:,.0f}")
st.write(f"✅ Saldo restante: $ {saldo_actual:,.0f}")

# =========================
# FORMULARIO
# =========================
st.subheader("➕ Registrar nuevo pago")

descripcion = st.text_input("Descripción (ej. Semana 1, Trabajo de muros)")
monto = st.number_input("Monto a pagar", min_value=0, step=10000)

# =========================
# FIRMA ✅
# =========================
st.subheader("✍️ Firma del constructor")

canvas_result = st_canvas(
    stroke_width=3,
    stroke_color="black",
    background_color="white",
    height=150,
    width=400,
    drawing_mode="freedraw",
)

# =========================
# REGISTRAR
# =========================
if st.button("Registrar pago"):

    if monto <= 0:
        st.error("El monto debe ser mayor a cero")

    elif monto > saldo_actual:
        st.error("El monto supera el saldo restante")

    elif canvas_result.image_data is None or canvas_result.image_data.sum() == 0:
        st.error("Debe firmar antes de registrar el pago")

    else:
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
        nuevo_saldo = saldo_actual - monto

        firma_texto = f"Firmado ✅ {fecha}"

        # ✅ SQLite
        cursor.execute(
            "INSERT INTO pagos (fecha, descripcion, monto, saldo, firmado) VALUES (?, ?, ?, ?, ?)",
            (fecha, descripcion, monto, nuevo_saldo, firma_texto)
        )
        conn.commit()

        # ✅ Google Sheets
        try:
            sheet.append_row([fecha, descripcion, monto, nuevo_saldo, firma_texto])
            st.success("✅ Guardado en Google Sheets")
        except Exception as e:
            st.error(f"Error en Sheets: {e}")

        st.success("✅ Pago registrado correctamente")

        # =========================
        # RECIBO IMAGEN ✅
        # =========================
        img = Image.new("RGB", (600, 400), "white")
        draw = ImageDraw.Draw(img)

        texto = f"""
RECIBO DE PAGO - CONSTRUCCION CARRERA 29 # 33 - 47 (Santa rita)

Fecha: {fecha}

Descripción:
{descripcion}

Monto: $ {monto:,.0f}

Saldo restante:
$ {nuevo_saldo:,.0f}

{firma_texto}
"""
        draw.text((20, 20), texto, fill="black")

        # insertar firma
        firma_img = Image.fromarray(canvas_result.image_data.astype("uint8"))
        firma_img = firma_img.resize((300, 100))
        img.paste(firma_img, (150, 250))

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")

        st.download_button(
            "📄 Descargar Recibo (Imagen)",
            buffer.getvalue(),
            file_name="recibo.png",
            mime="image/png"
        )

        st.image(img, caption="Vista previa del recibo")

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
