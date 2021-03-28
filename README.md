Bilibili 全自动录播上传脚本
======

### 功能

* 自动录制直播，弹幕，和礼物（来自：[B站录播姬](https://github.com/Bililive/BililiveRecorder)）
* 直播结束立刻上传先行版视频（只要你网速够快，就几乎不可能撞车）
* 视频审核通过自动评论高能位置和醒目留言
* 自动根据弹幕和礼物密度检测直播高能区域
* 压制带有高能进度条，弹幕的视频（部分 Nvidia GPU 支持 nvenc 加速）
* 自动用换源方法更新高能弹幕版的视频
* 生成醒目留言字幕（但是上传目前是手动的）

### 例子

以下两个账号主要都是用这个脚本上传的：[@熊卡录播 bot](https://space.bilibili.com/1576916333) 和 [@460 录播 bot](https://space.bilibili.com/75980004)

### 使用方法

文件夹设置：
1. 建一个空文件夹
2. 里面放入 `upload-task.yaml` 和 `comment-task.yaml` 。
   这两个文件是用于记录已经上传的录播和上传未审核的录播所需要发的评论的。
3. 放入 `config.json` ，可以根据 `config.example.json` 改。
   注意不要改 46 行的 webhook 。根据你需要录制的直播间填写。
4. 放入 `bilibili-config.yaml` 可以根据 `bilibili-config.example.yaml` 改。
   填入 `sessdata` 和 `bili_jct` 两项，可以参考 [Passkou/bilibili-api](https://github.com/Passkou/bilibili-api#获取-sessdata-和-csrf) ，
   填入需要上传的直播间号，注意要用长号，例如 128308 ，而不是短号，比如 261 。

文件夹设置完的目录结构如下：
```
${录制目标文件夹}
 |-- upload-task.yaml
 |-- comment-task.yaml
 |-- config.json
 `-- bilibili-config.yaml
```

使用 docker 运行脚本：

1. 安装 docker （已经安装的跳过这一步）：https://docs.docker.com/get-docker/
2. 运行 docker 镜像：

   有 GPU：`sudo docker run -d --restart=always --gpus all -e NVIDIA_DRIVER_CAPABILITIES=video,compute,utility --name auto-bilibili-recorder -v ${录制目标文件夹}:/storage valkjsaaa/auto-bilibili-recorder:2.4b`

   无 GPU：`sudo docker run -d --restart=always --name auto-bilibili-recorder -v ${录制目标文件夹}:/storage valkjsaaa/auto-bilibili-recorder:2.4b`
3. 停止录播：

   `sudo docker rm -f auto-bilibili-recorder`


*使用请注明脚本来自 [@熊卡录播 bot](https://space.bilibili.com/1576916333)*
   

### 测试过的环境

如果不需要显卡加速转码，应该只要是 x64 环境就可以。我的 docker 版本是 `Docker version 20.10.3, build 48d30b5` 。
显卡加速要求比较苛刻，我自己使用的录播机用的 Ubuntu 18.04.5 LTS 、GTX 980 Ti 和 Driver Version: 450.102.04 。
