FROM python:3.7.10

ARG KUBECTL_VERSION=v1.16.6
ENV WORKSPACE /src/rancher-validation
WORKDIR $WORKSPACE
ENV PYTHONPATH /src/rancher-validation


COPY [".", "$WORKSPACE"]

RUN wget https://storage.googleapis.com/kubernetes-release/release/$KUBECTL_VERSION/bin/linux/amd64/kubectl && \
    mv kubectl /bin/kubectl && \
    chmod +x /bin/kubectl  && \
    cd /tmp && \
    wget -q https://bitbucket.org/ariya/phantomjs/downloads/phantomjs-1.9.8-linux-x86_64.tar.bz2 && \
    tar -xjf phantomjs-1.9.8-linux-x86_64.tar.bz2 && \
    cp phantomjs-1.9.8-linux-x86_64/bin/phantomjs /usr/local/bin/phantomjs && \
    rm -rf phantomjs-* && \
    cd /tmp && \
    cd $WORKSPACE && \
    pip install --upgrade pip && \
    pip install -r tests/v2_validation/requirements.txt