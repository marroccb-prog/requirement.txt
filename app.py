import streamlit as st


def main():
    st.title("🚀 Mi aplicación Streamlit")
    st.write(
        "La app está funcionando correctamente desde app.py. "
        "Esto mantiene compatibilidad con Streamlit Cloud y con la ruta principal configurada."
    )
    st.caption("Si luego quieres cambiar el punto de entrada de despliegue, usa app.py o streamlit_app.py.")


if __name__ == "__main__":
    main()
