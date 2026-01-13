FROM python:3.13-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1

WORKDIR /app

# ÉTAPE X: Installation de wkhtmltopdf (et autres trucs)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl gnupg wkhtmltopdf \
    libxrender1 libfontconfig1 libnss3 libxss1 libasound2 libatk1.0-0 \
    libatk-bridge2.0-0 libcups2 libdrm2 libgbm1 libxkbcommon0 libgtk-3-0 libglib2.0-0 \
    git \
    && rm -rf /var/lib/apt/lists/*

# ÉTAPE X: Installation des dépendances Python
COPY pyproject.toml /app/
COPY . /app/
RUN pip install --no-cache-dir .

# ÉTAPE X : Télécharge et installe les binaires des navigateurs (Chromium ici)
# RUN python -m playwright install --with-deps chromium

# COPY . /app/

ENTRYPOINT ["python", "gourgandin.py"]
