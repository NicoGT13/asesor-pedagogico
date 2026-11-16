#!/usr/bin/env sh
# Recompila Tailwind tras modificar clases en index.html / app.js (requiere Node.js):
#   ./scripts/build_css.sh          (una vez)
#   ./scripts/build_css.sh --watch  (desarrollo)
npx --yes tailwindcss@3.4.17 -c tailwind.config.js -i frontend/src/input.css -o frontend/static/css/app.css --minify "$@"
