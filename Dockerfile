FROM python:3.10-slim AS compile-image
RUN apt-get update
RUN apt-get install -y --no-install-recommends build-essential gcc wget

# Make sure we use the virtualenv:
RUN python -m venv /opt/devenv
ENV PATH="/opt/devenv/bin:$PATH"

RUN pip install --upgrade pip

RUN pip install py-cord
RUN pip install python-dotenv

FROM python:3.10-slim AS build-image
COPY --from=compile-image /opt/devenv /opt/devenv

# Make sure we use the virtualenv:
ENV PATH="/opt/devenv/bin:$PATH"
ENV LD_LIBRARY_PATH="/opt/devenv/lib"

CMD ["bash"]