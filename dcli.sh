#docker run -it --rm -p 5000:5000 --entrypoint /bin/bash -v $PWD:/train reporting_obligation_app
docker run -it -p 5004:5004 -v $PWD:/train reporting_obligation_app