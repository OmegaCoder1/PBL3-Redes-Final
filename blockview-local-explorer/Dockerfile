FROM node:18-alpine

WORKDIR /app

# Copia os arquivos de configuração
COPY package*.json ./
COPY tsconfig*.json ./
COPY vite.config.ts ./
COPY tailwind.config.ts ./
COPY postcss.config.js ./
COPY components.json ./
COPY index.html ./

# Instala as dependências
RUN npm install

# Copia o código fonte
COPY src/ ./src/
COPY public/ ./public/

# Build da aplicação
RUN npm run build

# Instala o serve para servir os arquivos estáticos
RUN npm install -g serve

# Expõe a porta 8080
EXPOSE 8080

# Comando para servir os arquivos estáticos
CMD ["serve", "-s", "dist", "-l", "8080"] 