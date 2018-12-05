FROM fedora:22

LABEL Description = "product-definition-center"
LABEL Vendor = "Red Hat"
LABEL Version = "0.5"

RUN dnf upgrade -y && dnf clean all

# patternfly1
RUN curl -L https://copr.fedoraproject.org/coprs/patternfly/patternfly1/repo/fedora-22/patternfly-patternfly1-fedora-22.repo > \
            /etc/yum.repos.d/patternfly-patternfly1-fedora-22.repo
RUN curl -L http://www.graphviz.org/graphviz-rhel.repo > /etc/yum.repos.d/graphviz-rhel.repo

# install dependencies
RUN dnf install -y \
        rpm-build \
        sudo \
        passwd \
        tar \
        git \
        make \
        gcc \
        libuuid-devel \
        python-devel \
        python-setuptools \
        python-pip swig \
        openldap-devel \
        krb5-devel \
        koji \
        patternfly1 \
        vim-enhanced \
        'graphviz*' \
        libxml2 \
        libxslt \
        libxml2-devel \
        libxslt-devel \
        net-tools \
        zsh  \
        lsof \
        strace \
        nc  \
        less \
        curl && \
    dnf clean all

RUN pip install --upgrade pip

# create user in the container with the same name and id as the user building
# the image

ARG user
ARG user_id

RUN useradd -u $user_id $user && \
    usermod -aG wheel $user && \
    echo "$user ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers && \
    echo "Defaults:$user !requiretty" >> /etc/sudoers

COPY . /code
RUN chown -R $user:$user /code

USER $user
WORKDIR /code

RUN git reset --hard && \
    git clean -qdffx && \
    pip install --user -r requirements/devel.txt; \
    cp src/pdc/pdc/settings_local.py.dist src/pdc/pdc/settings_local.py && \
    sed -e 's/^DEBUG = .*/DEBUG = True/g' -i src/pdc/pdc/settings_local.py && \
    ./sync.sh && \
    python manage.py migrate

EXPOSE 8000

CMD ["make", "run"]
