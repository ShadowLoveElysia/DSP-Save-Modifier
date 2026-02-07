"""
Dyson Sphere Program - Dark Fog Save Converter
戴森球计划 - 黑雾存档转换器

将和平模式存档转换为黑雾(战斗)模式

License: AGPL-3.0
"""

import struct
import sys
import os
import shutil
import argparse
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple


__version__ = "1.0.0"


class BinaryReader:
    """模拟 .NET BinaryReader"""

    def __init__(self, data: bytes, offset: int = 0):
        self.data = data
        self.pos = offset

    def read_bytes(self, count: int) -> bytes:
        result = self.data[self.pos:self.pos + count]
        self.pos += count
        return result

    def read_int32(self) -> int:
        result = struct.unpack_from('<i', self.data, self.pos)[0]
        self.pos += 4
        return result

    def read_int64(self) -> int:
        result = struct.unpack_from('<q', self.data, self.pos)[0]
        self.pos += 8
        return result

    def read_uint64(self) -> int:
        result = struct.unpack_from('<Q', self.data, self.pos)[0]
        self.pos += 8
        return result

    def read_single(self) -> float:
        result = struct.unpack_from('<f', self.data, self.pos)[0]
        self.pos += 4
        return result

    def read_bool(self) -> bool:
        result = self.data[self.pos] != 0
        self.pos += 1
        return result

    def read_7bit_int(self) -> int:
        """读取 7-bit 编码的整数 (用于字符串长度)"""
        result = 0
        shift = 0
        while True:
            b = self.data[self.pos]
            self.pos += 1
            result |= (b & 0x7F) << shift
            if (b & 0x80) == 0:
                break
            shift += 7
        return result

    def read_string(self) -> str:
        """读取 .NET BinaryWriter 格式的字符串"""
        length = self.read_7bit_int()
        if length == 0:
            return ""
        result = self.data[self.pos:self.pos + length].decode('utf-8')
        self.pos += length
        return result

    def tell(self) -> int:
        return self.pos

    def seek(self, pos: int) -> None:
        self.pos = pos


class DSPSaveAnalyzer:
    """戴森球计划存档分析器"""

    MAGIC = b'VFSAVE'

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.data: Optional[bytearray] = None
        self.info: Dict[str, Any] = {}

    def load(self) -> bool:
        """加载存档文件"""
        try:
            with open(self.filepath, 'rb') as f:
                self.data = bytearray(f.read())
            return True
        except Exception as e:
            print(f"错误: 无法读取文件 - {e}")
            return False

    def validate(self) -> bool:
        """验证存档文件"""
        if self.data is None:
            return False
        if len(self.data) < 20:
            print("错误: 文件太小，不是有效的存档")
            return False
        if self.data[:6] != self.MAGIC:
            print("错误: 文件魔数不匹配，不是有效的DSP存档")
            return False
        return True

    def analyze(self, verbose: bool = True) -> Dict[str, Any]:
        """分析存档结构"""
        if not self.data:
            return {}

        reader = BinaryReader(self.data)

        # 文件头部
        magic = reader.read_bytes(6).decode('ascii')
        file_size = reader.read_int64()
        header_version = reader.read_int32()

        # 关键标志位置
        header_sandbox_offset = reader.tell()
        is_sandbox_header = reader.read_bool()

        header_peace_offset = reader.tell()
        is_peace_header = reader.read_bool()

        # 游戏版本
        ver = (reader.read_int32(), reader.read_int32(),
               reader.read_int32(), reader.read_int32())

        game_tick = reader.read_int64()
        save_ticks = reader.read_int64()

        # 截图
        screenshot_len = reader.read_int32()
        reader.seek(reader.tell() + screenshot_len)

        # AccountData (头部)
        reader.read_int32()  # version
        reader.read_int32()  # platform
        reader.read_uint64()  # userId
        reader.read_string()  # userName
        reader.read_uint64()  # energy

        # GameData
        gamedata_version = reader.read_int32()
        patch = reader.read_int32()

        # AccountData (GameData中)
        reader.read_int32()
        reader.read_int32()
        reader.read_uint64()
        reader.read_string()

        # gameName
        game_name = reader.read_string()

        # GameDesc
        gamedesc_start = reader.tell()
        gamedesc_version = reader.read_int32()

        creation_ticks = reader.read_int64()
        cv = (reader.read_int32(), reader.read_int32(),
              reader.read_int32(), reader.read_int32())

        galaxy_algo = reader.read_int32()
        galaxy_seed = reader.read_int32()
        star_count = reader.read_int32()
        player_proto = reader.read_int32()
        resource_mult = reader.read_single()

        # savedThemeIds
        theme_count = reader.read_int32()
        for _ in range(theme_count):
            reader.read_int32()

        achievement_enable = reader.read_bool()

        # 关键: GameDesc中的isPeaceMode
        gamedesc_peace_offset = reader.tell()
        is_peace_gamedesc = reader.read_bool()

        gamedesc_sandbox_offset = reader.tell()
        is_sandbox_gamedesc = reader.read_bool()

        # CombatSettings
        combat_start = reader.tell()
        combat_version = reader.read_int32()
        aggressiveness = reader.read_single()
        initial_level = reader.read_single()
        initial_growth = reader.read_single()
        initial_colonize = reader.read_single()
        max_density = reader.read_single()
        growth_speed = reader.read_single()
        power_threat = reader.read_single()
        battle_threat = reader.read_single()
        battle_exp = reader.read_single()

        self.info = {
            'magic': magic,
            'file_size': file_size,
            'header_version': header_version,
            'game_version': ver,
            'game_tick': game_tick,
            'game_name': game_name,
            'galaxy_seed': galaxy_seed,
            'star_count': star_count,
            'resource_mult': resource_mult,

            # 关键偏移
            'header_peace_offset': header_peace_offset,
            'header_sandbox_offset': header_sandbox_offset,
            'gamedesc_peace_offset': gamedesc_peace_offset,
            'gamedesc_sandbox_offset': gamedesc_sandbox_offset,
            'combat_settings_offset': combat_start,

            # 当前状态
            'is_peace_header': is_peace_header,
            'is_sandbox_header': is_sandbox_header,
            'is_peace_gamedesc': is_peace_gamedesc,
            'is_sandbox_gamedesc': is_sandbox_gamedesc,

            # 战斗设置
            'combat_settings': {
                'aggressiveness': aggressiveness,
                'initial_level': initial_level,
                'initial_growth': initial_growth,
                'initial_colonize': initial_colonize,
                'max_density': max_density,
                'growth_speed': growth_speed,
                'power_threat': power_threat,
                'battle_threat': battle_threat,
                'battle_exp': battle_exp,
            }
        }

        if verbose:
            self._print_info()

        return self.info

    def _print_info(self) -> None:
        """打印分析信息"""
        info = self.info

        print(f"\n{'='*60}")
        print(f"戴森球计划存档分析")
        print(f"{'='*60}")

        print(f"\n[基本信息]")
        print(f"  游戏名称: {info['game_name']}")
        print(f"  游戏版本: {'.'.join(map(str, info['game_version']))}")
        print(f"  星系种子: {info['galaxy_seed']}")
        print(f"  恒星数量: {info['star_count']}")
        print(f"  资源倍率: {info['resource_mult']}")

        print(f"\n[游戏模式]")
        is_peace = info['is_peace_header'] or info['is_peace_gamedesc']
        is_sandbox = info['is_sandbox_header'] or info['is_sandbox_gamedesc']

        mode = "和平模式" if is_peace else "黑雾模式"
        if is_sandbox:
            mode += " + 沙盒模式"
        print(f"  当前模式: {mode}")

        print(f"\n[关键偏移]")
        print(f"  头部 isPeaceMode: 偏移 {info['header_peace_offset']}, 值={info['is_peace_header']}")
        print(f"  GameDesc isPeaceMode: 偏移 {info['gamedesc_peace_offset']}, 值={info['is_peace_gamedesc']}")

        print(f"\n[战斗设置] (CombatSettings)")
        cs = info['combat_settings']
        print(f"  攻击性: {cs['aggressiveness']}")
        print(f"  初始等级: {cs['initial_level']}")
        print(f"  初始成长: {cs['initial_growth']}")
        print(f"  最大密度: {cs['max_density']}")

    def is_peace_mode(self) -> bool:
        """检查是否为和平模式"""
        return self.info.get('is_peace_header', True) or self.info.get('is_peace_gamedesc', True)

    def convert_to_combat(self, combat_settings: Optional[Dict] = None) -> bool:
        """转换为战斗模式"""
        if not self.data or not self.info:
            print("错误: 请先加载并分析存档")
            return False

        if not self.is_peace_mode():
            print("存档已经是黑雾模式，无需转换")
            return True

        modifications = []

        # 修改头部的 isPeaceMode
        if self.info['is_peace_header']:
            modifications.append({
                'offset': self.info['header_peace_offset'],
                'old': True,
                'new': False,
                'desc': '头部 isPeaceMode'
            })

        # 修改 GameDesc 的 isPeaceMode
        if self.info['is_peace_gamedesc']:
            modifications.append({
                'offset': self.info['gamedesc_peace_offset'],
                'old': True,
                'new': False,
                'desc': 'GameDesc isPeaceMode'
            })

        # 执行修改
        print(f"\n执行修改...")
        for mod in modifications:
            self.data[mod['offset']] = 0x00  # False
            print(f"  已修改: {mod['desc']} [偏移: {mod['offset']}]")

        # 如果提供了战斗设置，也进行修改
        if combat_settings:
            self._update_combat_settings(combat_settings)

        return True

    def _update_combat_settings(self, settings: Dict) -> None:
        """更新战斗设置"""
        offset = self.info['combat_settings_offset']
        offset += 4  # 跳过版本号

        fields = ['aggressiveness', 'initial_level', 'initial_growth',
                  'initial_colonize', 'max_density', 'growth_speed',
                  'power_threat', 'battle_threat', 'battle_exp']

        for field in fields:
            if field in settings:
                value = settings[field]
                struct.pack_into('<f', self.data, offset, value)
                print(f"  已修改: {field} = {value}")
            offset += 4

    def save(self, output_path: Optional[str] = None) -> bool:
        """保存修改后的存档"""
        if not self.data:
            return False

        save_path = output_path or self.filepath

        try:
            with open(save_path, 'wb') as f:
                f.write(self.data)
            print(f"\n存档已保存: {save_path}")
            return True
        except Exception as e:
            print(f"错误: 保存失败 - {e}")
            return False

    def create_backup(self) -> Optional[str]:
        """创建备份"""
        backup_path = self.filepath + '.backup'

        if os.path.exists(backup_path):
            # 添加时间戳
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = f"{self.filepath}.backup_{timestamp}"

        try:
            shutil.copy2(self.filepath, backup_path)
            print(f"已创建备份: {backup_path}")
            return backup_path
        except Exception as e:
            print(f"警告: 创建备份失败 - {e}")
            return None


# 黑雾强度预设
DIFFICULTY_PRESETS = {
    'low': {
        'name': '最低 (被动)',
        'aggressiveness': 0.0,      # Passive
        'initial_level': 0.0,
        'initial_growth': 0.5,
        'initial_colonize': 0.5,
        'max_density': 0.5,
        'growth_speed': 0.5,
        'power_threat': 0.5,
        'battle_threat': 0.5,
        'battle_exp': 1.0,
    },
    'normal': {
        'name': '默认 (普通)',
        'aggressiveness': 2.0,      # Normal
        'initial_level': 0.0,
        'initial_growth': 1.0,
        'initial_colonize': 1.0,
        'max_density': 1.0,
        'growth_speed': 1.0,
        'power_threat': 1.0,
        'battle_threat': 1.0,
        'battle_exp': 1.0,
    },
    'high': {
        'name': '最高 (狂暴)',
        'aggressiveness': 4.0,      # Rampage
        'initial_level': 3.0,
        'initial_growth': 2.0,
        'initial_colonize': 2.0,
        'max_density': 2.0,
        'growth_speed': 2.0,
        'power_threat': 2.0,
        'battle_threat': 2.0,
        'battle_exp': 2.0,
    },
}


def get_combat_settings(difficulty: str = 'normal') -> Dict[str, float]:
    """获取指定难度的战斗设置"""
    preset = DIFFICULTY_PRESETS.get(difficulty, DIFFICULTY_PRESETS['normal'])
    return {k: v for k, v in preset.items() if k != 'name'}


def main():
    parser = argparse.ArgumentParser(
        description='戴森球计划 - 黑雾存档转换器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  %(prog)s save.dsv                    # 分析存档
  %(prog)s save.dsv --convert          # 转换为黑雾模式(默认难度)
  %(prog)s save.dsv -c --difficulty low    # 最低难度
  %(prog)s save.dsv -c --difficulty high   # 最高难度
  %(prog)s save.dsv -c -o new_save.dsv     # 输出到新文件

难度等级:
  low    - 最低 (被动): 黑雾不主动攻击
  normal - 默认 (普通): 标准难度
  high   - 最高 (狂暴): 黑雾极具攻击性

注意:
  - 转换后的存档可能需要游戏重新生成黑雾巢穴
  - 建议在转换前备份原存档
  - 如果游戏加载异常，请使用备份恢复
        '''
    )

    parser.add_argument('save_file', help='存档文件路径 (.dsv)')
    parser.add_argument('--convert', '-c', action='store_true',
                        help='转换为黑雾模式')
    parser.add_argument('--difficulty', '-d', type=str,
                        choices=['low', 'normal', 'high'],
                        default='normal',
                        help='黑雾难度: low/normal/high (默认: normal)')
    parser.add_argument('--output', '-o', type=str,
                        help='输出文件路径 (默认覆盖原文件)')
    parser.add_argument('--no-backup', action='store_true',
                        help='不创建备份')
    parser.add_argument('--version', '-v', action='version',
                        version=f'%(prog)s {__version__}')

    args = parser.parse_args()

    # 检查文件
    if not os.path.exists(args.save_file):
        print(f"错误: 文件不存在: {args.save_file}")
        return 1

    # 创建分析器
    analyzer = DSPSaveAnalyzer(args.save_file)

    # 加载并验证
    if not analyzer.load():
        return 1

    if not analyzer.validate():
        return 1

    # 分析存档
    analyzer.analyze(verbose=True)

    # 如果需要转换
    if args.convert:
        if not analyzer.is_peace_mode():
            print("\n存档已经是黑雾模式，无需转换")
            return 0

        print(f"\n{'='*60}")
        print("准备转换为黑雾模式")
        print(f"{'='*60}")

        # 显示选择的难度
        preset = DIFFICULTY_PRESETS[args.difficulty]
        print(f"  难度: {preset['name']}")

        # 创建备份
        if not args.no_backup:
            analyzer.create_backup()

        # 获取战斗设置
        combat_settings = get_combat_settings(args.difficulty)

        # 执行转换
        if analyzer.convert_to_combat(combat_settings):
            # 保存
            output_path = args.output if args.output else None
            if analyzer.save(output_path):
                print(f"\n{'='*60}")
                print("转换完成!")
                print(f"{'='*60}")
                print("\n重要提示:")
                print("1. 存档已修改为黑雾模式")
                print("2. 和平模式存档中没有黑雾巢穴数据")
                print("3. 游戏可能会在加载后自动生成黑雾")
                print("4. 如果出现问题，请使用备份恢复")
                return 0

    return 0


if __name__ == '__main__':
    sys.exit(main())
