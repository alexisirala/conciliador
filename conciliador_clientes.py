import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Conciliador de Clientes", page_icon="EGT", layout="centered")
st.title("EGT - Conciliador de Clientes")
st.write("Sube tu archivo de extracto bancario (Excel) y descarga el archivo conciliado.")

uploaded_file = st.file_uploader("Cargar extracto Excel", type=["xlsx"])

def limpiar_col(col):
    # Limpia espacios y minusculas
    return str(col).strip().lower().replace(" ", "")

def procesar_excel(df):
    # Renombrar columnas limpias para evitar errores de espacios
    columnas_limpias = {col: limpiar_col(col) for col in df.columns}
    df = df.rename(columns=columnas_limpias)
    
    # Detectar columna de fecha y accion
    fecha_col = next((col for col in df.columns if "fecha" in col), df.columns[0])
    accion_col = next((col for col in df.columns if "accion" in col), df.columns[-1])

    # Verifica columnas obligatorias
    if "saldo" not in df.columns or "haber" not in df.columns:
        st.error("El archivo debe tener las columnas 'saldo' y 'haber'.")
        return None

    df[fecha_col] = pd.to_datetime(df[fecha_col])
    df["Fecha Corte"] = None
    df["Saldo Corte"] = None
    df["Creditos/Haber despues Corte"] = None
    df["Monto a Pagar"] = None
    df["Diferencia Calculada"] = None
    df["Situacion Pago"] = None
    df["Es Corte"] = False  # Nueva columna para marcar la fila del corte

    saldo_encabezado = df.loc[0, "saldo"]
    fecha_encabezado = df.loc[0, fecha_col]
    pagos_idx = df[df[accion_col].astype(str).str.strip().str.lower() == "pago"].index

    for idx in pagos_idx:
        row = df.loc[idx]
        fecha_pago = row[fecha_col]
        fecha_pago_date = fecha_pago.date()

        fechas_anteriores = df[df[fecha_col].dt.date < fecha_pago_date]
        if not fechas_anteriores.empty:
            fecha_corte_date = fechas_anteriores[fecha_col].dt.date.max()
            registros_corte = df[df[fecha_col].dt.date == fecha_corte_date]
            # Busca el idx de la fila corte
            idx_corte = registros_corte[fecha_col].idxmax()
            fecha_corte = df.loc[idx_corte, fecha_col]
            saldo_corte = df.loc[idx_corte, "saldo"]
            # Marca la fila corte
            df.at[idx_corte, "Es Corte"] = True
        else:
            saldo_corte = saldo_encabezado
            fecha_corte = fecha_encabezado
            df.at[0, "Es Corte"] = True  # La primera fila como corte si no hay anteriores

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
        elif pago_realizado < monto_a_pagar:
            situacion = "Deposito menor al monto a pagar (debe dinero)"
        else:
            situacion = "Deposito igual al monto a pagar (saldo saldado)"

        df.at[idx, "Fecha Corte"] = fecha_corte
        df.at[idx, "Saldo Corte"] = saldo_corte
        df.at[idx, "Creditos/Haber despues Corte"] = creditos_despues_corte_abs
        df.at[idx, "Monto a Pagar"] = monto_a_pagar
        df.at[idx, "Diferencia Calculada"] = diferencia
        df.at[idx, "Situacion Pago"] = situacion

    # Ordena la columna Es Corte para que aparezca primero si quieres
    cols = list(df.columns)
    if "Es Corte" in cols:
        cols.insert(0, cols.pop(cols.index("Es Corte")))
        df = df[cols]

    return df

def color_situacion(val):
    # Colorea la columna según la situación de pago
    if isinstance(val, str):
        if "mayor" in val:
            return "background-color: #d4f4dd"  # verde claro
        elif "menor" in val:
            return "background-color: #ffd1d1"  # rojo claro
        elif "igual" in val:
            return "background-color: #e6e6ff"  # azul claro
    return ""

def color_corte(row):
    # Colorea la fila del corte
    if row["Es Corte"]:
        return ["background-color: #fff3cd"] * len(row)  # amarillo claro
    return [""] * len(row)

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    conciliado = procesar_excel(df)
    if conciliado is not None:
        st.success("Archivo procesado correctamente.")
        # Visualización coloreando situación y corte
        df_styled = conciliado.style.applymap(color_situacion, subset=["Situacion Pago"])
        df_styled = df_styled.apply(color_corte, axis=1)
        st.write("Tabla conciliada:")
        st.write(df_styled)
        # Para descargar el resultado
        output = io.BytesIO()
        conciliado.to_excel(output, index=False)
        output.seek(0)
        st.download_button("Descargar archivo conciliado", output, "extracto_conciliado.xlsx")

st.markdown("""
---
**Conciliador de Clientes** para facilitar la gestión y el control de pagos.
""")