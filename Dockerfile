# Utiliser une image de base Python qui permet d'installer des paquets système
# python:3.11-slim-bookworm est un bon choix
FROM python:3.11-slim-bookworm

# Installer les dépendances nécessaires à Chrome et Chrome lui-même
# Ces commandes s'exécutent DANS le conteneur pendant sa construction
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    wget \
    gnupg && \
    wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && \
    apt-get install -y google-chrome-stable && \
    rm -rf /var/lib/apt/lists/*

# Définir le répertoire de travail dans le conteneur Docker
WORKDIR /app

# Copier le fichier des dépendances Python et les installer
# On le fait séparément pour que Docker puisse réutiliser cette étape si seuls les fichiers code changent
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier tout le reste de votre code source (vinted2.py, etc.) dans le conteneur
COPY . .

# Commande par défaut à exécuter lorsque le conteneur démarre
# C'est ce qui lance votre script
CMD ["python", "vinted2.py"]

# Note : Si votre script devait écouter sur un port, vous ajouteriez EXPOSE <port> ici.
# Pour un simple script qui s'exécute et s'arrête, CMD suffit.