FROM python:3.7-alpine
ADD server /app/server
ADD setup.py /app
WORKDIR /app
RUN pip install gunicorn Flask
RUN python setup.py install
CMD ["gunicorn", "--log-level=info", "-b", "0.0.0.0:8000", "server:app"]
