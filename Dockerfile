FROM python:3.12-slim AS build

RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
RUN pip install uv

WORKDIR /app
COPY . .

RUN uv sync --frozen
RUN git init && git add -A && git -c user.name=build -c user.email=build@localhost commit -m "build"
RUN uv run --group dev python -m mkdocs build --strict --site-dir _site/docs

RUN mkdir -p _site && cp -r website/* _site/

FROM nginx:alpine
COPY --from=build /app/_site /usr/share/nginx/html
EXPOSE 80
