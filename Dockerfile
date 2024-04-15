# 
FROM python:3.11


# 
WORKDIR /code


# 
COPY ./requirements.txt /code/requirements.txt

# 
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# 
COPY ./trains /code/app

#
ENV PYTHONPATH=/code/app

# 
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "--workers", "4", "--bind", "0.0.0.0:8000", "app.main:app"]
