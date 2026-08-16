# MRFHelper

MRFHelper 用于参数化生成钢框架的 OpenSees 二维平面模型，可用于时程分析、Pushover 分析等。模型统一采用 N、mm、t 单位制。

# 安装
- 运行项目根目录下 `main.py`
- 或通过 PyPI 安装：`pip install mrfhelper`

# 使用
`MRFHelper` 核心模块和示例代码使用 PEP 8 命名：模块、函数和对象属性采用 `snake_case`，类采用 `PascalCase`。为保持现有分析流程兼容，`subroutines` 目录及生成的 Python/Tcl 模型脚本仍沿用原有名称和格式。原有四步式输入接口的旧名称也继续作为兼容别名保留。可以从程序生成的 JSON 文件恢复模型：

```python
from MRFHelper import from_json

frame = from_json("model.json")
files = frame.generate_scripts("output")
```

手动定义模型时建议使用 `frame.building_geometry`、`frame.structural_components`、`frame.load_and_material` 和 `frame.connection_and_boundary`。旧写法 `frame.BuildingGeometry` 等仍然可用。

`generate_tcl_script` 返回各输出文件的路径。默认覆盖同名结果；若需保护已有文件，可传入 `overwrite=False`。绘图窗口默认不弹出，需要交互查看时可传入 `show_plot=True`。

# 建模方法
基于二维平面杆系模型建立钢框架 OpenSees 模型，可考虑构件的集中塑性变形和节点域剪切变形。梁、柱采用弹性梁柱单元，端部塑性铰采用改进 IMK 本构，节点域采用 Hysteretic 本构，并通过虚拟柱考虑重力框架的 P-Delta 效应。

