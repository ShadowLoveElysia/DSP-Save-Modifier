"""
Dyson Sphere Program - Dark Fog Injector v2.0
戴森球计划 - 黑雾数据注入器

从有黑雾的存档中提取黑雾数据，注入到无黑雾的存档中

License: AGPL-3.0
"""

import struct
import sys
import os
import shutil
import argparse
from datetime import datetime
from typing import Optional, Dict, Any, Tuple, List

__version__ = "2.0.0"

# ============================================================================
# 常量定义
# ============================================================================

MAGIC = b'VFSAVE'
HIVE_MAGIC = 19884  # 黑雾巢穴魔数


# ============================================================================
# 二进制读写工具类
# ============================================================================

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

    def read_double(self) -> float:
        result = struct.unpack_from('<d', self.data, self.pos)[0]
        self.pos += 8
        return result

    def read_bool(self) -> bool:
        result = self.data[self.pos] != 0
        self.pos += 1
        return result

    def read_7bit_int(self) -> int:
        """读取 7-bit 编码的整数"""
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

    def skip(self, count: int) -> None:
        self.pos += count

    def peek_int32(self) -> int:
        """查看下一个int32但不移动位置"""
        return struct.unpack_from('<i', self.data, self.pos)[0]


class BinaryWriter:
    """模拟 .NET BinaryWriter"""

    def __init__(self):
        self.buffer = bytearray()

    def write_int32(self, value: int) -> None:
        self.buffer.extend(struct.pack('<i', value))

    def write_bytes(self, data: bytes) -> None:
        self.buffer.extend(data)

    def get_bytes(self) -> bytes:
        return bytes(self.buffer)


# ============================================================================
# 存档解析器类
# ============================================================================

class DSPSaveParser:
    """戴森球计划存档解析器"""

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
            print("错误: 文件太小")
            return False
        if self.data[:6] != MAGIC:
            print("错误: 不是有效的DSP存档")
            return False
        return True

    def parse_header(self) -> Dict[str, Any]:
        """解析存档头部，获取基本信息"""
        if not self.data:
            return {}

        reader = BinaryReader(self.data)

        # 文件头
        magic = reader.read_bytes(6).decode('ascii')
        file_size = reader.read_int64()
        header_version = reader.read_int32()

        # 标志位
        header_sandbox_offset = reader.tell()
        is_sandbox_header = reader.read_bool()
        header_peace_offset = reader.tell()
        is_peace_header = reader.read_bool()

        # 游戏版本
        ver = (reader.read_int32(), reader.read_int32(),
               reader.read_int32(), reader.read_int32())

        game_tick = reader.read_int64()
        reader.read_int64()  # save_ticks

        # 截图
        screenshot_len = reader.read_int32()
        reader.skip(screenshot_len)

        # AccountData (头部)
        reader.read_int32()  # version
        reader.read_int32()  # platform
        reader.read_uint64()  # userId
        reader.read_string()  # userName
        reader.read_uint64()  # energy

        # GameData
        reader.read_int32()  # gamedata_version
        reader.read_int32()  # patch

        # AccountData (GameData中)
        reader.read_int32()
        reader.read_int32()
        reader.read_uint64()
        reader.read_string()

        # gameName
        game_name = reader.read_string()

        # GameDesc
        reader.read_int32()  # gamedesc_version
        reader.read_int64()  # creation_ticks
        reader.read_int32()  # cv[0]
        reader.read_int32()  # cv[1]
        reader.read_int32()  # cv[2]
        reader.read_int32()  # cv[3]

        galaxy_algo = reader.read_int32()
        galaxy_seed = reader.read_int32()
        star_count = reader.read_int32()
        reader.read_int32()  # player_proto
        resource_mult = reader.read_single()

        # savedThemeIds
        theme_count = reader.read_int32()
        for _ in range(theme_count):
            reader.read_int32()

        reader.read_bool()  # achievement_enable
        gamedesc_peace_offset = reader.tell()
        is_peace_gamedesc = reader.read_bool()
        gamedesc_sandbox_offset = reader.tell()
        is_sandbox_gamedesc = reader.read_bool()

        # CombatSettings
        combat_start = reader.tell()
        combat_version = reader.read_int32()
        aggressiveness = reader.read_single()

        self.info = {
            'game_name': game_name,
            'game_version': ver,
            'galaxy_seed': galaxy_seed,
            'star_count': star_count,
            'resource_mult': resource_mult,
            'header_peace_offset': header_peace_offset,
            'gamedesc_peace_offset': gamedesc_peace_offset,
            'combat_settings_offset': combat_start,
            'is_peace_header': is_peace_header,
            'is_peace_gamedesc': is_peace_gamedesc,
            'aggressiveness': aggressiveness,
        }

        return self.info

    def is_peace_mode(self) -> bool:
        """检查是否为和平模式"""
        return self.info.get('is_peace_header', True) or \
               self.info.get('is_peace_gamedesc', True)

    def find_dfhives_location(self) -> Tuple[int, int, int]:
        """
        查找 dfHives 数据在存档中的位置
        返回: (dfhives_count_offset, dfhives_data_start, dfhives_data_end)
        """
        if not self.data:
            return (-1, -1, -1)

        data = bytes(self.data)
        star_count = self.info.get('star_count', 0)
        hive_magic_bytes = struct.pack('<i', HIVE_MAGIC)

        # 从文件后半部分搜索魔数 19884
        search_start = len(data) // 2
        first_magic_pos = data.find(hive_magic_bytes, search_start)

        if first_magic_pos == -1:
            # 没有找到魔数，可能是和平模式
            return self._find_peace_mode_dfhives()

        # 向前查找 dfHives 数量
        dfhives_count_offset = first_magic_pos - 4
        count_at_pos = struct.unpack_from('<i', data, dfhives_count_offset)[0]

        if count_at_pos == star_count:
            # 找到正确位置，计算数据结束位置
            dfhives_data_end = self._find_dfhives_end(first_magic_pos, star_count)
            return (dfhives_count_offset, first_magic_pos, dfhives_data_end)

        return (-1, -1, -1)

    def _find_peace_mode_dfhives(self) -> Tuple[int, int, int]:
        """查找和平模式存档中 dfHives=0 的位置"""
        # 搜索特征：skillSystem 后面紧跟 0（dfHives数量）
        # 然后是 combatSpaceSystem 的版本号 0
        # 模式: [skillSystem数据...][0][0][units数据...][fleets数据...]

        data = bytes(self.data)
        star_count = self.info.get('star_count', 0)

        # 搜索连续的两个0（dfHives=0, combatSpaceSystem.version=0）
        search_start = len(data) // 2

        # 查找模式: int32(0) + int32(0) + int32(capacity) + int32(cursor=1)
        # 这是 dfHives=0 后面跟着 combatSpaceSystem
        for pos in range(search_start, len(data) - 20):
            val1 = struct.unpack_from('<i', data, pos)[0]
            val2 = struct.unpack_from('<i', data, pos + 4)[0]
            val3 = struct.unpack_from('<i', data, pos + 8)[0]
            val4 = struct.unpack_from('<i', data, pos + 12)[0]

            # dfHives=0, version=0, capacity>=1, cursor=1
            if val1 == 0 and val2 == 0 and val3 >= 1 and val4 == 1:
                # 验证：前面应该是 skillSystem 的数据
                # 后面应该是 DataPool 结构
                return (pos, pos + 4, pos + 4)

        return (-1, -1, -1)

    def _find_dfhives_end(self, start_pos: int, star_count: int) -> int:
        """查找 dfHives 数据的结束位置"""
        data = bytes(self.data)
        pos = start_pos

        for star_idx in range(star_count):
            # 读取每个星系的黑雾巢穴
            while True:
                if pos + 4 > len(data):
                    return pos
                magic = struct.unpack_from('<i', data, pos)[0]
                if magic != HIVE_MAGIC:
                    pos += 4  # 跳过结束标记 0
                    break
                pos += 4  # 跳过魔数
                # 跳过 hive 数据
                pos = self._skip_hive_data(pos)

        return pos

    def _skip_hive_data(self, pos: int) -> int:
        """跳过一个 hive 的数据"""
        reader = BinaryReader(self.data, pos)

        version = reader.read_int32()
        reader.read_int32()  # hiveAstroId
        reader.read_int32()  # seed
        reader.read_int32()  # rtseed

        # pbuilders 数组
        pbuilders_len = reader.read_int32()
        for _ in range(pbuilders_len):
            self._skip_pbuilder(reader)

        reader.read_bool()  # realized
        reader.read_bool()  # isEmpty
        reader.read_int32()  # ticks
        reader.read_int32()  # turboTicks
        reader.read_int32()  # turboRepress
        reader.read_bool()  # matterStatComplete
        reader.read_int32()  # matterProductStat
        reader.read_int32()  # matterConsumeStat
        reader.read_int32()  # matterProduction
        reader.read_int32()  # matterConsumption
        reader.read_int32()  # rootEnemyId
        reader.read_bool()  # isCarrierRealized
        reader.read_int32()  # tindersInTransit

        if version >= 1:
            reader.read_single()  # lancerAssaultCountBase
            if version == 1:
                reader.read_int32()

        if version >= 3:
            reader.read_int32()  # relayNeutralizedCounter

        # 跳过各种 DataPool
        for _ in range(7):  # builders,cores,nodes,connectors,replicators,gammas,turrets
            self._skip_datapool(reader)

        self._skip_objectpool(reader)  # relays

        for _ in range(2):  # tinders, units
            self._skip_datapool(reader)

        # idleRelayIds
        idle_relay_len = reader.read_int32()
        idle_relay_count = reader.read_int32()
        reader.skip(idle_relay_count * 4)

        # idleTinderIds
        idle_tinder_len = reader.read_int32()
        idle_tinder_count = reader.read_int32()
        reader.skip(idle_tinder_count * 4)

        # forms[0], forms[1], forms[2]
        for _ in range(3):
            self._skip_enemy_formation(reader)

        self._skip_evolve_data(reader)
        self._skip_hatred_list(reader)
        self._skip_hatred_list(reader)

        return reader.tell()

    def _skip_pbuilder(self, reader: BinaryReader):
        """跳过 GrowthPattern_DFSpace.Builder"""
        reader.read_int32()  # instBuilderId
        reader.read_int32()  # protoId
        reader.read_int32()  # modelIndex
        reader.read_int32()  # parentIndex
        reader.read_int32()  # childCount
        reader.read_int32()  # matterCost
        reader.read_int32()  # matterProvided
        reader.read_int32()  # workTicks
        reader.skip(4 * 7)   # lpos(3) + lrot(4)

    def _skip_datapool(self, reader: BinaryReader):
        """跳过 DataPool 数据"""
        capacity = reader.read_int32()
        cursor = reader.read_int32()
        recycle_cursor = reader.read_int32()
        # 需要跳过元素数据，但不知道元素大小
        # 这里简化处理，实际需要根据具体类型
        pass

    def _skip_objectpool(self, reader: BinaryReader):
        """跳过 ObjectPool 数据"""
        capacity = reader.read_int32()
        cursor = reader.read_int32()
        recycle_cursor = reader.read_int32()
        pass

    def _skip_enemy_formation(self, reader: BinaryReader):
        """跳过 EnemyFormation"""
        reader.read_int32()  # version
        port_count = reader.read_int32() & 0xFFFF
        vacancy_cursor = (reader.read_int32() >> 16) & 0xFFFF
        # 实际格式更复杂，这里简化

    def _skip_evolve_data(self, reader: BinaryReader):
        """跳过 EvolveData"""
        reader.read_int32()  # version
        reader.read_int32()  # level
        reader.read_int64()  # expl
        reader.read_int64()  # expf
        reader.read_int64()  # expp
        reader.read_int64()  # exppshr
        reader.read_int32()  # threat
        reader.read_int32()  # maxThreat
        reader.read_int32()  # threatshr
        reader.read_int32()  # waves
        reader.read_int32()  # waveTicks
        reader.read_int32()  # waveAsmTicks
        reader.read_int32()  # rankBase

    def _skip_hatred_list(self, reader: BinaryReader):
        """跳过 HatredList"""
        reader.read_int32()  # version
        for _ in range(8):
            reader.read_int64()  # target
            reader.read_int32()  # value

    def extract_dfhives_data(self) -> Optional[bytes]:
        """提取 dfHives 数据（包括数量）"""
        loc = self.find_dfhives_location()
        if loc[0] == -1:
            return None

        count_offset, data_start, data_end = loc
        # 提取从数量开始到数据结束的所有字节
        return bytes(self.data[count_offset:data_end])

    def get_dfhives_count(self) -> int:
        """获取 dfHives 数量"""
        loc = self.find_dfhives_location()
        if loc[0] == -1:
            return -1
        return struct.unpack_from('<i', self.data, loc[0])[0]

    def get_star_hive_boundaries(self) -> List[Tuple[int, int]]:
        """
        获取每个星系的黑雾数据边界
        返回: [(start, end), ...] 每个星系的数据范围
        """
        loc = self.find_dfhives_location()
        if loc[0] == -1:
            return []

        data = bytes(self.data)
        star_count = self.info.get('star_count', 0)
        boundaries = []
        pos = loc[1]  # 从第一个魔数位置开始

        for star_idx in range(star_count):
            star_start = pos
            # 读取该星系的所有 hive
            while True:
                if pos + 4 > len(data):
                    break
                magic = struct.unpack_from('<i', data, pos)[0]
                if magic != HIVE_MAGIC:
                    pos += 4  # 跳过结束标记 0
                    break
                pos += 4  # 跳过魔数
                pos = self._skip_hive_data(pos)
            boundaries.append((star_start, pos))

        return boundaries


# ============================================================================
# 注入器类
# ============================================================================

class DarkFogInjector:
    """黑雾数据注入器"""

    def __init__(self, source_path: str, target_path: str):
        self.source = DSPSaveParser(source_path)
        self.target = DSPSaveParser(target_path)

    def validate(self) -> Tuple[bool, str]:
        """验证两个存档"""
        if not self.source.load() or not self.source.validate():
            return (False, "无法加载源存档")

        if not self.target.load() or not self.target.validate():
            return (False, "无法加载目标存档")

        self.source.parse_header()
        self.target.parse_header()

        if self.source.is_peace_mode():
            return (False, "源存档是和平模式，没有黑雾数据")

        return (True, "验证通过")

    def check_compatibility(self) -> Tuple[bool, str]:
        """检查星系配置兼容性"""
        src = self.source.info
        tgt = self.target.info

        same_seed = src['galaxy_seed'] == tgt['galaxy_seed']
        same_count = src['star_count'] == tgt['star_count']

        if same_seed and same_count:
            return (True, "星系配置相同 - 推荐")
        elif same_count:
            return (False, f"星系数量相同({src['star_count']})但种子不同")
        else:
            return (False, f"星系配置不同: 源={src['star_count']}星, 目标={tgt['star_count']}星")

    def inject(self, output_path: str, skip_stars: List[int] = None) -> Tuple[bool, str]:
        """
        执行注入
        skip_stars: 要跳过的星系索引列表（从0开始），如 [0] 表示跳过主星系
        """
        if skip_stars is None:
            skip_stars = []

        # 1. 定位源存档的 dfHives 数据
        src_loc = self.source.find_dfhives_location()
        if src_loc[0] == -1:
            return (False, "无法在源存档中定位黑雾数据")

        # 2. 定位目标存档的 dfHives 位置
        tgt_loc = self.target.find_dfhives_location()
        if tgt_loc[0] == -1:
            return (False, "无法在目标存档中定位黑雾数据位置")

        # 3. 获取源存档每个星系的边界
        src_boundaries = self.source.get_star_hive_boundaries()
        star_count = self.source.info.get('star_count', 0)

        if len(src_boundaries) != star_count:
            return (False, "源存档星系数据解析错误")

        # 4. 构建新的 dfHives 数据（跳过指定星系）
        new_dfhives = bytearray()
        new_dfhives.extend(struct.pack('<i', star_count))  # 写入星系数量

        skipped_count = 0
        for star_idx in range(star_count):
            start, end = src_boundaries[star_idx]
            if star_idx in skip_stars:
                # 跳过该星系，写入空数据（只有结束标记0）
                new_dfhives.extend(struct.pack('<i', 0))
                skipped_count += 1
            else:
                # 复制该星系的黑雾数据
                new_dfhives.extend(self.source.data[start:end])

        print(f"  跳过了 {skipped_count} 个星系的黑雾数据")

        # 5. 构建新的目标存档
        tgt_data = self.target.data
        new_data = bytearray()

        # 前半部分（到 dfHives 位置）
        new_data.extend(tgt_data[:tgt_loc[0]])

        # 注入过滤后的黑雾数据
        new_data.extend(new_dfhives)

        # 后半部分（dfHives 之后）
        new_data.extend(tgt_data[tgt_loc[2]:])

        # 5. 修改 isPeaceMode 标志
        self._set_peace_mode(new_data, False)

        # 6. 更新文件大小
        self._update_file_size(new_data)

        # 7. 保存
        try:
            with open(output_path, 'wb') as f:
                f.write(new_data)
            return (True, f"成功保存到: {output_path}")
        except Exception as e:
            return (False, f"保存失败: {e}")

    def _set_peace_mode(self, data: bytearray, is_peace: bool) -> None:
        """设置和平模式标志"""
        tgt_info = self.target.info
        value = 0x01 if is_peace else 0x00

        # 修改头部的 isPeaceMode
        if 'header_peace_offset' in tgt_info:
            data[tgt_info['header_peace_offset']] = value

        # 修改 GameDesc 的 isPeaceMode
        if 'gamedesc_peace_offset' in tgt_info:
            data[tgt_info['gamedesc_peace_offset']] = value

    def _update_file_size(self, data: bytearray) -> None:
        """更新文件大小字段"""
        new_size = len(data)
        struct.pack_into('<q', data, 6, new_size)


# ============================================================================
# 警告和帮助信息
# ============================================================================

def print_warning():
    """打印警告信息"""
    print("""
╔════════════════════════════════════════════════════════════════╗
║                      重要警告 / WARNING                         ║
╠════════════════════════════════════════════════════════════════╣
║  1. 请务必备份原存档！                                          ║
║                                                                ║
║  2. 关于星系配置:                                               ║
║     [推荐] 使用相同星系配置(seed和星系数量)的存档               ║
║     [可选] 使用不同星系配置 - 有风险，可能导致:                 ║
║            - 黑雾巢穴位置不正确                                 ║
║            - 游戏崩溃或数据异常                                 ║
║                                                                ║
║  3. 此工具仍在开发中，可能存在未知问题                          ║
╚════════════════════════════════════════════════════════════════╝
""")


def main():
    parser = argparse.ArgumentParser(
        description='戴森球计划 - 黑雾数据注入器 v2.0',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  %(prog)s -a save.dsv                    # 分析存档
  %(prog)s -s combat.dsv -t peace.dsv -o output.dsv
                                          # 注入黑雾数据
  %(prog)s -s combat.dsv -t peace.dsv -o output.dsv --skip-birth-star
                                          # 注入但跳过主星系
  %(prog)s -s combat.dsv -t peace.dsv --skip-stars 0,1,2
                                          # 跳过指定星系
注意:
  - 推荐使用相同星系配置的存档
  - 不同配置需要 --force 参数
  - 使用 --skip-birth-star 保护已建设的主星系
        '''
    )

    parser.add_argument('--analyze', '-a', type=str,
                        help='分析存档文件')
    parser.add_argument('--source', '-s', type=str,
                        help='源存档（有黑雾）')
    parser.add_argument('--target', '-t', type=str,
                        help='目标存档（无黑雾）')
    parser.add_argument('--output', '-o', type=str,
                        help='输出文件路径')
    parser.add_argument('--force', '-f', action='store_true',
                        help='强制执行（即使配置不同）')
    parser.add_argument('--no-backup', action='store_true',
                        help='不创建备份')
    parser.add_argument('--skip-birth-star', action='store_true',
                        help='跳过主星系（出生星系）的黑雾数据')
    parser.add_argument('--skip-stars', type=str,
                        help='跳过指定星系的黑雾数据，用逗号分隔（从0开始，如: 0,1,2）')
    parser.add_argument('--version', '-v', action='version',
                        version=f'%(prog)s {__version__}')

    args = parser.parse_args()

    if args.analyze:
        return analyze_save(args.analyze)
    elif args.source and args.target:
        return inject_darkfog(args)
    else:
        parser.print_help()
        return 1


def analyze_save(filepath: str) -> int:
    """分析单个存档文件"""
    if not os.path.exists(filepath):
        print(f"错误: 文件不存在: {filepath}")
        return 1

    parser = DSPSaveParser(filepath)
    if not parser.load() or not parser.validate():
        return 1

    info = parser.parse_header()

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
    is_peace = parser.is_peace_mode()
    mode = "和平模式" if is_peace else "黑雾模式"
    print(f"  当前模式: {mode}")
    print(f"  攻击性设置: {info['aggressiveness']}")

    print(f"\n[黑雾数据]")
    dfhives_count = parser.get_dfhives_count()
    if dfhives_count == -1:
        print(f"  无法定位黑雾数据")
    elif dfhives_count == 0:
        print(f"  黑雾巢穴数量: 0 (和平模式)")
    else:
        print(f"  黑雾巢穴数量: {dfhives_count}")
        loc = parser.find_dfhives_location()
        print(f"  数据位置: 偏移 {loc[0]} - {loc[2]}")
        print(f"  数据大小: {loc[2] - loc[0]} 字节")

    return 0


def inject_darkfog(args) -> int:
    """执行黑雾数据注入"""
    # 检查文件
    if not os.path.exists(args.source):
        print(f"错误: 源文件不存在: {args.source}")
        return 1
    if not os.path.exists(args.target):
        print(f"错误: 目标文件不存在: {args.target}")
        return 1

    # 确定输出路径
    if args.output:
        output_path = args.output
    else:
        base, ext = os.path.splitext(args.target)
        output_path = f"{base}_darkfog{ext}"

    print_warning()

    # 创建注入器
    injector = DarkFogInjector(args.source, args.target)

    # 验证存档
    valid, msg = injector.validate()
    if not valid:
        print(f"错误: {msg}")
        return 1

    # 显示存档信息
    print(f"\n{'='*60}")
    print(f"存档信息")
    print(f"{'='*60}")

    src_info = injector.source.info
    tgt_info = injector.target.info

    print(f"\n[源存档] (有黑雾)")
    print(f"  游戏名称: {src_info['game_name']}")
    print(f"  星系种子: {src_info['galaxy_seed']}")
    print(f"  恒星数量: {src_info['star_count']}")

    print(f"\n[目标存档] (无黑雾)")
    print(f"  游戏名称: {tgt_info['game_name']}")
    print(f"  星系种子: {tgt_info['galaxy_seed']}")
    print(f"  恒星数量: {tgt_info['star_count']}")

    # 检查兼容性
    compatible, compat_msg = injector.check_compatibility()
    print(f"\n[兼容性检查]")
    print(f"  {compat_msg}")

    if not compatible and not args.force:
        print(f"\n警告: 星系配置不同，可能导致问题!")
        print(f"如果仍要继续，请使用 --force 参数")
        return 1

    if not compatible:
        print(f"\n警告: 使用 --force 强制执行，风险自负!")

    # 创建备份
    if not args.no_backup:
        backup_path = args.target + '.backup'
        if os.path.exists(backup_path):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = f"{args.target}.backup_{timestamp}"
        try:
            shutil.copy2(args.target, backup_path)
            print(f"\n已创建备份: {backup_path}")
        except Exception as e:
            print(f"警告: 创建备份失败 - {e}")

    # 执行注入
    print(f"\n{'='*60}")
    print(f"执行注入")
    print(f"{'='*60}")

    # 解析要跳过的星系
    skip_stars = []
    if args.skip_birth_star:
        skip_stars.append(0)  # 主星系索引为0
        print(f"  将跳过主星系（索引 0）的黑雾数据")
    if args.skip_stars:
        try:
            extra_skips = [int(x.strip()) for x in args.skip_stars.split(',')]
            skip_stars.extend(extra_skips)
            print(f"  将跳过星系索引: {extra_skips}")
        except ValueError:
            print(f"错误: --skip-stars 参数格式错误，应为逗号分隔的数字")
            return 1
    skip_stars = list(set(skip_stars))  # 去重

    success, msg = injector.inject(output_path, skip_stars=skip_stars)
    if not success:
        print(f"错误: {msg}")
        return 1

    print(f"\n{msg}")

    print(f"\n{'='*60}")
    print(f"注入完成!")
    print(f"{'='*60}")
    print(f"\n重要提示:")
    print(f"1. 黑雾数据已从源存档注入到目标存档")
    print(f"2. 如果星系配置不同，黑雾位置可能不正确")
    print(f"3. 如果游戏加载异常，请使用备份恢复")

    return 0


if __name__ == '__main__':
    sys.exit(main())
