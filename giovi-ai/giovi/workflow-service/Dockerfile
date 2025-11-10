# workflow-service/Dockerfile

# Stage 1: Build the application
FROM node:18-slim AS build
WORKDIR /usr/src/app

COPY package*.json ./
# Installa TUTTE le dipendenze, incluse devDependencies come typescript
RUN npm ci

# <<< MODIFICA CHIAVE: Installa typescript globalmente IN QUESTO STAGE DI BUILD >>>
RUN npm install -g typescript

COPY . .
# Esegui lo script di build definito in package.json
# Ora 'tsc' (o 'npx tsc') dovrebbe essere trovato nel PATH globale di questo stage
RUN npm run build

# Stage 2: Create the final production image
FROM node:18-slim AS production
ENV NODE_ENV=production
WORKDIR /usr/src/app

# Copia package.json e package-lock.json dalla fase di build
COPY --from=build /usr/src/app/package.json ./package.json
COPY --from=build /usr/src/app/package-lock.json ./package-lock.json

# Installa SOLO le dipendenze di produzione
RUN npm ci --only=production --ignore-scripts

# Copia il codice JavaScript compilato dalla cartella /lib della fase di build
COPY --from=build /usr/src/app/lib ./lib

EXPOSE 8080
CMD [ "node", "lib/server.js" ]