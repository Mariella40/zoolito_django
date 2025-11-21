# Descargar dependencias:

## 1. Crear entorno virtual:

### En Windows
`python -m venv venv`

### En Linux / macOS
`python3 -m venv venv`

## 2. Activar entorno virtual:

### En Windows (CMD o PowerShell)
`venv\Scripts\activate`

### En Linux / macOS
`source venv/bin/activate`

## 3. Instalar dependencias:

`pip install -r requirements.txt`

# Hacer migraciones:

`python manage.py makemigrations`

`python manage.py migrate`

# Ejecutar el servidor:

`python manage.py runserver 0.0.0.0:8000`