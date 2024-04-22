docker build -t relieph-image .
docker run --name relieph-dev -p 8000:80 relieph-image
docker container logs relieph-dev
