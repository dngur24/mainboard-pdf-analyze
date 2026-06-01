# 1. Base image
# slim 버전에서 빌드 도구 부족으로 인한 오류를 방지하기 위해 전체 이미지를 사용합니다.
FROM node:24

# 2. Set working directory
WORKDIR /app

RUN git clone https://github.com/dngur24/mainboard-pdf-analyze.git && cd mainboard-pdf-analyze


# RUN cd 
# 3. Copy package files and install dependencies
COPY package*.json ./

# 4. Copy project files
COPY . .

RUN npm install

# 5. Environment variables
ENV PORT=3000
ENV NODE_ENV=production

# 6. Expose port
EXPOSE 3000

# 7. Execution command
CMD ["node", "app.js"]
