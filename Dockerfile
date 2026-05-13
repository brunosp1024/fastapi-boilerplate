FROM python:3.13.5

# Install Poetry
RUN pip install --no-cache-dir poetry

WORKDIR /app

# Copy dependency files first for better cache
COPY pyproject.toml poetry.lock* ./

# Install production dependencies (without dev)
RUN poetry config virtualenvs.create false \
	&& poetry install --no-interaction --no-ansi --no-root --only main

# Copy the rest of the code
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]