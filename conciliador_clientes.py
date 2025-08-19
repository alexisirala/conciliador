import streamlit as st
import pandas as pd
import io
import time

st.set_page_config(page_title="Conciliador de Clientes", page_icon="EGT", layout="centered")
st.title("EGT - Conciliador de Clientes")
st.write("Sube tu archivo de extracto bancario (Excel) y descarga el archivo conciliado.")

uploaded_file = st.file_uploader("Cargar extracto Excel", type=["xlsx"])

def procesar_excel(df):
    # Detectar columna de fecha
    col_fecha = [col for col in df.columns if str(col).strip().lower() == "fecha"]
    fecha_col = col_fecha[0] if col_fecha else df.columns[0]
    col_accion = [col for col in df.columns if str(col).strip().lower() == "accion"]
    accion_col = col_accion[0] if col_accion else df.columns[-1]

    df[fecha_col] = pd.to_datetime(df[fecha_col])
    if "saldo" not in df.columns or "haber" not in df.columns:
        st.error("El archivo debe tener las columnas 'saldo' y 'haber'.")
        return None

    df["Fecha Corte"] = None
    df["Saldo Corte"] = None
    df["Creditos/Haber despues Corte"] = None
    df["Monto a Pagar"] = None
    df["Diferencia Calculada"] = None
    df["Situaci贸n Pago"] = None

    saldo_encabezado = df.loc[0, "saldo"]
    fecha_encabezado = df.loc[0, fecha_col]
    pagos_idx = df[df[accion_col].astype(str).str.strip().str.lower() == "pago"].index
    total_pagos = len(pagos_idx)
    inicio = time.time()

    for i, idx in enumerate(pagos_idx, 1):
        row = df.loc[idx]
        fecha_pago = row[fecha_col]
        fecha_pago_date = fecha_pago.date()

        fechas_anteriores = df[df[fecha_col].dt.date < fecha_pago_date]
        if not fechas_anteriores.empty:
            fecha_corte_date = fechas_anteriores[fecha_col].dt.date.max()
            registros_corte = df[df[fecha_col].dt.date == fecha_corte_date]
            idx_corte = registros_corte[fecha_col].idxmax()
            fecha_corte = df.loc[idx_corte, fecha_col]
            saldo_corte = df.loc[idx_corte, "saldo"]
        else:
            saldo_corte = saldo_encabezado
            fecha_corte = fecha_encabezado

        creditos_despues_corte = df[
            (df[fecha_col] > fecha_corte) &
            (df[fecha_col] <= fecha_pago) &
            (df["haber"] < 0) &
            (df.index != idx)
        ]["haber"].sum()

        creditos_despues_corte_abs = abs(creditos_despues_corte)
        pago_realizado = abs(row["haber"])
        monto_a_pagar = saldo_corte - creditos_despues_corte_abs
        diferencia = pago_realizado - monto_a_pagar

        if pago_realizado > monto_a_pagar:
            situacion = "Dep贸sito mayor al monto a pagar (saldo a favor)"
        elif pago_realizado < monto_a_pagar:
            situacion = "Dep贸sito menor al monto a pagar (debe dinero)"
        else:
            situacion = "Dep贸sito igual al monto a pagar (saldo saldado)"

        df.at[idx, "Fecha Corte"] = fecha_corte
        df.at[idx, "Saldo Corte"] = saldo_corte
        df.at[idx, "Creditos/Haber despues Corte"] = creditos_despues_corte_abs
        df.at[idx, "Monto a Pagar"] = monto_a_pagar
        df.at[idx, "Diferencia Calculada"] = diferencia
        df.at[idx, "Situaci贸n Pago"] = situacion

    return df

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    conciliado = procesar_excel(df)
    if conciliado is not None:
        st.success("Archivo procesado correctamente.")
        st.dataframe(conciliado)
        # Para descargar el resultado
        output = io.BytesIO()
        conciliado.to_excel(output, index=False)
        output.seek(0)
        st.download_button("Descargar archivo conciliado", output, "extracto_conciliado.xlsx")

st.markdown("""
---
**Conciliador de Clientes** creado con 鉂わ笍 para facilitar la gesti贸n y el control de pagos.
""")
