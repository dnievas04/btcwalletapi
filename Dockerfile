# Pull official base image
FROM python:3.8.0-alpine

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install psycopg2 dependencies
RUN apk update \
    && apk add postgresql-dev gcc python3-dev musl-dev

RUN mkdir /app
WORKDIR /app

# Install dependencies
RUN pip install --upgrade pip
COPY requirements.txt /app/
RUN pip install -r requirements.txt

# Copy entrypoint.sh
COPY entrypoint.sh /app/entrypoint.sh

# Copy project
COPY . /app/

# Run entrypoint.sh
ENTRYPOINT ["/app/entrypoint.sh"]