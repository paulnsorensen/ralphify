# Ralphify — website & docs build tasks
# These recipes build the static site served at ralphify.co

# Output directory for the combined site (separate from dist/ which is for the Python package)
site_dir := "_site"

# Build everything: landing page + docs → dist/website/
[group('website')]
website-build: website-build-landing website-build-docs

# Build only the landing page → dist/website/
[group('website')]
website-build-landing:
    rm -rf {{ site_dir }}
    mkdir -p {{ site_dir }}
    cp -r website/* {{ site_dir }}/

# Build only the mkdocs site → dist/website/docs/
[group('website')]
website-build-docs:
    uv run --group dev python -m mkdocs build --strict --site-dir {{ site_dir }}/docs

# Preview the landing page (serves dist/website/ on port 8080)
[group('website')]
website-preview: website-build
    cd {{ site_dir }} && python3 -m http.server 8080

# Preview docs only (mkdocs dev server on port 8000)
[group('website')]
docs-preview:
    uv run --group dev python -m mkdocs serve
