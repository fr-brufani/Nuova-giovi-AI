# pms-sync-service/Dockerfile

# Stage 1: Build the application
FROM node:18-slim AS build
WORKDIR /usr/src/app
# Copia solo i file necessari per installare le dipendenze
COPY package*.json ./
# Installa TUTTE le dipendenze (incluse dev) per la build
RUN npm ci

# Copia il resto del codice sorgente
COPY . .
# Compila TypeScript (lo script in package.json ora usa 'node .../tsc')
RUN npm run build

# Stage 2: Create the final production image
FROM node:18-slim AS production
ENV NODE_ENV=production
WORKDIR /usr/src/app
# Copia solo i file necessari per installare le dipendenze di produzione
COPY package*.json ./
# Installa SOLO le dipendenze di produzione
RUN npm ci --only=production --ignore-scripts
# Copia il codice compilato dalla fase di build
COPY --from=build /usr/src/app/lib ./lib
# Esponi la porta (Cloud Run userà $PORT, ma 8080 è un default comune)
EXPOSE 8080
# Comando per avviare l'applicazione
CMD [ "node", "lib/server.js" ]