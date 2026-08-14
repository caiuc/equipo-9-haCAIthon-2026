import os

import psycopg2
from cryptography.fernet import Fernet
from werkzeug.security import check_password_hash, generate_password_hash

MEMORY_DB = {
    "users": [],
    "profiles": [],
    "documents": [],
    "access_logs": [],
}


def get_db_connection():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return None

    try:
        connection = psycopg2.connect(database_url)
        connection.autocommit = False
        return connection
    except Exception:
        return None


def _next_user_id():
    return max((user["id"] for user in MEMORY_DB["users"]), default=0) + 1


def _next_profile_id():
    return max((profile["id"] for profile in MEMORY_DB["profiles"]), default=0) + 1


def _next_document_id():
    return max((document["id"] for document in MEMORY_DB["documents"]), default=0) + 1


def _next_access_log_id():
    return max((log["id"] for log in MEMORY_DB["access_logs"]), default=0) + 1


def _get_fernet():
    key = os.getenv("FERNET_KEY")
    if not key:
        raise ValueError("FERNET_KEY no configurada")
    return Fernet(key.encode())


def encrypt_title(title: str) -> str:
    return _get_fernet().encrypt(title.encode("utf-8")).decode("utf-8")


def decrypt_title(cipher_text: str) -> str:
    return _get_fernet().decrypt(cipher_text.encode("utf-8")).decode("utf-8")


def get_user_by_rut(rut: str):
    connection = get_db_connection()
    if connection is None:
        for user in MEMORY_DB["users"]:
            if user["rut"] == rut:
                return user
        return None

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, rut, hash_pass, rol FROM users WHERE rut = %s",
                (rut,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return {
                "id": row[0],
                "rut": row[1],
                "hash_pass": row[2],
                "rol": row[3],
            }
    except Exception:
        return get_user_by_rut(rut)
    finally:
        connection.close()


def create_user_with_profile(rut: str, password: str, nombre_completo: str, rol: str = "paciente") -> bool:
    if not rut or not password or not nombre_completo:
        raise ValueError("rut, password y nombre_completo son obligatorios.")

    if get_user_by_rut(rut):
        return False

    connection = get_db_connection()
    if connection is None:
        user_id = _next_user_id()
        MEMORY_DB["users"].append(
            {
                "id": user_id,
                "rut": rut,
                "hash_pass": generate_password_hash(password),
                "rol": rol,
            }
        )
        MEMORY_DB["profiles"].append(
            {
                "id": _next_profile_id(),
                "user_id": user_id,
                "full_name": nombre_completo,
                "bio_data": "",
            }
        )
        return True

    try:
        with connection.cursor() as cursor:
            hashed_password = generate_password_hash(password)
            cursor.execute(
                "INSERT INTO users (rut, hash_pass, rol) VALUES (%s, %s, %s) RETURNING id",
                (rut, hashed_password, rol),
            )
            user_id = cursor.fetchone()[0]

            cursor.execute(
                "INSERT INTO profiles (user_id, full_name, bio_data) VALUES (%s, %s, %s)",
                (user_id, nombre_completo, ""),
            )

        connection.commit()
        return True
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def authenticate_user(rut: str, password: str):
    user = get_user_by_rut(rut)
    if not user:
        return None

    if not check_password_hash(user["hash_pass"], password):
        return None

    return user


def create_document_for_patient(rut_paciente: str, rut_autor: str, titulo_examen: str, archivo_uuid: str):
    paciente = get_user_by_rut(rut_paciente)
    if paciente is None:
        return None

    autor = get_user_by_rut(rut_autor)
    if autor is None:
        return None

    encrypted_title = encrypt_title(titulo_examen)

    connection = get_db_connection()
    if connection is None:
        document = {
            "id": _next_document_id(),
            "patient_id": paciente["id"],
            "author_id": autor["id"],
            "file_title": encrypted_title,
            "file_uuid": archivo_uuid,
            "is_validated": autor["rol"] == "medico",
        }
        MEMORY_DB["documents"].append(document)
        return document

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO docs (patient_id, author_id, file_title, file_uuid, is_validated) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                (paciente["id"], autor["id"], encrypted_title, archivo_uuid, autor["rol"] == "medico"),
            )
            document_id = cursor.fetchone()[0]
        connection.commit()
        return {"id": document_id}
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def get_patient_documents_by_rut(rut_paciente: str):
    paciente = get_user_by_rut(rut_paciente)
    if paciente is None:
        return []

    connection = get_db_connection()
    if connection is None:
        documents = []
        for document in MEMORY_DB["documents"]:
            if document["patient_id"] == paciente["id"]:
                documents.append(
                    {
                        "id": document["id"],
                        "file_uuid": document["file_uuid"],
                        "titulo": decrypt_title(document["file_title"]),
                        "es_validado": document["is_validated"],
                    }
                )
        return documents

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, file_uuid, file_title, is_validated FROM docs WHERE patient_id = %s ORDER BY submit_date DESC",
                (paciente["id"],),
            )
            rows = cursor.fetchall()
            return [
                {
                    "id": row[0],
                    "file_uuid": row[1],
                    "titulo": decrypt_title(row[2]),
                    "es_validado": row[3],
                }
                for row in rows
            ]
    finally:
        connection.close()


def register_access_log(rut_paciente: str, rut_medico: str):
    paciente = get_user_by_rut(rut_paciente)
    medico = get_user_by_rut(rut_medico)
    if paciente is None or medico is None:
        return None

    connection = get_db_connection()
    if connection is None:
        log = {
            "id": _next_access_log_id(),
            "doc_id": None,
            "patient_id": paciente["id"],
            "access_date": "now",
        }
        MEMORY_DB["access_logs"].append(log)
        return log

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO auditoria_accesos (patient_id) VALUES (%s) RETURNING id",
                (paciente["id"],),
            )
            log_id = cursor.fetchone()[0]
        connection.commit()
        return {"id": log_id}
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
