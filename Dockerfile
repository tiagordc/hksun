FROM python:3.11
ENV PYTHONUNBUFFERED 1
RUN mkdir /app
WORKDIR /app
RUN pip install --upgrade pip
RUN pip install huawei-solar==2.2.4
RUN pip install quart==0.18.3
COPY app.py /app
HEALTHCHECK --interval=30s --timeout=3s CMD curl -f http://localhost:5000 || exit 1
EXPOSE 5000
CMD [ "quart", "run", "--host", "0.0.0.0", "--port", "5000"]
