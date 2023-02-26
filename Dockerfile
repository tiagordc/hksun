FROM python:3.11
ENV PYTHONUNBUFFERED 1
RUN mkdir /app
WORKDIR /app
RUN pip install --upgrade pip
RUN pip install huawei-solar==2.2.4
COPY app.py /app
CMD [ "python", "-u", "app.py" ]
