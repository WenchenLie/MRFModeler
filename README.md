MRFMolder可用于生成钢框架OpenSees二维平面模型的tcl脚本，适用于对钢框架结构进行后续时程分析、Pushover分析等。

### 安装
* 运行项目根目录下main.py
* 或通过PyPi安装：`pip install MRFHelper`

### 使用
通过定义三维钢框架的建筑尺寸、截面型号、荷载及其他建模参数，程序会自动将结构简化为二维平面分析模型，并生成对应的OpenSees模型。  
也可以运行以下代码直接得到程序内置已经建好的模型：  
```
frame = MRFhelper.Repository('4SMRF')
frame.generate_tcl_script('output')
```

### 建模方法
基于二维平面杆系模型建立钢框架的OpenSees模型，可考虑构件的集中塑性变形和节点域的剪切变形。梁、柱构件采用弹性梁柱单元，端部塑性铰采用改进IMK本构进行模拟，节点域的剪切行为采用Hysteretic本构进行模拟，采用虚拟柱考虑重力框架的P-delta效应。

