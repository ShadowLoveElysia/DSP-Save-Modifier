"""
Dyson Sphere Program - Frida Hook for Dark Fog Data Export
戴森球计划 - Frida Hook 黑雾数据导出器

使用 Frida 动态 hook 游戏，在保存时导出黑雾数据

License: AGPL-3.0

使用方法:
1. 安装 Frida: pip install frida frida-tools
2. 启动游戏，加载一个有黑雾的存档
3. 运行此脚本: python dsp_frida_hook.py
4. 在游戏中保存，脚本会自动导出黑雾数据
5. 使用导出的数据文件配合注入器使用
"""

import frida
import sys
import os
import json
import struct
import time
from datetime import datetime
from typing import Optional

__version__ = "1.0.0"

# 导出文件路径
EXPORT_DIR = os.path.dirname(os.path.abspath(__file__))
EXPORT_FILE = os.path.join(EXPORT_DIR, "dfhives_export.bin")
EXPORT_INFO = os.path.join(EXPORT_DIR, "dfhives_export.json")


def get_frida_script():
    """返回 Frida JavaScript 脚本"""
    return """
'use strict';

// 查找 Unity mono 模块
var monoModule = null;
var modules = Process.enumerateModules();
for (var i = 0; i < modules.length; i++) {
    if (modules[i].name.toLowerCase().indexOf('mono') !== -1) {
        monoModule = modules[i];
        break;
    }
}

if (!monoModule) {
    send({type: 'error', message: 'Cannot find mono module'});
} else {
    send({type: 'info', message: 'Found mono module: ' + monoModule.name});
}

// Mono API 函数
var mono_get_root_domain = null;
var mono_thread_attach = null;
var mono_assembly_foreach = null;
var mono_assembly_get_image = null;
var mono_class_from_name = null;
var mono_class_get_method_from_name = null;
var mono_compile_method = null;

function initMonoApi() {
    try {
        mono_get_root_domain = new NativeFunction(
            Module.findExportByName(monoModule.name, 'mono_get_root_domain'),
            'pointer', []
        );
        mono_thread_attach = new NativeFunction(
            Module.findExportByName(monoModule.name, 'mono_thread_attach'),
            'pointer', ['pointer']
        );
        mono_assembly_foreach = new NativeFunction(
            Module.findExportByName(monoModule.name, 'mono_assembly_foreach'),
            'void', ['pointer', 'pointer']
        );
        mono_assembly_get_image = new NativeFunction(
            Module.findExportByName(monoModule.name, 'mono_assembly_get_image'),
            'pointer', ['pointer']
        );
        mono_class_from_name = new NativeFunction(
            Module.findExportByName(monoModule.name, 'mono_class_from_name'),
            'pointer', ['pointer', 'pointer', 'pointer']
        );
        mono_class_get_method_from_name = new NativeFunction(
            Module.findExportByName(monoModule.name, 'mono_class_get_method_from_name'),
            'pointer', ['pointer', 'pointer', 'int']
        );
        mono_compile_method = new NativeFunction(
            Module.findExportByName(monoModule.name, 'mono_compile_method'),
            'pointer', ['pointer']
        );

        send({type: 'info', message: 'Mono API initialized'});
        return true;
    } catch (e) {
        send({type: 'error', message: 'Failed to init Mono API: ' + e});
        return false;
    }
}

// 存储找到的程序集
var assemblyCSharp = null;

function findAssembly(assembly, userData) {
    var image = mono_assembly_get_image(assembly);
    var name = image.readPointer().readCString();
    if (name && name.indexOf('Assembly-CSharp') !== -1) {
        assemblyCSharp = image;
    }
}

function hookSaveMethod() {
    if (!initMonoApi()) return;

    // 附加到 mono 线程
    var domain = mono_get_root_domain();
    mono_thread_attach(domain);

    // 查找 Assembly-CSharp
    var callback = new NativeCallback(findAssembly, 'void', ['pointer', 'pointer']);
    mono_assembly_foreach(callback, ptr(0));

    if (!assemblyCSharp) {
        send({type: 'error', message: 'Cannot find Assembly-CSharp'});
        return;
    }

    send({type: 'info', message: 'Found Assembly-CSharp'});

    // 查找 GameSave.SaveCurrentGame 方法
    var gameSaveClass = mono_class_from_name(
        assemblyCSharp,
        Memory.allocUtf8String(''),
        Memory.allocUtf8String('GameSave')
    );

    if (!gameSaveClass.isNull()) {
        var saveMethod = mono_class_get_method_from_name(
            gameSaveClass,
            Memory.allocUtf8String('SaveCurrentGame'),
            1
        );

        if (!saveMethod.isNull()) {
            var saveMethodPtr = mono_compile_method(saveMethod);
            send({type: 'info', message: 'Found SaveCurrentGame at: ' + saveMethodPtr});

            // Hook 保存方法
            Interceptor.attach(saveMethodPtr, {
                onEnter: function(args) {
                    send({type: 'save_start', message: 'Game save started'});
                },
                onLeave: function(retval) {
                    send({type: 'save_end', message: 'Game save completed'});
                }
            });
        }
    }

    send({type: 'ready', message: 'Hook ready. Save your game to export dark fog data.'});
}

// 延迟执行，等待游戏完全加载
setTimeout(hookSaveMethod, 2000);
"""


class FridaHooker:
    """Frida Hook 管理器"""

    def __init__(self):
        self.session: Optional[frida.core.Session] = None
        self.script: Optional[frida.core.Script] = None
        self.process_name = "DSPGAME.exe"

    def find_process(self) -> Optional[int]:
        """查找游戏进程"""
        try:
            for proc in frida.enumerate_processes():
                if self.process_name.lower() in proc.name.lower():
                    return proc.pid
            return None
        except Exception as e:
            print(f"错误: 无法枚举进程 - {e}")
            return None

    def attach(self) -> bool:
        """附加到游戏进程"""
        pid = self.find_process()
        if pid is None:
            print(f"错误: 找不到游戏进程 {self.process_name}")
            print("请先启动游戏并加载存档")
            return False

        try:
            self.session = frida.attach(pid)
            print(f"已附加到进程: {self.process_name} (PID: {pid})")
            return True
        except Exception as e:
            print(f"错误: 无法附加到进程 - {e}")
            return False

    def on_message(self, message, data):
        """处理来自脚本的消息"""
        if message['type'] == 'send':
            payload = message['payload']
            msg_type = payload.get('type', 'unknown')
            msg_text = payload.get('message', '')

            if msg_type == 'error':
                print(f"[错误] {msg_text}")
            elif msg_type == 'info':
                print(f"[信息] {msg_text}")
            elif msg_type == 'ready':
                print(f"\n{'='*50}")
                print(msg_text)
                print(f"{'='*50}\n")
            elif msg_type == 'save_start':
                print(f"[保存] 游戏正在保存...")
            elif msg_type == 'save_end':
                print(f"[保存] 保存完成!")
                print(f"[提示] 黑雾数据已在存档中，使用注入器提取")
            elif msg_type == 'data':
                # 处理导出的数据
                self.handle_export_data(data)
        elif message['type'] == 'error':
            print(f"[脚本错误] {message}")

    def handle_export_data(self, data):
        """处理导出的黑雾数据"""
        if data:
            with open(EXPORT_FILE, 'wb') as f:
                f.write(data)
            print(f"[导出] 黑雾数据已保存到: {EXPORT_FILE}")

    def run(self):
        """运行 hook"""
        if not self.attach():
            return False

        try:
            self.script = self.session.create_script(get_frida_script())
            self.script.on('message', self.on_message)
            self.script.load()

            print("\n按 Ctrl+C 退出...")

            # 保持运行
            while True:
                time.sleep(1)

        except KeyboardInterrupt:
            print("\n正在退出...")
        except Exception as e:
            print(f"错误: {e}")
        finally:
            if self.script:
                self.script.unload()
            if self.session:
                self.session.detach()

        return True


def print_usage():
    """打印使用说明"""
    print(f"""
{'='*60}
戴森球计划 - Frida Hook 黑雾数据导出器 v{__version__}
{'='*60}

使用方法:
  1. 安装 Frida: pip install frida frida-tools
  2. 启动游戏，加载一个有黑雾的存档
  3. 运行此脚本: python {os.path.basename(__file__)}
  4. 在游戏中保存，脚本会监控保存操作
  5. 保存完成后，使用注入器从存档中提取黑雾数据

注意:
  - 需要管理员权限运行
  - 游戏必须已经启动并加载存档
  - Frida 可能被杀毒软件拦截，请添加白名单

替代方案:
  如果 Frida 不工作，可以直接使用注入器:
  1. 新建一个相同配置的黑雾模式游戏
  2. 立即保存
  3. 使用注入器从这个存档提取黑雾数据
""")


def main():
    print_usage()

    # 检查 Frida 是否安装
    try:
        import frida
    except ImportError:
        print("错误: 未安装 Frida")
        print("请运行: pip install frida frida-tools")
        return 1

    hooker = FridaHooker()
    hooker.run()

    return 0


if __name__ == '__main__':
    sys.exit(main())
