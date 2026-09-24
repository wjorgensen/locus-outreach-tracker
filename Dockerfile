FROM python:3.12-slim
WORKDIR /app
COPY mini.py ./
EXPOSE 8080
CMD ["python", "mini.py"]
