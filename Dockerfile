# Auto bilibili live recording server
#
# VERSION               0.0.1
ARG COMMON_IMAGE=nvidia/cuda:11.0-devel-ubuntu20.04
FROM ${COMMON_IMAGE}

ENV TZ=Asia/Shanghai
ARG DEBIAN_FRONTEND=noninteractive


RUN apt-get update && apt-get install -y wget git apt-transport-https software-properties-common
RUN add-apt-repository universe
RUN apt-get update && apt-get install -y wget ffmpeg fonts-noto-color-emoji fonts-noto-cjk-extra cmake python3 python3-pip
RUN update-ca-certificates -f

RUN wget https://packages.microsoft.com/config/ubuntu/20.04/packages-microsoft-prod.deb -O packages-microsoft-prod.deb
RUN dpkg -i packages-microsoft-prod.deb

RUN apt-get update && apt-get install -y dotnet-sdk-5.0 powershell
RUN rm -rf /var/lib/apt/lists/*
RUN if [[ ${COMMON_IMAGE} == *"cuda"* ]] ; then ln -s /usr/local/cuda/lib64/stubs/libcuda.so /usr/local/cuda/lib64/stubs/libcuda.so.1 ; fi

RUN ln -s /usr/bin/pwsh /usr/bin/powershell

RUN git clone https://github.com/valkjsaaa/BililiveRecorder.git && cd BililiveRecorder && git checkout 7bbef299529d46737c8e95424d4f56423d02bf74

WORKDIR "/BililiveRecorder"

RUN dotnet build BililiveRecorder.Cli/BililiveRecorder.Cli.csproj -c Release
RUN dotnet nuget locals all --clear
RUN apt -y remove dotnet-sdk-5.0 powershell

#ENTRYPOINT BililiveRecorder/BililiveRecorder.Cli/bin/Release/netcoreapp3.1/BililiveRecorder.Cli

WORKDIR "/"

RUN git clone https://github.com/valkjsaaa/DanmakuFactory.git && cd DanmakuFactory && git checkout 8d376672da6346dd9da91738d9b6232d5d9a37cf

WORKDIR "/DanmakuFactory"

RUN mkdir temp
RUN make -f makefile_64

#ENTRYPOINT /bin/bash

RUN pip3 install git+https://github.com/valkjsaaa/danmaku_tools.git@4e15a59c907e1927d031c06ad408382d6da6e448

WORKDIR "/webhook"

COPY *.py .
COPY requirements.txt .
RUN pip3 install --upgrade -r requirements.txt
RUN wget https://raw.githubusercontent.com/valkjsaaa/Bilibili-Toolkit/7b86a61214149cc3f790d02d5d06ecd7540b9bdb/bilibili.py


WORKDIR "/storage"
CMD python3 /webhook/process_video.py