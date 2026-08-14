import os
from uuid import uuid4

import httpx
import psycopg2
from cryptography.fernet import Fernet
from dotenv import load_dotenv
from werkzeug.security import check_password_hash, generate_password_hash
from supabase import create_client, Client


MEMORY_DB = {
    "users": [],
    "profiles": [],
    "documents": [],
    "access_logs": [],
}


load_dotenv()


def _get_supabase_base_url() -> str:
    url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    if url.endswith("/rest/v1"):
        url = url[: -len("/rest/v1")]
    return url


def _get_supabase_storage_key() -> str:
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if key:
        return key

    key = os.getenv("SUPABASE_KEY", "")
    if key.startswith("sb_publishable_"):
        print("[DB WARNING] Se está usando SUPABASE_KEY publishable para Storage; puede fallar por RLS.")
    return key


def get_storage_bucket_name() -> str:
    return os.getenv("SUPABASE_BUCKET", "hacaithon-docs")


def build_storage_metadata(file_uuid: str) -> dict:
    bucket = get_storage_bucket_name()
    storage_path = f"{bucket}/{file_uuid}"
    supabase_url = _get_supabase_base_url()

    public_url = None
    if supabase_url:
        public_url = f"{supabase_url}/storage/v1/object/public/{bucket}/{file_uuid}"

    return {
        "bucket_name": bucket,
        "storage_path": storage_path,
        "public_url": public_url,
    }


def upload_file_to_supabase_storage(original_filename: str, file_content: bytes, content_type: str | None = None) -> dict:
    bucket = get_storage_bucket_name()
    supabase_url = _get_supabase_base_url()
    supabase_key = _get_supabase_storage_key()

    if not supabase_url or not supabase_key:
        print("[DB WARNING] upload_file_to_supabase_storage: SUPABASE_URL/SUPABASE_KEY no configuradas.")
        return {
            "uploaded": False,
            "file_uuid": original_filename,
            "bucket_name": bucket,
        }

    sanitized_name = os.path.basename(original_filename)
    object_key = f"exams/{uuid4().hex}_{sanitized_name}"
    upload_url = f"{supabase_url}/storage/v1/object/{bucket}/{object_key}"

    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": content_type or "application/octet-stream",
        "x-upsert": "true",
    }

    response = httpx.post(upload_url, content=file_content, headers=headers, timeout=30.0)
    if response.status_code >= 400:
        raise RuntimeError(
            "Error subiendo archivo a Supabase Storage "
            f"(status={response.status_code}): {response.text}"
        )

    return {
        "uploaded": True,
        "file_uuid": object_key,
        "bucket_name": bucket,
    }


def delete_file_from_supabase_storage(file_uuid: str):
    supabase_url = _get_supabase_base_url()
    supabase_key = _get_supabase_storage_key()
    bucket = get_storage_bucket_name()

    if not supabase_url or not supabase_key:
        return

    delete_url = f"{supabase_url}/storage/v1/object/{bucket}/{file_uuid}"
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
    }

    try:
        httpx.delete(delete_url, headers=headers, timeout=15.0)
    except Exception as exc:
        print(f"[DB ERROR] No se pudo eliminar archivo huérfano en storage: {exc}")


def get_db_connection():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return None

    try:
        connection = psycopg2.connect(database_url)
        connection.autocommit = False
        return connection
    except Exception as exc:
        # Keep local fallback behavior, but surface the real DB error.
        print(f"[DB ERROR] No se pudo conectar a PostgreSQL/Supabase: {exc}")
        return None


def _warn_memory_fallback(context: str):
    if os.getenv("DATABASE_URL"):
        print(f"[DB WARNING] {context}: usando MEMORY_DB por fallo de conexión; no se persiste en Supabase.")


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
        _warn_memory_fallback("get_user_by_rut")
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
    except Exception as exc:
        connection.rollback()
        print(f"[DB ERROR] Fallo en get_user_by_rut para rut={rut}: {exc}")
        return None
    finally:
        connection.close()


def create_user_with_profile(rut: str, password: str, nombre_completo: str, rol: str = "paciente") -> bool:
    if not rut or not password or not nombre_completo:
        raise ValueError("rut, password y nombre_completo son obligatorios.")

    if get_user_by_rut(rut):
        return False

    connection = get_db_connection()
    if connection is None:
        _warn_memory_fallback("create_user_with_profile")
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
    except Exception as exc:
        connection.rollback()
        print(f"[DB ERROR] Fallo en create_user_with_profile para rut={rut}: {exc}")
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


def create_document_for_patient(
    rut_paciente: str,
    rut_autor: str,
    titulo_examen: str,
    archivo_uuid: str,
    file_content: bytes | None = None,
    content_type: str | None = None,
):
    paciente = get_user_by_rut(rut_paciente)
    if paciente is None:
        return None

    autor = get_user_by_rut(rut_autor)
    if autor is None:
        return None

    encrypted_title = encrypt_title(titulo_examen)
    uploaded_file_uuid = archivo_uuid

    if file_content is not None:
        upload_result = upload_file_to_supabase_storage(archivo_uuid, file_content, content_type)
        uploaded_file_uuid = upload_result["file_uuid"]

    connection = get_db_connection()
    if connection is None:
        _warn_memory_fallback("create_document_for_patient")
        storage = build_storage_metadata(uploaded_file_uuid)
        document = {
            "id": _next_document_id(),
            "patient_id": paciente["id"],
            "author_id": autor["id"],
            "file_title": encrypted_title,
            "file_uuid": uploaded_file_uuid,
            "is_validated": autor["rol"] == "medico",
            "bucket_name": storage["bucket_name"],
            "storage_path": storage["storage_path"],
            "public_url": storage["public_url"],
        }
        MEMORY_DB["documents"].append(document)
        return document

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO docs (patient_id, author_id, file_title, file_uuid, is_validated) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                (paciente["id"], autor["id"], encrypted_title, uploaded_file_uuid, autor["rol"] == "medico"),
            )
            document_id = cursor.fetchone()[0]
        connection.commit()
        return {"id": document_id}
    except Exception as exc:
        connection.rollback()
        if uploaded_file_uuid != archivo_uuid:
            delete_file_from_supabase_storage(uploaded_file_uuid)
        print(
            f"[DB ERROR] Fallo en create_document_for_patient para rut_paciente={rut_paciente}, rut_autor={rut_autor}: {exc}"
        )
        raise
    finally:
        connection.close()


def get_patient_documents_by_rut(rut_paciente: str):
    paciente = get_user_by_rut(rut_paciente)
    if paciente is None:
        return []

    connection = get_db_connection()
    if connection is None:
        _warn_memory_fallback("get_patient_documents_by_rut")
        documents = []
        for document in MEMORY_DB["documents"]:
            if document["patient_id"] == paciente["id"]:
                storage = build_storage_metadata(document["file_uuid"])
                documents.append(
                    {
                        "id": document["id"],
                        "file_uuid": document["file_uuid"],
                        "titulo": decrypt_title(document["file_title"]),
                        "es_validado": document["is_validated"],
                        "bucket_name": document.get("bucket_name", storage["bucket_name"]),
                        "storage_path": document.get("storage_path", storage["storage_path"]),
                        "public_url": document.get("public_url", storage["public_url"]),
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
            documents = []
            for row in rows:
                storage = build_storage_metadata(row[1])
                documents.append(
                    {
                        "id": row[0],
                        "file_uuid": row[1],
                        "titulo": decrypt_title(row[2]),
                        "es_validado": row[3],
                        "bucket_name": storage["bucket_name"],
                        "storage_path": storage["storage_path"],
                        "public_url": storage["public_url"],
                    }
                )
            return documents
    finally:
        connection.close()


def register_access_log(rut_paciente: str, rut_medico: str):
    paciente = get_user_by_rut(rut_paciente)
    medico = get_user_by_rut(rut_medico)
    if paciente is None or medico is None:
        return None

    connection = get_db_connection()
    if connection is None:
        _warn_memory_fallback("register_access_log")
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
    except Exception as exc:
        connection.rollback()
        print(f"[DB ERROR] Fallo en register_access_log para rut_paciente={rut_paciente}: {exc}")
        raise
    finally:
        connection.close()


url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") # Usamos la llave maestra
supabase: Client = create_client(url, key)

def generar_url_lectura(ruta_archivo):
    """
    Genera una URL firmada válida por 3600 segundos (1 hora)
    para que el frontend pueda visualizar el archivo privado.
    """
    try:
        # Pide a Supabase una URL temporal para el archivo en 'hacaithon-docs'
        respuesta = supabase.storage.from_('hacaithon-docs').create_signed_url(ruta_archivo, 3600)
        
        # Dependiendo de la versión del SDK, devuelve un diccionario o un string
        if isinstance(respuesta, dict) and 'signedURL' in respuesta:
            return respuesta['signedURL']
        return respuesta # Si el SDK devuelve el string directamente
    except Exception as e:
        print(f"Error generando URL firmada: {e}")
        return None