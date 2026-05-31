# 1. Base image
# slim 버전에서 빌드 도구 부족으로 인한 오류를 방지하기 위해 전체 이미지를 사용합니다.
FROM node:20

# 2. Set working directory
WORKDIR /app

# 3. Copy package files and install dependencies
COPY package*.json ./

# npm install 시 발생할 수 있는 메모리/네트워크 문제를 방지하기 위해 
# 몇 가지 최적화 옵션을 추가하거나 캐시를 정리합니다.
RUN npm install --production && npm cache clean --force

# 4. Copy project files
COPY . .

# 5. Environment variables
ENV PORT=3000
ENV NODE_ENV=production

# 6. Expose port
EXPOSE 3000

# 7. Execution command
CMD ["node", "app.js"]
