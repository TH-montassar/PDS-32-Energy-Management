# Image Python légère
FROM python:3.10-slim

# Dossier de travail
WORKDIR /app

# Copier les dépendances
COPY requirements.txt .

# Installer les dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code
COPY . .

# Exposer le port Flask
EXPOSE 5000

# Variable d'environnement
ENV FLASK_APP=app.py
ENV FLASK_ENV=development

# Commande de démarrage
CMD ["python", "app.py"]