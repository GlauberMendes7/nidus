# ------------------------------------------------------------------------------

# FROM nvcr.io/nvidia/pytorch:21.09-py3 AS build
# FROM powerapi/powerapi:2.1.0 AS build
FROM python:3.10-slim AS build


# RUN echo "deb https://deb.debian.org/debian stable main" > /etc/apt/sources.list
# RUN apt update && apt upgrade -y && apt autoremove -y
# RUN apt install -y --no-install-recommends build

RUN python3 -m venv /tmp/.venv

ENV PATH="/tmp/.venv/bin:${PATH}"
# RUN source /tmp/.venv/bin/activate

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade -r requirements.txt

# RUN pip install --no-cache-dir --upgrade pip

# ------------------------------------------------------------------------------

# FROM nvcr.io/nvidia/pytorch:21.09-py3
# FROM powerapi/powerapi:2.1.0
FROM python:3.10-slim

COPY --from=build /tmp/.venv /app/.venv

WORKDIR /app/

COPY nidus /app/nidus/

ENTRYPOINT ["/app/nidus/./entrypoint.sh"]
