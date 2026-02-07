# DSP Dark Fog Save Converter

戴森球计划 - 黑雾存档转换器

## 项目描述

本工具用于将《戴森球计划》(Dyson Sphere Program) 和平模式存档转换为黑雾(战斗)模式。通过分析游戏存档的二进制结构，精确定位并修改关键标志位，实现模式转换。支持自定义黑雾难度等级，无需修改游戏本体文件。

将《戴森球计划》和平模式存档转换为黑雾(战斗)模式的工具。

## 功能特性

- 分析存档文件结构
- 显示当前游戏模式
- 将和平模式存档转换为黑雾模式
- 支持三种难度等级（最低/默认/最高）
- 自动创建备份

## 安装要求

- Python 3.6+
- 无需额外依赖

## 使用方法

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

| 参数 | 说明 |
|------|------|
| `save_file` | 存档文件路径 |
| `--convert, -c` | 转换为黑雾模式 |
| `--difficulty, -d` | 难度等级: low/normal/high |
| `--output, -o` | 输出文件路径 |
| `--no-backup` | 不创建备份 |
| `--version, -v` | 显示版本号 |

## 工作原理

存档文件中有两处 `isPeaceMode` 标志：
1. **文件头部** (偏移 19)
2. **GameDesc 数据中**

本工具将这两处的值从 `true` 修改为 `false`。

## 重要提示

1. 转换前请备份原存档
2. 和平模式存档中没有黑雾巢穴数据
3. 游戏可能需要重新生成黑雾
4. 如果出现问题请使用备份恢复

## 许可证

AGPL-3.0 License
