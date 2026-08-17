FROM node:20-alpine

RUN corepack enable

WORKDIR /app

COPY frontend/package.json ./
COPY frontend/pnpm-lock.yaml* ./

RUN pnpm install

COPY frontend ./

ENV NEXT_PUBLIC_API_URL=http://localhost:8000

EXPOSE 3000

CMD ["pnpm", "dev", "-H", "0.0.0.0"]
