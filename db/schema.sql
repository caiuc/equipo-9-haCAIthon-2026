
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    rut VARCHAR(12) UNIQUE NOT NULL,
    hash_pass TEXT NOT NULL, 
    rol VARCHAR(10) NOT NULL     
);

CREATE TABLE IF NOT EXISTS profiles (
    id SERIAL PRIMARY KEY,
    user_id INT UNIQUE REFERENCES users(id),
    full_name VARCHAR(100) NOT NULL,
    bio_data TEXT        
);

CREATE TABLE IF NOT EXISTS docs (
    id SERIAL PRIMARY KEY,
    patient_id INT REFERENCES users(id),
    author_id INT REFERENCES users(id),
    file_title TEXT NOT NULL,         
    file_uuid VARCHAR(255) UNIQUE NOT NULL, 
    is_validated BOOLEAN DEFAULT FALSE,    
    submit_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS auditoria_accesos (
    id SERIAL PRIMARY KEY,
    doc_id INT REFERENCES docs(id),
    patient_id INT REFERENCES users(id),
    access_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);