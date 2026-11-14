import streamlit as st
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import re
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Directorio | Franco Marroquín",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- SEGURIDAD DE ACCESO (PIN) ---
def verificar_acceso():
    pin_configurado = st.secrets.get("APP_PIN", "")
    if not pin_configurado:
        return True
    if st.session_state.get("autenticado"):
        return True

    st.title("🔒 Acceso al Directorio Ejecutivo")
    pin_ingresado = st.text_input("Ingresa tu PIN de seguridad:", type="password")
    if st.button("Entrar", use_container_width=True):
        if pin_ingresado == str(pin_configurado):
            st.session_state.autenticado = True
            st.rerun()
        else:
            st.error("PIN incorrecto.")
    return False

if not verificar_acceso():
    st.stop()

# --- CONEXIÓN A GOOGLE SHEETS ---
@st.cache_resource
def conectar_sheets():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    cliente = gspread.authorize(creds)
    return cliente.open("Directorio_Franco_DB")

try:
    hoja_calculo = conectar_sheets()
    ws_estado = hoja_calculo.worksheet("estado_maestro")
    ws_historial = hoja_calculo.worksheet("historial")
    ws_finanzas = hoja_calculo.worksheet("finanzas")
except Exception as e:
    st.error(f"Error conectando con Google Sheets. Revisa tus Secrets y permisos: {e}")
    st.stop()

# --- FUNCIONES DE BASE DE DATOS EN LA NUBE ---
def obtener_estado_maestro():
    registros = ws_estado.get_all_values()
    if len(registros) < 2:
        estado_inicial = """**ESTADO MAESTRO - FRANCO MARROQUÍN**
- Ubicación: Puente Alto, Santiago, Chile.
- Trabajo (99minutos): Operación normal | franco.marroquin@99minutos.com | +569330386
- Instituto (Santo Tomás): Proyecto de título y defensa próxima | francoalexander.marroquin@alumnos.santotomas.cl
- Personal: marro.ccb@gmail.com | +56929669265
- Foco Actual: Redactar proyecto de título, desarrollar aplicación funcional y ordenar finanzas."""
        ahora = datetime.now().strftime("%Y-%m-%d %H:%M")
        ws_estado.append_row([estado_inicial, ahora])
        return estado_inicial, ahora
    return registros[1][0], registros[1][1]

def guardar_estado_maestro(nuevo_contenido):
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M")
    ws_estado.update("A2:B2", [[nuevo_contenido, ahora]])

def obtener_mensajes(agente):
    registros = ws_historial.get_all_records()
    return [
        {"role": r["rol"], "content": r["contenido"], "time": str(r["timestamp"])}
        for r in registros if r["agente"] == agente
    ]

def guardar_mensaje(agente, rol, contenido):
    ahora = datetime.now().strftime("%d/%m %H:%M")
    ws_historial.append_row([agente, rol, contenido, ahora])

def limpiar_historial_agente(agente):
    registros = ws_historial.get_all_values()
    encabezado = registros[0]
    filtrados = [fila for fila in registros[1:] if fila[0] != agente]
    ws_historial.clear()
    ws_historial.append_row(encabezado)
    if filtrados:
        ws_historial.append_rows(filtrados)

def agregar_movimiento_financiero(tipo, categoria, descripcion, monto):
    fecha = datetime.now().strftime("%Y-%m-%d")
    ws_finanzas.append_row([fecha, tipo, categoria, descripcion, int(monto)])

def obtener_finanzas_df():
    registros = ws_finanzas.get_all_records()
    if not registros:
        return pd.DataFrame()
    df = pd.DataFrame(registros)
    df["monto"] = pd.to_numeric(df["monto"], errors="coerce").fillna(0)
    return df.iloc[::-1]

# --- PROMPTS DE LOS 7 AGENTES ---
REGLA_GOBERNANZA = """
REGLAS DE GOBERNANZA Y SINCRONIZACIÓN AUTOMÁTICA:
1. NUNCA cambies planes aprobados, presupuestos, arquitectura, capítulos ni rutinas sin emitir primero esta alerta:
   "⚠️ PROPUESTA DE MODIFICACIÓN: [Qué deseas cambiar] | MOTIVO: [Justificación] | IMPACTO EN OTROS AGENTES: [A quiénes afecta]. ¿Apruebas?"
2. Cuando se cierre un acuerdo, decisión o avance relevante, incluye al final de tu respuesta exactamente estas etiquetas con el nuevo resumen global actualizado (manteniendo los datos vigentes y sumando lo nuevo):
   [ESTADO_MAESTRO_INICIO]
   (Aquí va el texto completo y actualizado del Estado Maestro)
   [ESTADO_MAESTRO_FIN]
"""

AGENTES = {
    "1. Jefe de Gabinete (COO)": f"""ROL: Jefe de Gabinete (COO) de Franco Alexander Marroquín. Ingeniero experto en gestión operativa, logística, comercio exterior, contabilidad y productividad.
CONTEXTO: Santiago, Chile. Trabajo: 99minutos (franco.marroquin@99minutos.com | +569330386). Estudios: Santo Tomás (francoalexander.marroquin@alumnos.santotomas.cl). Personal: marro.ccb@gmail.com | +56929669265.
TAREA: Gestionar agenda diaria/semanal, equilibrar trabajo, tesis, app, finanzas, legal y salud. Delegar tareas al directorio y evitar el agotamiento.
{REGLA_GOBERNANZA}""",

    "2. Director Académico (I+D)": f"""ROL: Director Académico y Gerente de I+D de Franco Marroquín. Ingeniero senior experto en Logística, Comercio Exterior, Contabilidad, Metodología de Investigación y Redacción Técnica (normas APA).
CONTEXTO: Proyecto de título y próxima defensa en Instituto Santo Tomás (francoalexander.marroquin@alumnos.santotomas.cl). Sincronizado con el CTO (app) y Estratega Corporativo.
TAREA: Redactar capítulos de tesis, estructurar defensa (diapositivas, guion), simular preguntas de comisión y apoyar en materias técnicas/contables.
{REGLA_GOBERNANZA}""",

    "3. Arquitecto de Software (CTO)": f"""ROL: CTO y Arquitecto de Software de Franco Marroquín. Experto Full-Stack, bases de datos y cloud, con formación en Ingeniería, Logística, Comercio Exterior y Contabilidad.
CONTEXTO: Desarrollas la aplicación funcional del proyecto de título en Santo Tomás.
TAREA: Diseñar arquitectura, base de datos, código limpio y documentación técnica (diagramas, diccionario de datos, manuales) alineada con la tesis.
{REGLA_GOBERNANZA}""",

    "4. Estratega Corporativo": f"""ROL: Gerente de Operaciones y Estratega Corporativo de Franco Marroquín. Ingeniero experto en Logística de última milla, Comercio Exterior, Contabilidad de costos y Auditoría.
CONTEXTO: Trabajo en 99minutos (franco.marroquin@99minutos.com). Proteges estrictamente la confidencialidad de 99minutos sin filtrar datos sensibles.
TAREA: Alinear experiencia laboral con el proyecto de título, auditar cruzadamente al Director Académico y CTO (qué agregar/quitar) y proyectar futura comercialización.
{REGLA_GOBERNANZA}""",

    "5. Director Financiero (CFO)": f"""ROL: CFO de Franco Marroquín. Contador Auditor, Ingeniero Comercial y Asesor Financiero en Chile (CLP/UF).
CONTEXTO: Finanzas personales (marro.ccb@gmail.com) y evaluación económica del proyecto/futura empresa.
TAREA: Ordenar flujo de caja personal, presupuesto, ahorro e inversión (APV, UF, cuentas remuneradas). Evaluar costos/precios del proyecto. Nunca pidas claves bancarias.
{REGLA_GOBERNANZA}""",

    "6. Director Legal y Tributario": f"""ROL: Director Legal y Tributario de Franco Marroquín. Abogado Corporativo y Tributario especialista en legislación chilena (SII, Código del Trabajo, Propiedad Intelectual/INAPI, SpA).
CONTEXTO: Empleo en 99minutos, tesis en Santo Tomás.
TAREA: Blindar propiedad intelectual del software, prevenir conflictos laborales/académicos y preparar constitución de empresa real (SpA/EIRL) y régimen tributario SII. Recomienda validación presencial cuando aplique.
{REGLA_GOBERNANZA}""",

    "7. Médico de Cabecera": f"""ROL: Médico de Cabecera y Director de Bienestar de Franco Marroquín. Médico General especialista en medicina del estilo de vida, nutrición clínica, sueño, ergonomía y prevención de burnout.
CONTEXTO: Alta carga cognitiva (99minutos + tesis + software).
TAREA: Optimizar sueño, alimentación práctica, pausas activas y preparación de consultas médicas reales.
ÉTICA MÉDICA: Nunca emitas diagnósticos definitivos ni prescribas fármacos con receta. Ante señales de alarma, deriva a urgencias presencial.
{REGLA_GOBERNANZA}"""
}

# --- BARRA LATERAL ---
with st.sidebar:
    st.title("⚙️ Configuración")
    api_guardada = st.secrets.get("GEMINI_API_KEY", "")
    api_key = st.text_input("🔑 API Key Gemini:", value=api_guardada, type="password")

    st.markdown("---")
    contenido_actual, fecha_act = obtener_estado_maestro()
    st.subheader("🧠 Estado Maestro")
    st.caption(f"Sincronizado en Google Sheets: {fecha_act}")
    nuevo_estado = st.text_area("Memoria compartida:", value=contenido_actual, height=220)
    if st.button("💾 Guardar Manualmente", use_container_width=True):
        guardar_estado_maestro(nuevo_estado)
        st.success("Memoria actualizada en la nube.")
        st.rerun()

# --- NAVEGACIÓN PRINCIPAL ---
tab_chat, tab_finanzas, tab_memoria = st.tabs(["💬 Directorio IA", "💰 Finanzas (CLP)", "🧠 Memoria Global"])

with tab_chat:
    col1, col2 = st.columns([4, 1])
    with col1:
        agente_seleccionado = st.selectbox("Selecciona Departamento:", list(AGENTES.keys()), label_visibility="collapsed")
    with col2:
        if st.button("🗑️ Limpiar", help="Borrar historial de este agente", use_container_width=True):
            limpiar_historial_agente(agente_seleccionado)
            st.rerun()

    mensajes_db = obtener_mensajes(agente_seleccionado)
    for msg in mensajes_db:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            st.caption(msg["time"])

    if prompt_usuario := st.chat_input("Escribe tu mensaje al directorio..."):
        if not api_key:
            st.warning("⚠️ Agrega tu GEMINI_API_KEY en los Secrets de Streamlit Cloud.")
        else:
            guardar_mensaje(agente_seleccionado, "user", prompt_usuario)
            with st.chat_message("user"):
                st.markdown(prompt_usuario)

            try:
                genai.configure(api_key=api_key)
                modelo = genai.GenerativeModel('gemini-2.5-flash')

                historial_reciente = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in mensajes_db[-8:]])

                contexto_extra = ""
                if "Director Financiero" in agente_seleccionado:
                    df_fin = obtener_finanzas_df()
                    if not df_fin.empty:
                        resumen_fin = df_fin.head(15).to_string(index=False)
                        contexto_extra = f"\nÚLTIMOS MOVIMIENTOS FINANCIEROS EN GOOGLE SHEETS (CLP):\n{resumen_fin}\n"

                prompt_completo = f"""
{AGENTES[agente_seleccionado]}

ESTADO MAESTRO ACTUAL:
{contenido_actual}
{contexto_extra}
HISTORIAL RECIENTE:
{historial_reciente}

MENSAJE DE FRANCO:
{prompt_usuario}
"""
                with st.spinner("Consultando al departamento..."):
                    respuesta = modelo.generate_content(prompt_completo)
                    texto_respuesta = respuesta.text

                patron = r"\[ESTADO_MAESTRO_INICIO\](.*?)\[ESTADO_MAESTRO_FIN\]"
                coincidencia = re.search(patron, texto_respuesta, re.DOTALL)
                if coincidencia:
                    estado_extraido = coincidencia.group(1).strip()
                    guardar_estado_maestro(estado_extraido)
                    texto_respuesta = re.sub(patron, "\n✅ *Memoria sincronizada permanentemente en Google Sheets.*", texto_respuesta, flags=re.DOTALL)

                guardar_mensaje(agente_seleccionado, "assistant", texto_respuesta)
                with st.chat_message("assistant"):
                    st.markdown(texto_respuesta)

            except Exception as e:
                st.error(f"Error de conexión: {e}")

with tab_finanzas:
    st.subheader("Control Financiero Personal (CLP)")

    with st.expander("➕ Registrar Ingreso o Gasto", expanded=False):
        with st.form("form_finanzas", clear_on_submit=True):
            tipo = st.selectbox("Tipo:", ["Gasto", "Ingreso", "Ahorro / Inversión"])
            categoria = st.selectbox("Categoría:", ["Sueldo / Honorarios", "Vivienda / Cuentas", "Alimentación", "Transporte", "Estudios / Tesis", "Salud", "Ocio", "Fondo Empresa", "Otros"])
            descripcion = st.text_input("Detalle (ej. Supermercado, Pago cuota):")
            monto = st.number_input("Monto ($ CLP):", min_value=0, step=1000)
            if st.form_submit_button("Guardar Movimiento", use_container_width=True):
                if monto > 0:
                    agregar_movimiento_financiero(tipo, categoria, descripcion, monto)
                    st.success("Guardado en Google Sheets. El CFO ya puede analizarlo.")
                    st.rerun()

    df_finanzas = obtener_finanzas_df()
    if not df_finanzas.empty:
        ingresos = df_finanzas[df_finanzas["tipo"] == "Ingreso"]["monto"].sum()
        gastos = df_finanzas[df_finanzas["tipo"] == "Gasto"]["monto"].sum()
        ahorro = df_finanzas[df_finanzas["tipo"] == "Ahorro / Inversión"]["monto"].sum()
        balance = ingresos - gastos - ahorro

        c1, c2, c3 = st.columns(3)
        c1.metric("Ingresos", f"${ingresos:,.0f}")
        c2.metric("Gastos", f"${gastos:,.0f}")
        c3.metric("Disponible", f"${balance:,.0f}")

        st.dataframe(df_finanzas[["fecha", "tipo", "categoria", "descripcion", "monto"]], use_container_width=True, hide_index=True)
    else:
        st.info("Registra tu primer movimiento arriba para que el **5. Director Financiero** analice tus números.")

with tab_memoria:
    st.subheader("🧠 Estado Maestro del Directorio")
    st.caption(f"Última sincronización: {fecha_act}")
    st.markdown(contenido_actual)
