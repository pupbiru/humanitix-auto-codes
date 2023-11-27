FROM python:3.10-slim

WORKDIR /app
ADD requirements.txt /app
RUN pip install -r requirements.txt

ADD get-settings.py /app
ADD main.py /app

CMD ["python", "main.py"]