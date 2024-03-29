# Auto bilibili live recording server
#
# VERSION               0.0.1
ARG COMMON_IMAGE=nvidia/cuda:12.1.0-devel-ubuntu22.04
FROM ${COMMON_IMAGE}

ENV TZ=Asia/Shanghai
ARG DEBIAN_FRONTEND=noninteractive


RUN apt-get update && apt-get install -y wget git apt-transport-https software-properties-common
RUN add-apt-repository universe
RUN apt-get update && apt-get install -y wget ffmpeg fonts-noto-color-emoji fonts-noto-cjk-extra cmake python3 python3-pip curl unzip
RUN update-ca-certificates -f

RUN apt-get update && apt-get install -y libc6 libgcc1 libgssapi-krb5-2 libicu70 libssl3 libstdc++6 zlib1g

#RUN wget https://github.com/PowerShell/PowerShell/releases/download/v7.1.5/powershell-7.1.5-linux-arm64.tar.gz -O powershell.tar.gz
#RUN mkdir -p /opt/pwsh
#RUN tar -xvzf powershell.tar.gz -C /opt/pwsh
#
#RUN wget https://dot.net/v1/dotnet-install.sh
#RUN bash ./dotnet-install.sh -c 8.0

RUN [ "/bin/bash", "-c", "if [[ ${COMMON_IMAGE} == *'cuda'* ]] ; then ln -s /usr/local/cuda/lib64/stubs/libcuda.so /usr/local/cuda/lib64/stubs/libcuda.so.1 ; fi" ]

#RUN ln -s /opt/pwsh/pwsh /usr/bin/powershell
#RUN ln -s /root/.dotnet/dotnet /usr/bin/dotnet
#
#RUN git clone https://github.com/BililiveRecorder/BililiveRecorder.git BililiveRecorder-src && cd BililiveRecorder-src && git checkout v2.11.0
#
#WORKDIR "/BililiveRecorder-src"
#
#RUN dpkgArch="$(uname -m)" && echo "Detected architecture: $dpkgArch" ; \
#    case "$dpkgArch" in \
#        aarch64) export RID='linux-arm64' && echo "Setting RID to 'linux-arm64'" ;; \
#        x86_64) export RID='linux-x64' && echo "Setting RID to 'linux-x64'" ;; \
#        *) export RID='linux-x64' && echo "Setting default RID to 'linux-x64'" ;; \
#    esac; \
#    cd BililiveRecorder.Cli && dotnet build -o /BililiveRecorder -c Release -r $RID
#
#
#RUN dotnet nuget locals all --clear
#RUN rm -rf /opt/pwsh
#RUN rm -rf /root/.dotnet

# Download from GitHub release
RUN dpkgArch="$(uname -m)" && \
    echo "Detected architecture: $dpkgArch" && \
    case "$dpkgArch" in \
        aarch64) \
            URL='https://github.com/BililiveRecorder/BililiveRecorder/releases/download/v2.11.0/BililiveRecorder-CLI-linux-arm64.zip' \
            ;; \
        x86_64) \
            URL='https://github.com/BililiveRecorder/BililiveRecorder/releases/download/v2.11.0/BililiveRecorder-CLI-linux-x64.zip' \
            ;; \
        *) \
            echo "Unsupported architecture: $dpkgArch" && exit 1 \
            ;; \
    esac && \
    echo "Downloading BililiveRecorder CLI from $URL" && \
    curl -L $URL -o /tmp/bililive_recorder.zip && \
    unzip /tmp/bililive_recorder.zip -d /BililiveRecorder && \
    rm /tmp/bililive_recorder.zip

WORKDIR "/"

RUN git clone https://github.com/hihkm/DanmakuFactory.git && cd DanmakuFactory && git checkout d994828fa3bb39c06e625062faadf5a8850abeaf

WORKDIR "/DanmakuFactory"

RUN mkdir temp
RUN make -f makefile

#ENTRYPOINT /bin/bash

RUN pip3 install git+https://github.com/valkjsaaa/danmaku_tools.git@c7d86d10f157066ca24196b4222d9ef291e8e78e

WORKDIR "/usr/local/bin"

RUN wget https://raw.githubusercontent.com/keylase/nvidia-patch/2d31a42d8da0050a63d4f466ddd1244321e2ef52/patch.sh && \
    wget https://raw.githubusercontent.com/keylase/nvidia-patch/2d31a42d8da0050a63d4f466ddd1244321e2ef52/docker-entrypoint.sh && \
    chmod +x patch.sh && \
    chmod +x docker-entrypoint.sh

WORKDIR "/webhook"

COPY requirements.txt .
RUN pip3 install --upgrade -r requirements.txt
RUN wget https://raw.githubusercontent.com/valkjsaaa/Bilibili-Toolkit/7b86a61214149cc3f790d02d5d06ecd7540b9bdb/bilibili.py

COPY *.py ./

WORKDIR "/storage"
ENV PYTHONUNBUFFERED=1
CMD /usr/local/bin/docker-entrypoint.sh python3 -u /webhook/process_video.py
