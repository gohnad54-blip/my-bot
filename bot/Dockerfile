FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -r bot/requirements.txt
CMD ["python", "bot/bot.py"]