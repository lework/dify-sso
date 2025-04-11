# ---- 运行环境 ----
FROM python:3.11-alpine AS running

ENV LANG='en_US.UTF-8' \
    LANGUAGE='en_US.UTF-8' \
    TZ='Asia/Shanghai' \
    PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/

RUN \
    sed -i 's/dl-cdn.alpinelinux.org/mirrors.aliyun.com/g' /etc/apk/repositories \
    && apk --update -t --no-cache add tzdata libpq \
    && ln -snf /usr/share/zoneinfo/${TZ} /etc/localtime \
    && echo "${TZ}" > /etc/timezone \
    && apk add --no-cache --virtual .build-deps gcc python3-dev musl-dev postgresql-dev \
    && pip install --upgrade pip \
    && pip install --no-cache-dir psycopg2 \
    && apk del --no-cache .build-deps

WORKDIR /app

# 下载依赖
COPY requirements.txt .
RUN --mount=type=cache,id=pip,target=/root/.cache \
  pip install -r requirements.txt

# 拷贝代码
COPY . .

CMD ["python", "-m", "app.main"]