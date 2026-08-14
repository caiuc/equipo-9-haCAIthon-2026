import os

from dotenv import load_dotenv
from flask import Flask, render_template_string, redirect, request, session, url_for

from app.backend.queries import (
    authenticate_user,
    create_document_for_patient,
    create_user_with_profile,
    get_patient_documents_by_rut,
    get_user_by_rut,
    register_access_log,
)

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")


@app.route("/")
def inicio():
    if "user_id" in session:
        return redirect(url_for("portal"))
    return redirect(url_for("login"))


@app.route("/portal")
def portal():
    if "user_id" not in session:
        return redirect(url_for("login"))

    rol = session.get("rol", "paciente")
    if rol == "medico":
        template = """
        <html>
            <body>
                <h1>Portal médico</h1>
                <p>Buscar paciente</p>
                <form action="/historial" method="get">
                    <input type="text" name="rut_paciente" placeholder="RUT del paciente">
                    <button type="submit">Buscar</button>
                </form>
            </body>
        </html>
        """
    else:
        template = """
        <html>
            <body>
                <h1>Mi historial</h1>
                <p>Documentos del paciente</p>
                <ul>
                    <li>Examen de laboratorio</li>
                    <li>Control cardiológico</li>
                </ul>
            </body>
        </html>
        """

    return render_template_string(template)


@app.route("/historial")
def historial():
    if "user_id" not in session:
        return redirect(url_for("login"))

    rut_paciente = request.args.get("rut_paciente", "").strip()
    if not rut_paciente:
        return "Debes indicar un RUT de paciente.", 400

    if session.get("rol") != "medico":
        return "Solo un médico puede consultar historiales ajenos.", 403

    paciente = get_user_by_rut(rut_paciente)
    if paciente is None:
        return "Paciente no encontrado.", 404

    documentos = get_patient_documents_by_rut(rut_paciente)
    register_access_log(rut_paciente, session.get("rut"))

    html = """
    <html>
        <body>
            <h1>Historial de paciente</h1>
            <p>Paciente: {{ paciente_rut }}</p>
            <ul>
                {% for documento in documentos %}
                    <li>
                        {{ documento.titulo }}
                        {% if documento.es_validado %}
                            - Validado
                        {% else %}
                            - Pendiente
                        {% endif %}
                    </li>
                {% endfor %}
            </ul>
        </body>
    </html>
    """

    return render_template_string(html, paciente_rut=rut_paciente, documentos=documentos)


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
        session["rut"] = user["rut"]
        return redirect(url_for("portal"))

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


@app.route("/subir_examen", methods=["POST"])
def subir_examen():
    if "user_id" not in session:
        return redirect(url_for("login"))

    rut_paciente = request.form.get("rut_paciente", "").strip()
    titulo_examen = request.form.get("titulo_examen", "").strip()
    archivo = request.files.get("archivo")

    if not rut_paciente or not titulo_examen or archivo is None:
        return "Faltan datos o archivo para subir el examen.", 400

    created = create_document_for_patient(
        rut_paciente=rut_paciente,
        rut_autor=session.get("rut", ""),
        titulo_examen=titulo_examen,
        archivo_uuid=archivo.filename,
    )

    if created is None:
        return "No se pudo registrar el examen.", 500

    return redirect(url_for("historial", rut_paciente=rut_paciente))


if __name__ == "__main__":
    app.run(debug=True)