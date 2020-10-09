FROM python:3.8-alpine
ADD server /app/server
ADD setup.py /app
WORKDIR /app
RUN pip install gunicorn flask
RUN python setup.py install
ENTRYPOINT ["gunicorn", "--log-level=info", "-b", "0.0.0.0:8000", "server:app"]
