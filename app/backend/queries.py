import os

import psycopg2
from werkzeug.security import check_password_hash, generate_password_hash

MEMORY_DB = {
    "users": [],
    "profiles": [],
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
