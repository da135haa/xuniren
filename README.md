# 虚拟人说话头生成(NeRF 虚拟人实时驱动)--尽情打造自己的 call annie 吧

![](/img/example.gif)

xuniren windows 安装教程：[一步步教学在 Windows 下面安装 pytorch3d 来部署 xuniren 这个项目 - 坤坤 - 博客园 (cnblogs.com)](https://www.cnblogs.com/dm521/p/17469967.html)

模型训练教程：[(278 条消息) xuniren（Fay 数字人开源社区项目）NeRF 模型训练教程\_郭泽斌之心的博客-CSDN 博客](https://blog.csdn.net/aa84758481/article/details/131135823)

# Get Started

## Installation

Tested on Ubuntu 22.04, Pytorch 1.12 and CUDA 11.6，or Pytorch 1.12 and CUDA 11.3

```python
git clone https://github.com/waityousea/xuniren.git
cd xuniren
```

### Install dependency

```python
# for ubuntu, portaudio is needed for pyaudio to work.
sudo apt install portaudio19-dev

pip install -r requirements.txt
or
## environment.yml中的pytorch使用的1.12和cuda 11.3
conda env create -f environment.yml
## install pytorch3d
#ubuntu/mac
pip install "git+https://github.com/facebookresearch/pytorch3d.git"
```

**windows 安装 pytorch3d**

- gcc & g++ ≥ 4.9

在 windows 中，需要安装 gcc 编译器，可以根据需求自行安装，例如采用 MinGW

以下安装步骤来自于[pytorch3d](https://github.com/facebookresearch/pytorch3d/blob/main/INSTALL.md)官方, 可以根据需求进行选择。

```python
conda create -n pytorch3d python=3.9
conda activate pytorch3d
conda install pytorch=1.13.0 torchvision pytorch-cuda=11.6 -c pytorch -c nvidia
conda install -c fvcore -c iopath -c conda-forge fvcore iopath
```

对于 CUB 构建时间依赖项，仅当您的 CUDA 早于 11.7 时才需要，如果您使用的是 conda，则可以继续

```
conda install -c bottler nvidiacub
```

```
# Demos and examples
conda install jupyter
pip install scikit-image matplotlib imageio plotly opencv-python

# Tests/Linting
pip install black usort flake8 flake8-bugbear flake8-comprehensions
```

任何必要的补丁后，你可以去“x64 Native Tools Command Prompt for VS 2019”编译安装

```
git clone https://github.com/facebookresearch/pytorch3d.git
cd pytorch3d
python setup.py install
```

### Build extension

By default, we use [`load`](https://pytorch.org/docs/stable/cpp_extension.html#torch.utils.cpp_extension.load) to build the extension at runtime. However, this may be inconvenient sometimes. Therefore, we also provide the `setup.py` to build each extension:

```
# install all extension modules
# notice: 该模块必须安装。
# 在windows下，建议采用vs2019的x64 Native Tools Command Prompt for VS 2019命令窗口安装
bash scripts/install_ext.sh(建议复制出来单独安装)
```

### **start(独立运行)**

环境配置完成后，启动虚拟人生成器：

```python
python app.py
```

### **start（对接 fay，在 ubuntu 20.04 及 windows10 下完成测试）**

环境配置完成后，启动 fay 对接脚本(无须启动 app.py)

```python
python fay_connect.py
```

![](img/weplay.png)

扫码支助开源开发工作，凭支付单号入 qq 交流群

接口的输入与输出信息 [Websoket.md](https://github.com/waityousea/xuniren/blob/main/WebSocket.md)

虚拟人生成的核心文件

```python
## 注意，核心文件需要单独训练
.
├── data
│   ├── kf.json
│   ├── pretrained
│   └── └── ngp_kg.pth

```

### Inference Speed

在台式机 RTX A4000 或笔记本 RTX 3080ti 的显卡（显存 16G）上进行视频推理时，1s 可以推理 35~43 帧，假如 1s 视频 25 帧，则 1s 可推理约 1.5s 视频。

# Acknowledgement

- The data pre-processing part is adapted from [AD-NeRF](https://github.com/YudongGuo/AD-NeRF).
- The NeRF framework is based on [torch-ngp](https://github.com/ashawkey/torch-ngp).
- The algorithm core come from [RAD-NeRF](https://github.com/ashawkey/RAD-NeRF).
- Usage example [Fay](https://github.com/TheRamU/Fay).

学术交流可发邮件到邮箱：waityousea@126.com

---

目標聲音資源
data/audio/aud\_%d.wav
依照目標音源產生出來的 cuda 資料,用於生成對嘴影片
data/audio/aud\_%d*eo.npy
eo.npy 生成的對嘴無聲影片
data/video/results/ngp*%d.mp4
將目標聲音源+對嘴影片合併後,生成的最終影片
data/video/results/output\_%d.mp4
