# Static file serving — no build step, no node_modules, no npm supply
# chain. Chart.js is vendored (src/vendor/) rather than pulled from a CDN
# at request time, so this image is fully self-contained.

FROM nginx:1.27-alpine

RUN adduser -D -u 1000 appuser \
    && chown -R appuser:appuser /var/cache/nginx /var/run \
    && touch /var/run/nginx.pid \
    && chown appuser:appuser /var/run/nginx.pid

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY src/ /usr/share/nginx/html/

USER 1000
EXPOSE 8080
