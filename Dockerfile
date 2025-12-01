FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# ÉTAPE X: Installation de wkhtmltopdf (et autres libs nécessaires)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl gnupg wkhtmltopdf \
    libxrender1 libfontconfig1 \
    git \
    && rm -rf /var/lib/apt/lists/*

# ÉTAPE X: Installation des dépendances Python
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

ENTRYPOINT ["python", "gourgandin.py"]
