FROM python:3.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    postgresql-client \
    gettext \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN msgfmt locale/uk/LC_MESSAGES/django.po -o locale/uk/LC_MESSAGES/django.mo && \
    msgfmt locale/en/LC_MESSAGES/django.po -o locale/en/LC_MESSAGES/django.mo

RUN mkdir -p /app/logs /app/staticfiles /app/celerybeat

COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 8001

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["gunicorn", "warehouse.wsgi:application", "--bind", "0.0.0.0:8001", "--workers", "3", "--timeout", "60"]
