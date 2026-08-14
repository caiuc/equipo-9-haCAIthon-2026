import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, render_template_string, redirect, request, session, url_for, render_template

if __package__ in (None, ""):
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from app.backend.queries import (
        authenticate_user,
        create_document_for_patient,
        create_user_with_profile,
        get_patient_documents_by_rut,
        get_user_by_rut,
        register_access_log,
    )
else:
    from app.backend.queries import (
        authenticate_user,
        create_document_for_patient,
        create_user_with_profile,
        get_patient_documents_by_rut,
        get_user_by_rut,
        register_access_log,
    )

load_dotenv()

app = Flask(__name__, template_folder='frontend/templates')
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")


@app.route("/")
def inicio():
    if "user_id" in session:
        return redirect(url_for("portal"))
    return redirect(url_for("login"))


@app.route("/portal")
def portal():
    if "user_id" not in session: return redirect(url_for("login"))
    # Simulamos el objeto usuario para el HTML
    usuario = {"nombre_completo": "Usuario", "rol": session.get("rol"), "rut": session.get("rut")}
    documentos = get_patient_documents_by_rut(session.get("rut")) if session.get("rol") == "paciente" else []
    return render_template("portal.html", usuario=usuario, documentos=documentos)


@app.route("/historial", methods=["GET"])
def historial():
    if "user_id" not in session or session.get("rol") != "medico": return redirect(url_for("login"))
    rut_paciente = request.args.get("rut_paciente")
    documentos = get_patient_documents_by_rut(rut_paciente)
    return render_template("portal.html", usuario={"rol": "medico", "rut": rut_paciente}, documentos=documentos)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        rut = request.form.get("rut", "").strip()
        password = request.form.get("password", "")

        try:
            user = authenticate_user(rut, password)
        except Exception as exc:
            app.logger.error("Error en autenticacion para rut=%s: %s", rut, exc, exc_info=True)
            return "Error interno al autenticar.", 500

        if not user:
            return "Credenciales inválidas.", 401

        session["user_id"] = user["id"]
        session["rol"] = user["rol"]
        session["rut"] = user["rut"]
        return redirect(url_for("portal"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# Reemplaza la ruta /registro completa
@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        rut = request.form.get("rut", "").strip()
        password = request.form.get("password", "")
        nombre_completo = request.form.get("nombre_completo", "").strip()
        rol = request.form.get("rol", "paciente").strip()
        
        try:
            if create_user_with_profile(rut, password, nombre_completo, rol):
                return redirect(url_for("login"))
        except:
            return "Error en registro", 400
    return render_template("register.html")


@app.route("/subir_examen", methods=["POST"])
def subir_examen():
    if "user_id" not in session:
        return redirect(url_for("login"))

    rut_paciente = request.form.get("rut_paciente", "").strip()
    titulo_examen = request.form.get("titulo_examen", "").strip()
    archivo = request.files.get("archivo")

    if not rut_paciente or not titulo_examen or archivo is None:
        return "Faltan datos o archivo para subir el examen.", 400

    file_content = archivo.read()
    if not file_content:
        return "El archivo está vacío.", 400

    try:
        created = create_document_for_patient(
            rut_paciente=rut_paciente,
            rut_autor=session.get("rut", ""),
            titulo_examen=titulo_examen,
            archivo_uuid=archivo.filename,
            file_content=file_content,
            content_type=archivo.mimetype,
        )
    except Exception as exc:
        app.logger.error(
            "Error interno en /subir_examen para rut_paciente=%s: %s",
            rut_paciente,
            exc,
            exc_info=True,
        )
        return "Error interno al subir examen.", 500

    if created is None:
        return "No se pudo registrar el examen.", 500

    return redirect(url_for("historial", rut_paciente=rut_paciente))

# app.py
from flask import redirect, jsonify
from backend.queries import generar_url_lectura

@app.route('/ver_documento/<path:nombre_archivo>', methods=['GET'])
def ver_documento(nombre_archivo):
    # NOTA: En un sistema real, aquí verificarías si el usuario tiene sesión iniciada
    # usando la variable 'session' de Flask antes de generar la URL.
    
    url_temporal = generar_url_lectura(nombre_archivo)
    
    if url_temporal:
        # Redirige el navegador automáticamente al PDF autorizado
        return redirect(url_temporal)
    else:
        return jsonify({"error": "Archivo no encontrado o error de permisos"}), 404


if __name__ == "__main__":
    app.run(debug=True)