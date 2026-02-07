# DSP Dark Fog Save Tools

戴森球计划 - 黑雾存档工具集

## 项目描述

将《戴森球计划》(Dyson Sphere Program) 和平模式存档转换为黑雾(战斗)模式的工具集。

## 工具列表

| 工具 | 说明 |
|------|------|
| `dsp_darkfog_converter.py` | 简单转换器 - 修改存档标志位和战斗设置 |
| `dsp_darkfog_injector.py` | 数据注入器 - 从其他存档注入完整黑雾数据 |
| `dsp_frida_hook.py` | Frida Hook - 动态监控游戏进程（实验性） |

## 功能特性

- 分析存档文件结构和黑雾数据
- 将和平模式存档转换为黑雾模式
- 从有黑雾的存档提取数据注入到和平存档
- 支持跳过指定星系（保护已建设区域）
- 支持三种难度等级（最低/默认/最高）
- 自动创建备份

## 安装要求

- Python 3.8+
- （可选）Frida: `pip install frida frida-tools`

## 重要警告

```
╔════════════════════════════════════════════════════════════════╗
║  1. 请务必备份原存档！                                          ║
║  2. 推荐使用相同星系配置（种子和星系数量）的存档                ║
║  3. 使用 --skip-birth-star 保护已建设的主星系                   ║
║  4. 不同星系配置可能导致黑雾位置异常或游戏崩溃                  ║
╚════════════════════════════════════════════════════════════════╝
```

---

## 工具一：简单转换器 (dsp_darkfog_converter.py)

仅修改存档标志位，不注入黑雾数据。游戏加载后可能自动生成黑雾。

### 分析存档
```bash
python dsp_darkfog_converter.py "你的存档.dsv"
```

### 转换为黑雾模式（默认难度）
```bash
python dsp_darkfog_converter.py "你的存档.dsv" --convert
```

### 指定难度等级
```bash
# 最低难度 - 被动模式
python dsp_darkfog_converter.py "存档.dsv" -c -d low

# 默认难度 - 普通模式
python dsp_darkfog_converter.py "存档.dsv" -c -d normal

# 最高难度 - 狂暴模式
python dsp_darkfog_converter.py "存档.dsv" -c -d high
```

### 输出到新文件
```bash
python dsp_darkfog_converter.py "存档.dsv" -c -o "新存档.dsv"
```

### 自定义详细设置
```bash
# 使用预设并覆盖部分设置
python dsp_darkfog_converter.py "存档.dsv" -c -d normal --max-density 2.0

# 完全自定义
python dsp_darkfog_converter.py "存档.dsv" -c --aggressiveness 3 --initial-level 2 --max-density 1.5
```

---

## 工具二：数据注入器 (dsp_darkfog_injector.py)

从有黑雾的存档提取完整数据，注入到和平模式存档。**推荐使用此工具。**

### 分析存档
```bash
python dsp_darkfog_injector.py -a "存档.dsv"
```

### 基本注入
```bash
python dsp_darkfog_injector.py -s "有黑雾的存档.dsv" -t "和平存档.dsv" -o "输出.dsv"
```

### 跳过主星系（保护已建设区域）
```bash
python dsp_darkfog_injector.py -s "源.dsv" -t "目标.dsv" -o "输出.dsv" --skip-birth-star
```

### 跳过多个星系
```bash
python dsp_darkfog_injector.py -s "源.dsv" -t "目标.dsv" --skip-stars 0,1,2
```

### 强制注入（不同星系配置）
```bash
python dsp_darkfog_injector.py -s "源.dsv" -t "目标.dsv" -o "输出.dsv" --force
```

## 难度等级

| 等级 | 参数 | 说明 |
|------|------|------|
| 最低 | `low` | 被动模式，黑雾不主动攻击 |
| 默认 | `normal` | 普通难度，标准战斗体验 |
| 最高 | `high` | 狂暴模式，黑雾极具攻击性 |

## 存档位置

Windows 默认存档路径:
```
%USERPROFILE%\Documents\Dyson Sphere Program\Save\
```

## 命令行参数

### 转换器参数 (dsp_darkfog_converter.py)

| 参数 | 说明 |
|------|------|
| `save_file` | 存档文件路径 |
| `--convert, -c` | 转换为黑雾模式 |
| `--difficulty, -d` | 难度预设: low/normal/high |
| `--output, -o` | 输出文件路径 |
| `--no-backup` | 不创建备份 |

### 注入器参数 (dsp_darkfog_injector.py)

| 参数 | 说明 |
|------|------|
| `--analyze, -a` | 分析存档文件 |
| `--source, -s` | 源存档（有黑雾） |
| `--target, -t` | 目标存档（无黑雾） |
| `--output, -o` | 输出文件路径 |
| `--skip-birth-star` | 跳过主星系 |
| `--skip-stars` | 跳过指定星系（如: 0,1,2） |
| `--force, -f` | 强制执行 |
| `--no-backup` | 不创建备份 |

### 可选详细设置

| 参数 | 说明 | 范围 |
|------|------|------|
| `--aggressiveness` | 攻击性 | 0=被动, 2=普通, 4=狂暴 |
| `--initial-level` | 初始等级 | 0-10 |
| `--initial-growth` | 初始成长 | 0.25-3 |
| `--initial-colonize` | 初始殖民 | 0.5-3 |
| `--max-density` | 最大密度 | 0.5-3 |
| `--growth-speed` | 成长速度 | 0.25-3 |
| `--power-threat` | 电力威胁 | 0.01-10 |
| `--battle-threat` | 战斗威胁 | 0.01-10 |
| `--battle-exp` | 战斗经验 | 0.01-10 |

## 工作原理

存档文件中有两处 `isPeaceMode` 标志：
1. **文件头部** (偏移 19)
2. **GameDesc 数据中**

黑雾数据 (`dfHives`) 按星系组织，每个星系可有多个巢穴。

---

## 推荐工作流程

### 场景：将已玩很久的和平存档转为黑雾模式

```bash
# 步骤 1: 新建一个相同配置的黑雾游戏
#         （相同种子、相同星系数量）
#         进入游戏后立即保存，命名为 "黑雾模板.dsv"

# 步骤 2: 使用注入器，跳过主星系
python dsp_darkfog_injector.py \
    -s "黑雾模板.dsv" \
    -t "你的和平存档.dsv" \
    -o "转换后.dsv" \
    --skip-birth-star

# 步骤 3: 加载 "转换后.dsv" 验证效果
```

## 重要提示

1. 转换前请备份原存档
2. 和平模式存档中没有黑雾巢穴数据
3. 游戏可能需要重新生成黑雾
4. 如果出现问题请使用备份恢复

## 许可证

AGPL-3.0 License
