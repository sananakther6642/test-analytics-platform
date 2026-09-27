# Static file serving — no build step, no node_modules, no npm supply
# chain. Chart.js is vendored (src/vendor/) rather than pulled from a CDN
# at request time, so this image is fully self-contained.

FROM nginx:1.27-alpine

RUN adduser -D -u 1000 appuser \
    && chown -R appuser:appuser /var/cache/nginx /var/run /etc/nginx/conf.d \
    && touch /var/run/nginx.pid \
    && chown appuser:appuser /var/run/nginx.pid

# nginx's own entrypoint runs envsubst on every *.template here, writing
# the result to /etc/nginx/conf.d/ before startup — see nginx.conf's
# comment on why the upstream host can't be hardcoded.
COPY nginx.conf /etc/nginx/templates/default.conf.template
COPY src/ /usr/share/nginx/html/

ENV API_UPSTREAM_HOST=api:8000
ENV API_UPSTREAM_SCHEME=http

USER 1000
EXPOSE 8080
