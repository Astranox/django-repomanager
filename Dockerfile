FROM docker.io/python:3.10-slim
# set environment variables
ENV LANG=C.UTF-8 LC_ALL=C.UTF-8 PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH='.'

# set work directory
WORKDIR /usr/src/app

# Tell apt-get we're never going to be able to give manual
# feedback:
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get -y upgrade && rm -rf /var/lib/apt/lists/*

# install dependencies
COPY ./requirements.txt .
#RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# lint
# E121 continuation line under-indented for hanging indent
# E123 closing bracket does not match indentation of opening bracket's line
# E126 continuation line over-indented for hanging indent
# E261 two spaces before inline comment
# F405 star imports
#RUN pip install --no-cache-dir flake8 && flake8 --ignore=E121,E123,E126,E261,E501,F401,F403,F405 .

EXPOSE 8000

# run entrypoint.sh
ENTRYPOINT ["/usr/src/app/entrypoint.sh"]
