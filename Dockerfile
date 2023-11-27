FROM python:3.11-slim

ADD requirements.txt /
RUN pip install -r requirements.txt

ADD get-settings.py /
ADD main.py /

CMD ["python", "main.py"]