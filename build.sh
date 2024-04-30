docker build -t relieph-image .
# docker run --name relieph-dev -d -p 8000:80 relieph-image
docker run --name relieph-dev -d -p 8000:80 relieph-image
docker container logs relieph-dev
