FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/templates/default.conf.template
COPY index.html styles.css app.js /usr/share/nginx/html/

EXPOSE 80
