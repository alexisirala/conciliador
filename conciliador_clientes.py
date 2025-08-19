import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Conciliador de Clientes", page_icon="EGT", layout="centered")
st.title("EGT - Conciliador de Clientes")
st.write("Sube tu archivo de extracto bancario (Excel .xls o .xlsx) y descarga el archivo conciliado.")

uploaded_file = st.file_uploader("Cargar extracto Excel", type=["xls", "xlsx"])

def limpiar_col(col):
    return str(col).strip().lower().replace(" ", "")

def marcar_pagos(df, concepto_col):
    df["Es Pago"] = df[concepto_col].astype(str).str.strip().str.lower().apply(
        lambda x: x.startswith("boleta depósito") or x.startswith("pago desde terminal eglobalt")
    )
    return df

def procesar_excel(df):
    columnas_limpias = {col: limpiar_col(col) for col in df.columns}
    df = df.rename(columns=columnas_limpias)
    fecha_col = next((col for col in df.columns if "fecha" in col), df.columns[0])
    concepto_col = next((col for col in df.columns if "concepto" in col), None)
    if not concepto_col:
        st.error("El archivo debe tener la columna 'Concepto'.")
        return None
    if "saldo" not in df.columns or "haber" not in df.columns:
        st.error("El archivo debe tener las columnas 'saldo' y 'haber'.")
        return None
    df[fecha_col] = pd.to_datetime(df[fecha_col])
    df = marcar_pagos(df, concepto_col)
    df["Fecha Corte"] = None
    df["Saldo Corte"] = None
    df["Creditos/Haber despues Corte"] = None
    df["Monto a Pagar"] = None
    df["Diferencia Calculada"] = None
    df["Situacion Pago"] = None
    df["Es Corte"] = False
    df["Estado"] = ""
    saldo_encabezado = df.loc[0, "saldo"]
    fecha_encabezado = df.loc[0, fecha_col]
    pagos_idx = df[df["Es Pago"]].index
    for idx in pagos_idx:
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
            df.at[idx_corte, "Es Corte"] = True
            df.at[idx_corte, "Estado"] = "🚩 Corte"
        else:
            saldo_corte = saldo_encabezado
            fecha_corte = fecha_encabezado
            df.at[0, "Es Corte"] = True
            df.at[0, "Estado"] = "🚩 Corte"
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
            situacion = "Deposito mayor al monto a pagar (saldo a favor)"
            df.at[idx, "Estado"] = "✅ Sobrante"
        elif pago_realizado < monto_a_pagar:
            situacion = "Deposito menor al monto a pagar (debe dinero)"
            df.at[idx, "Estado"] = "⚠️ Faltante"
        else:
            situacion = "Deposito igual al monto a pagar (saldo cero)"
            df.at[idx, "Estado"] = "🔵 Saldado"
        df.at[idx, "Fecha Corte"] = fecha_corte
        df.at[idx, "Saldo Corte"] = saldo_corte
        df.at[idx, "Creditos/Haber despues Corte"] = creditos_despues_corte_abs
        df.at[idx, "Monto a Pagar"] = monto_a_pagar
        df.at[idx, "Diferencia Calculada"] = diferencia
        df.at[idx, "Situacion Pago"] = situacion
    return df

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
    except Exception as e:
        st.error("No se pudo abrir el archivo. Verifica que sea un Excel válido (.xls o .xlsx) guardado desde Excel. Error: %s" % str(e))
        df = None
    if df is not None:
        conciliado = procesar_excel(df)
        if conciliado is not None:
            st.success("Archivo procesado correctamente.")
            st.dataframe(conciliado, use_container_width=True)
            output = io.BytesIO()
            conciliado.to_excel(output, index=False)
            output.seek(0)
            st.download_button("Descargar archivo conciliado", output, "extracto_conciliado.xlsx")

st.markdown("""
---
**Conciliador de Clientes** para facilitar la gestión y el control de pagos.
""")