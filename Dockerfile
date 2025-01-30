FROM pytorch/pytorch:1.13.1-cuda11.6-cudnn8-runtime
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN apt-get update && apt-get install ffmpeg libsm6 libxext6 -y
# Configurar la zona horaria
ENV TZ=Europe/Madrid
RUN ln -sf /usr/share/zoneinfo/Europe/Madrid /etc/localtime && echo "Europe/Madrid" > /etc/timezone
WORKDIR /src/
