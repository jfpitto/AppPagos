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

        img = Image.new("RGB", (750, 550), "white")
        draw = ImageDraw.Draw(img)

        draw.text((250, 20), "RECIBO DE PAGO", fill="black")
        draw.line((50, 60, 700, 60), fill="black", width=2)

        draw.text((50, 80), "Proyecto:", fill="black")
        draw.text((150, 80), "Construcción Carrera 29 # 33 - 47 – Santa Rita", fill="black")

        draw.text((50, 110), "Fecha:", fill="black")
        draw.text((150, 110), fecha.split(" ")[0], fill="black")

        draw.text((350, 110), "Hora:", fill="black")
        draw.text((420, 110), fecha.split(" ")[1], fill="black")

        draw.line((50, 140, 700, 140), fill="black")

        # ✅ NOMBRE FIJO
        draw.text((50, 160), "Recibí de:", fill="black")
        draw.text((150, 160), "Maria Elena Giraldo Gomez", fill="black")

        draw.text((50, 190), "Concepto:", fill="black")
        draw.text((150, 190), "Pago de mano de obra por actividades de construcción", fill="black")

        draw.line((50, 220, 700, 220), fill="black")

        draw.text((50, 240), "Detalle:", fill="black")
        draw.text((50, 260), descripcion, fill="black")

        draw.line((50, 300, 700, 300), fill="black")

        draw.text((50, 320), "Monto pagado:", fill="black")
        draw.text((250, 320), f"$ {monto:,.0f}", fill="black")

        draw.text((50, 350), "Saldo restante:", fill="black")
        draw.text((250, 350), f"$ {nuevo_saldo:,.0f}", fill="black")

        draw.line((50, 380, 700, 380), fill="black")

        # FIRMA
        draw.text((50, 400), "Firma del trabajador:", fill="black")

        firma_img = Image.fromarray(canvas_result.image_data.astype("uint8"))
        firma_img = firma_img.resize((300, 100))
        img.paste(firma_img, (200, 380))

        draw.line((200, 480, 500, 480), fill="black")

        draw.text((50, 500), "Constancia: El pago fue recibido a satisfacción.", fill="black")

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
