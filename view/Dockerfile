FROM nginx:alpine

# Copiar los archivos de la web a Nginx
COPY view/ /usr/share/nginx/html/

# Puerto HTTP del contenedor
EXPOSE 80

# Ejecutar Nginx
CMD ["nginx", "-g", "daemon off;"]
