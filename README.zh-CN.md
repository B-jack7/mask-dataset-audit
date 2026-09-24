# Mask Dataset Audit：分割数据集检查工具

[English](README.md) · [一键 Colab 示例](https://colab.research.google.com/github/B-jack7/mask-dataset-audit/blob/main/notebooks/quickstart.ipynb)

训练前检查图像和 PNG 掩码，输出可离线打开的 HTML 报告及 JSON。检查配对缺失、尺寸不一致、异常标签、损坏文件，以及训练/验证/测试集之间像素完全相同的图片。只读原数据，不需要 GPU，不上传图片。

```bash
git clone https://github.com/B-jack7/mask-dataset-audit.git
cd mask-dataset-audit
python -m pip install .
python examples/make_demo.py demo-data
mask-dataset-audit demo-data --labels 0,1 --out demo-report
```

打开 `demo-report/report.html`。合成示例故意埋入四个错误，所以命令返回 **1 是预期行为**。重跑时请选择新的数据和报告目录。

真实数据结构为 `数据集/train/images/`、`数据集/train/masks/`，以及对应的 `val`、`test`。按目录内的相对路径和文件名（去掉扩展名）配对。支持嵌套子目录。

```bash
mask-dataset-audit ./dataset --labels 0,1,2 --ignore 255 --out ./report
```

- `--labels` 指定真实类别值；`--ignore` 单独计数，绝不会偷偷当成背景。
- 只有训练集和验证集时，加 `--splits train,val`。
- 掩码必须是整数标签 PNG，支持调色板索引及 16 位标签，不支持 RGB 彩色掩码自动映射。
- 返回码：0 无错误（可能有警告）；1 检出数据错误且已写报告；2 配置或执行失败。
- 输出目录必须新建且在数据集之外，避免覆盖文件。

**相同像素检测不能证明患者级划分正确。** 同一患者不同切片、缩放或裁剪后的重复图片不会被这项检查识别。工具不判断标注质量、医学有效性或数据真实性。报告含文件名，分享前请自行检查。

详细格式、限制与开发方法见英文 README。
