Bilibili 全自动录播上传脚本
======

### 功能

* 自动录制直播，弹幕，和礼物（来自：[B站录播姬](https://github.com/Bililive/BililiveRecorder)）
* 直播结束立刻上传先行版视频（只要你网速够快，就几乎不可能撞车）
* 视频审核通过自动评论高能位置和醒目留言
* 自动根据弹幕和礼物密度检测直播高能区域
* 压制带有高能进度条，弹幕的视频（部分 Nvidia GPU 支持 nvenc 加速）
* 自动用换源方法更新高能弹幕版的视频
* 生成并上传醒目留言字幕
* 边录边修大部分录播数据流格式问题（来自 B站录播姬 v1.3)
* 主播意外下播，很快重新上播时会自动拼接
* 只需要一个配置文件
* 高能路牌自动提取最相关的弹幕
* （新）登录时可以指定 HTTP 代理以解决部分 IP 地址无法自动登录的问题
* （新）当主播切换分辨率的时候自动使用更宽、更高清的分辨率
* （新）根据分辨率渲染弹幕，避免竖屏情况下重叠的弹幕

### 例子

以下两个账号主要都是用这个脚本上传的：[@熊卡录播 bot](https://space.bilibili.com/1576916333) 和 [@460 录播 bot](https://space.bilibili.com/75980004)

### 使用方法

文件夹设置：
1. 建一个空文件夹
2. 放入 `recorder_config.yaml`。


文件夹设置完的目录结构如下：
```
${录制目标文件夹}
 `-- recorder_config.yaml
```

模版使用（视频标题和描述可以使用）：
配置文件中的视频标题和描述可以使用[模版语言](https://docs.python.org/3/library/string.html#template-strings) 。包含以下模版：
* `$name`：主播名字
* `$title`：主播直播间名称，以主播下播时的设置为准
* `$uploader_name`：上传者名字，也就是 `account` 里的 `name`
* `$y`：没有前缀0的年份，如 2021 （年）
* `$m`：没有前缀0的月份，如 4 （月）
* `$d`：没有前缀0的日期，如 1 （日）
* `$yy`：有前缀0的年份，如 2021 （年）
* `$mm`：有前缀0的月份，如 04 （月）
* `$dd`：有前缀0的日期，如 01 （日）
* `$HH`：小时
* `$MM`：分钟
* `$SS`：秒
* `$flv_path`：录播文件所对应的相对目录

常见例子：
  `测试【$name】$yy年$mm月$dd日 $title` 会变成 "测试【碳酸熊卡】2021年04月24日 竟是阳间直播人"

使用 docker 运行脚本：

1. 安装 docker （已经安装的跳过这一步）：https://docs.docker.com/get-docker/

   如果想使用 GPU 加速的话，还需要[安装 NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html#setting-up-nvidia-container-toolkit)

   例如，如果是 Ubuntu/Debian 的话，需要：
   ```bash
   distribution=$(. /etc/os-release;echo $ID$VERSION_ID) \
   && curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add - \
   && curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
   
   curl -s -L https://nvidia.github.io/nvidia-container-runtime/experimental/$distribution/nvidia-container-runtime.list | sudo tee /etc/apt/sources.list.d/nvidia-container-runtime.list
   
   sudo apt-get update
   
   sudo apt-get install -y nvidia-docker2
   
   sudo systemctl restart docker
   ```
   
2. 运行 docker 镜像：

   x64/arm64 无 GPU：`sudo docker run -d --restart=always --name auto-bilibili-recorder -v ${录制目标文件夹}:/storage ghcr.io/valkjsaaa/auto-bilibili-recorder:master`

   x64 有 GPU：`sudo docker run -d --restart=always --gpus all -e NVIDIA_DRIVER_CAPABILITIES=video,compute,utility --name auto-bilibili-recorder -v ${录制目标文件夹}:/storage ghcr.io/valkjsaaa/auto-bilibili-recorder-gpu:master`
   
   注：国内用户可以使用 `ghcr.dockerproxy.com` 替换掉 `ghcr.io` 以提升镜像下载速度，如： `ghcr.dockerproxy.com/valkjsaaa/auto-bilibili-recorder-gpu:master`

3. 立即停止录播（会中断正在录制/转码/上传的录播）：

   `sudo docker rm -f auto-bilibili-recorder`


*使用请注明脚本来自 [@熊卡录播 bot](https://space.bilibili.com/1576916333)*
   
### 配置文件 `recorder_config.yaml` 例子 

[简单录播账号](https://github.com/valkjsaaa/auto-bilibili-recorder/blob/master/example_dir/recorder_config.uploader.yaml)

[只录播，不上传](https://github.com/valkjsaaa/auto-bilibili-recorder/blob/master/example_dir/recorder_config.record_only.yaml)

[只录播不上传，支持弹幕相关自定义选项](https://github.com/valkjsaaa/auto-bilibili-recorder/blob/master/example_dir/recorder_config.record_only_customize.yaml)

[多个直播间，多个账号](https://github.com/valkjsaaa/auto-bilibili-recorder/blob/master/example_dir/recorder_config.multi_uploader.yaml)

[用户名密码登陆，使用代理（目前暂时不可用）](https://github.com/valkjsaaa/auto-bilibili-recorder/blob/master/example_dir/recorder_config.password_proxy.yaml)


### 测试过的环境

如果不需要显卡加速转码，应该只要是 x64 环境就可以。我的 docker 版本是 `Docker version 20.10.3, build 48d30b5` 。
显卡加速要求比较苛刻，我自己使用的录播机用的 Ubuntu 18.04.5 LTS 、GTX 980 Ti 和 Driver Version: 450.102.04 。
