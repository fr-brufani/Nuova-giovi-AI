# Stage 1: Build the application
FROM node:20-slim AS build

WORKDIR /usr/src/app

# Copia package.json e package-lock.json (o npm-shrinkwrap.json)
COPY package*.json ./

# Installa *tutte* le dipendenze, incluse devDependencies per la build
# Usiamo --frozen-lockfile per assicurarci di usare le versioni esatte del lockfile
RUN npm ci

# Copia il codice sorgente (include lib pre-compilata)
COPY . .

# Verifica che lib esista e usa il JS pre-compilato
RUN npm run build && ls -la lib/

# Stage 2: Create the final production image
FROM node:20-slim AS production

ENV NODE_ENV=production
WORKDIR /usr/src/app

# Copia package.json e package-lock.json
COPY package*.json ./

# Installa *solo* le dipendenze di produzione in modo pulito
RUN npm ci --omit=dev --ignore-scripts

# Copia il codice compilato dalla fase di build
COPY --from=build /usr/src/app/lib ./lib

# Copia la cartella node_modules dalla fase di build (assicura coerenza)
# Questo può essere omesso se npm ci --only=production è sufficiente
# COPY --from=build /usr/src/app/node_modules ./node_modules

# Esponi la porta su cui l'applicazione ascolterà (Cloud Run usa $PORT)
EXPOSE 8080

# Comando per avviare l'applicazione
# Specifichiamo l'host 0.0.0.0 per accettare connessioni esterne al container
CMD [ "node", "lib/server.js" ]