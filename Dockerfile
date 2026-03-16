FROM python:3.12-slim AS build

RUN pip install uv

WORKDIR /app
COPY . .

RUN uv sync --frozen
RUN uv run --group dev python -m mkdocs build --strict --site-dir _site/docs

RUN mkdir -p _site && cp -r website/* _site/

FROM nginx:alpine
COPY --from=build /app/_site /usr/share/nginx/html
EXPOSE 80
