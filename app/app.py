import os

from dotenv import load_dotenv
from flask import Flask, redirect, request, session, url_for

from app.backend.queries import authenticate_user, create_user_with_profile

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")


@app.route("/")
def inicio():
    if "user_id" in session:
        return f"Portal de usuario: {session.get('rol', 'usuario')}"
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        rut = request.form.get("rut", "").strip()
        password = request.form.get("password", "")

        user = authenticate_user(rut, password)
        if not user:
            return "Credenciales inválidas.", 401

        session["user_id"] = user["id"]
        session["rol"] = user["rol"]
        return redirect(url_for("inicio"))

    return "Pantalla de login"


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/registro", methods=["POST"])
def registro():
    rut = request.form.get("rut", "").strip()
    password = request.form.get("password", "")
    nombre_completo = request.form.get("nombre_completo", "").strip()
    rol = request.form.get("rol", "paciente").strip()

    if not rut or not password or not nombre_completo:
        return "Faltan datos obligatorios para el registro.", 400

    try:
        created = create_user_with_profile(
            rut=rut,
            password=password,
            nombre_completo=nombre_completo,
            rol=rol,
        )
    except ValueError as exc:
        return str(exc), 500

    if not created:
        return "El RUT ya existe en el sistema.", 400

    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)