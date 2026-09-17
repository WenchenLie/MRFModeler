# MRFHelper

MRFHelper 用于参数化生成 OpenSees 二维规则平面框架模型，支持钢框架 `Frame` 和钢筋混凝土框架 `RCFrame`，可输出 Tcl 与 OpenSeesPy 脚本，并与 OpenSAS 的时程、IDA、Pushover、循环 Pushover 及后处理流程衔接。模型统一采用 N、mm、t 单位制。

## 安装

- 运行项目根目录下 `main.py`。
- 或通过 PyPI 安装：`pip install mrfhelper`。

开发和 OpenSeesPy 集成测试使用 Python 3.12；当前 `.venv` 为 Python 3.12，且测试依赖中包含 OpenSeesPy。可用 `uv sync --python .venv/Scripts/python.exe --extra test` 重建同样的环境。

当前 MRFHelper 程序版本暂固定为 `2.6`。

## 通用接口

`Frame` 和 `RCFrame` 的模块、函数、对象属性及 JSON 字段统一使用当前的 `snake_case` 名称，类使用 `PascalCase`。旧版 CamelCase、拼写错误及兼容入口已移除。

```python
from MRFHelper import from_json

frame = from_json("model.json")
files = frame.generate_scripts("output")
```

`from_json()` 根据 JSON 中的 `frame_type` 返回 `Frame` 或 `RCFrame`；钢框架未设置该字段时按钢框架读取。`generate_scripts()` 返回全部输出文件路径，默认覆盖同名结果；传入 `overwrite=False` 可拒绝覆盖，传入 `show_plot=True` 可显示框架立面图。两类框架均生成自包含 HTML 建模报告，包含模型信息、构件布置、截面示意、截面特性与屈服弯矩。

## 钢筋混凝土框架

完整示例见 [examples/RCMRF_2s.py](examples/RCMRF_2s.py)，配筋表见 [examples/RCMRF_2s_sections.csv](examples/RCMRF_2s_sections.csv)，JSON 输入示例见 [examples/RCMRF_2s.json](examples/RCMRF_2s.json)。在源码目录运行示例时使用：

```powershell
python examples/RCMRF_2s.py
```

RC 模型采用 `elasticBeamColumn + zeroLength IMKPeakOriented + Joint2D`：梁柱中段为有效刚度弹性单元，端部为集中塑性铰，节点域使用 Joint2D。梁柱弹性段与塑性铰按 `n=10` 作串联刚度修正。梁柱统一调用 `RCHinge`，传入材料、截面、上下层与侧面配筋率、箍筋率、轴压比、构件长度和程序计算的 EI 折减系数；子程序内部参照 `ModSpring_IMK_RC.tcl` 计算正负向 IMK 参数。其中纵筋率和传入子程序的轴压比按毛截面 `b·h` 定义，子程序会按正负弯曲方向的有效高度换算；最后一个方向参数用于交换两端铰的正负弯矩方向。节点、构件和塑性铰编号沿用钢框架规则及 `doc/Notation.pdf`。

RC 材料需显式定义：

```python
from MRFHelper import RCFrame

frame = RCFrame("RC_2S2B")
# 完成几何定义后：
frame.structural_components.load_sections_csv("sections.csv")
frame.structural_components.set_beams(2, ["S250x500", "S250x500"])
frame.structural_components.set_beams(3, ["S250x500", "S250x500"])
frame.structural_components.set_columns(1, ["S350x350"] * 3)
frame.structural_components.set_columns(2, ["S300x300"] * 3)

# 用户直接输入各楼层节点质量 [t] 与竖向荷载 [N]；竖向荷载向下为正。
frame.load_and_material.set_masses(
    moment_frame=[[7.5, 15.0, 7.5], [7.0, 14.0, 7.0]],
    leaning_column=[2.1, 1.0],
)
frame.load_and_material.set_loads(
    moment_frame=[[73500, 147000, 73500], [68000, 136000, 68000]],
    leaning_column=[20700, 9900],
)

frame.load_and_material.set_material(
    fc_expected=40,
    ec=30000,
    fy_expected=460,
    es=200000,
    poisson_ratio=0.2,
)
# 考虑倾覆力矩使柱轴压比放大 25%；不改变实际施加的重力荷载与质量。
frame.load_and_material.set_axial_load_ratio_amplification_factor(1.25)
```

程序不再根据面荷载、组合系数或建筑面积计算和分配荷载、质量。`moment_frame` 的行数和 `leaning_column` 的长度必须等于结构层数，索引顺序自动对应楼层 `2..N+1`；`moment_frame` 每行按轴线从左至右排列，长度等于框架轴线数。质量单位为 t，竖向荷载单位为 N，且两者均须为非负有限数；生成 OpenSees 重力荷载时程序自动把向下幅值转换为负 Y 方向。柱轴压比仅累计抗弯框架节点的竖向荷载，虚拟柱荷载不计入抗弯框架柱轴力。

`fc_expected` 和 `fy_expected` 均为期望强度。`axial_load_ratio_amplification_factor` 必须不小于 `1.0`，仅放大用于柱铰、RC 柱有效刚度和 RC 节点域计算的柱轴力；不会改变用户输入并实际施加的竖向荷载或质量。钢框架和 RC 框架的默认值均为 `1.25`。有效刚度不再由用户输入：梁的 `EIy/EIg` 固定为 `0.3`；每根柱先按放大后的轴压比计算 `0.75 × (0.1 + PPy)^0.8`，再将结果限制在 `0.2–0.6`，其中 `PPy = 放大系数 × P/(b·h·fc)`。

### 配筋 CSV

CSV 每行定义一个截面，长度单位均为 mm。必需列如下：

| 列名 | 含义 |
|---|---|
| `section_name` | 任意非空的唯一截面名；梁柱类别由后续截面设置方法确定 |
| `b`, `h` | 截面宽度和高度 |
| `cover` | 混凝土表面至箍筋外缘的净保护层 |
| `top_corner`, `top_inner` | 上部角点筋和上部内侧筋 |
| `bottom_corner`, `bottom_inner` | 下部角点筋和下部内侧筋 |
| `side_each` | 每个侧面的纵筋 |
| `stirrup` | 箍筋；数量表示有效箍筋肢数 |
| `stirrup_spacing` | 箍筋间距 |

CSV 不包含 `section_type` 列，截面名称可以是任意非空字符串；梁柱类别由 `set_beams()` 或 `set_columns()` 的调用位置确定。可选列 `bond_slip` 取 0 或 1，默认 1。钢筋采用 `数量D直径`，例如 `2D25`；空值或 `0` 表示无钢筋。顶层或底层存在两排钢筋时用 `+` 从混凝土表面向内依次连接，例如 `2D22+2D20` 表示两排内侧筋。相邻排净距按 `max(25 mm, 前排直径, 当前排直径)` 计算。程序会校验缺列、重复名称、非法钢筋规格、保护层或钢筋排越界及未定义截面引用。

RC JSON 是与 Python 参数定义对应的输入配置，只保存 `section_csv` 路径、梁柱截面名称、几何、节点质量、节点竖向荷载、材料和边界配置，不再嵌入截面尺寸、配筋、已解析节点域材料或 IMK 派生参数。CSV 是必要输入；相对路径按 JSON 文件所在目录解析。

### Joint2D 节点域

用户可在完成材料输入后选择三种节点域模型：

```python
frame.connection_and_boundary.set_joint_panel_model("Elastic")
frame.connection_and_boundary.set_joint_panel_model("Rigid", stiffness_factor=1000)
frame.connection_and_boundary.set_joint_panel_model(
    "MCFT",
    steel_hardening_ratio=0.01,
    maximum_aggregate_size=20,
    horizontal_axial_force=0,
)
```

`Elastic` 使用 `G·b_j·h_c·h_b` 作为 Joint2D 中心转动弹簧刚度，其中 `G=Ec/[2(1+ν)]`；`Rigid` 使用相同表达式再乘 `stiffness_factor`。两者均采用 OpenSees `Elastic` 材料。默认模式为 `Elastic`。

`MCFT` 按 Altoontash 论文第 4.2.1 节、式 (4.1)–(4.33)，在生成模型时由 `MRFHelper/rc_mcft.py` 逐步增加剪切应变，迭代满足节点域水平与竖向正应力平衡，并检查裂缝面钢筋屈服、混凝土压碎和裂缝滑移。程序从相邻梁纵筋和柱纵筋计算 `ρx/ρy` 与最大钢筋间距 `Sx/Sy`，柱轴力由重力荷载计算后乘轴压比放大系数；梁水平轴力默认取零，可通过 `horizontal_axial_force` 指定。MCFT 的剪应力–剪应变曲线按虚功关系 `M=τ·b_j·h_c·h_b` 转换为中心弹簧弯矩–转角骨架，计算得到的 16 个正负向 Pinching4 包络参数直接写入模型中的 `RCJoint2D` 调用。循环夹缩点取峰值变形与峰值力的 25%；夹缩、退化、能量容量和损伤类型等固定参数在生成模型的 Elements 区间定义为变量。`steel_hardening_ratio` 默认 `0.01`，`maximum_aggregate_size` 默认 `20 mm`。

`JointPanelContext -> JointMaterialSpec` 仍保留为可插拔接口。writer 将生成期得到的材料参数写入模型文件；`RCJoint2D.py/.tcl` 只负责按照这些参数创建材料、四个外部节点和 Joint2D 单元，不再执行 MCFT 迭代。该函数仅在 Elements 区间调用一次。

Tcl 将楼层质量放在 Joint2D 四自由度中心节点。OpenSeesPy 3.8 的 `mass()` 不能从三自由度 BasicBuilder 向该内部节点写入四维质量，因此 Python 脚本将等量质量放在相邻普通梁节点，并由零长度铰的高刚度平动方向传递到节点域。Python 的 PO/CP 静力流程无需阻尼参数，使用归一化的高度分布并跳过 Joint2D 域中不必要且不稳定的 ARPACK 调用；TH 流程仍执行特征值分析。

当前版本仍不包含 Mander 混凝土本构、楼板、剪力墙、纤维铰、独立钢筋滑移单元或三维建模。

### OpenSAS 文件放置

RC 输出保持平铺，仅包含模型 `.py/.tcl/.json`、文本模型信息、框架立面图和自包含 HTML 建模报告，不再单独输出截面 PNG，也不重复复制任何外部子程序。

将生成的模型 `.py/.tcl` 复制到 `OpenSAS/models`，再手动将本项目 `subroutines` 文件夹中的所需文件复制到 `OpenSAS/subroutines`。钢框架与 RC 框架共用 `TimeHistorySolver`、`PushoverAnalysis` 和 `CyclicPushover`，并统一采用 `Transformation` 约束处理器；RC 塑性铰与 Joint2D 分别调用 `RCHinge` 和 `RCJoint2D`。MRFHelper 不会自动写入 OpenSAS。

## 钢框架建模方法

钢框架继续采用二维平面杆系模型，可考虑构件集中塑性变形和节点域剪切变形。梁、柱采用弹性梁柱单元，端部塑性铰采用改进 IMK 本构，节点域采用 Hysteretic 本构，并通过虚拟柱考虑重力框架的 P-Delta 效应。
