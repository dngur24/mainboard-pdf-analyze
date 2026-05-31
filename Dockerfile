# 1. Base image
FROM node:20-slim

# 2. Set working directory
WORKDIR /app

# 3. Copy package files and install dependencies
# 패키지 파일을 먼저 복사하여 캐시 효율을 높입니다.
COPY package*.json ./
RUN npm install --production

# 4. Copy project files
# .dockerignore에 정의된 파일을 제외한 모든 파일을 복사합니다.
COPY . .

# 5. Environment variables
# 런타임에 .env 파일이나 컨테이너 설정으로 주입받아야 합니다.
ENV PORT=3000
ENV NODE_ENV=production

# 6. Expose port
EXPOSE 3000

# 7. Execution command
CMD ["node", "app.js"]
