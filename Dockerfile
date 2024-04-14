# use python 3.11 image
FROM python:3.11

# copy source file to /app
COPY ./src /app/src

# set working directory to docker
WORKDIR /app/src

# install packages
RUN pip install --no-cache-dir --upgrade -r /app/src/requirements.txt
RUN pip install fastapi uvicorn

# expose port 8000 to be used to received requests
EXPOSE 8000

# run application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "80", "--reload"]