# Auto bilibili live recording server
#
# VERSION               0.0.1

FROM nvidia/cuda:11.0-devel-ubuntu20.04

ENV TZ=Asia/Shanghai
ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y wget git apt-transport-https software-properties-common

RUN wget https://packages.microsoft.com/config/ubuntu/20.04/packages-microsoft-prod.deb -O packages-microsoft-prod.deb
RUN dpkg -i packages-microsoft-prod.deb

RUN add-apt-repository universe

RUN apt-get update && apt-get install -y dotnet-sdk-5.0 powershell


RUN ln -s /usr/bin/pwsh /usr/bin/powershell

RUN git clone https://github.com/valkjsaaa/BililiveRecorder.git

WORKDIR "/BililiveRecorder"

RUN git checkout 7291d30d57a70ae4262d5d95bd1d07ac48949e3d
RUN dotnet build BililiveRecorder.Cli/BililiveRecorder.Cli.csproj -c Release

#ENTRYPOINT BililiveRecorder/BililiveRecorder.Cli/bin/Release/netcoreapp3.1/BililiveRecorder.Cli

WORKDIR "/"

RUN apt-get update && apt-get install -y cmake

RUN git clone https://github.com/valkjsaaa/DanmakuFactory.git

WORKDIR "/DanmakuFactory"

RUN git checkout 8d376672da6346dd9da91738d9b6232d5d9a37cf
RUN mkdir temp

RUN make -f makefile_64

RUN apt-get update && apt-get install -y python3 python3-pip

WORKDIR "/webhook"

COPY *.py .

COPY requirements.txt .

RUN pip3 install -r requirements.txt

#ENTRYPOINT /bin/bash

WORKDIR "/"
RUN apt-get update && apt-get install -y dotnet-sdk-3.1 ffmpeg fonts-noto-color-emoji fonts-noto-cjk-extra

RUN ln -s /usr/local/cuda/lib64/stubs/libcuda.so /usr/local/cuda/lib64/stubs/libcuda.so.1

WORKDIR "/DanmakuProcess"
RUN git clone https://github.com/valkjsaaa/bilibili-danmaku-energy-map.git ./
RUN git checkout 2a4c0dd21ddf32e9e10050ba5391e395aaab8fc7
RUN pip3 install -r requirements.txt

WORKDIR "/storage"
CMD python3 /webhook/process_video.py