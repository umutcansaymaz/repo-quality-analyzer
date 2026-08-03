# repo-quality-analyzer — production image (Next.js standalone)
# Build:  docker build -t repo-quality-analyzer .
# Run:    docker run -p 3000:3000 repo-quality-analyzer

FROM node:24-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* bun.lock* ./
RUN npm ci --ignore-scripts || npm install --ignore-scripts

FROM node:24-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# Exclude dev/QA workspaces from the image (huge cloned-repo trees)
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM node:24-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

# Analysis results + SQLite store
RUN mkdir -p /app/db/analysis-results /app/validation_workspace

EXPOSE 3000
CMD ["node", "server.js"]
