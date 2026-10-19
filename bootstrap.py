"""First-run demo; --install explicitly adds the isolated optional toolchain."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent


def check_integrity(root):
    from scripts.verify_distribution import verify_installation
    if not verify_installation(Path(root))['passed']:
        raise ValueError('源码完整性检查失败。首次安装请重新解压完整源码；已有定制项目请按迁移文档处理。')


def run_command(root, command, *, json_result=True):
    environment = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1')
    result = subprocess.run(list(map(str,command)), cwd=root, env=environment,
                            capture_output=json_result, text=True, encoding='utf-8', errors='replace')
    if result.returncode:
        step=Path(str(command[1])).name if len(command)>1 else 'command'
        raise RuntimeError(f'步骤 {step} 失败，退出码 {result.returncode}；请按用户指南诊断此步骤。')
    if not json_result:
        return {}
    try:
        report = json.loads(result.stdout)
    except ValueError:
        raise RuntimeError('命令未返回预期 JSON，未将此步骤判定为成功。') from None
    if not isinstance(report,dict):
        raise RuntimeError('命令结果格式不符合预期。')
    return report


def resolve_node(node, root=None):
    from spider_core.project_runtime import select_node
    return select_node(root or ROOT, node)


def tool_python(root):
    return Path(root)/'.venv-toolchain'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')


def install_tools(root,node):
    run_command(root,[sys.executable,'scripts/install_browser_toolchain.py','--component','all',
                      '--node',str(node),'--apply'],json_result=False)
    python=tool_python(root)
    if not python.is_file():
        raise RuntimeError('工具环境 Python 尚未生成，安装未完成。')
    configured=run_command(root,[str(python),'scripts/browser_toolchain.py','configure',
                                '--python',str(python),'--node',str(node)])
    if configured.get('passed') is not True:
        raise RuntimeError('MCP 启动定义生成失败。')


def onboard(root, *, install=False,node=None):
    if sys.version_info[:2] != (3, 11):
        raise ValueError('本项目部署入口需要 Python 3.11；请保留已有 Python，选择或并行安装 3.11，并使用其真实路径重新执行。')
    root=Path(root).resolve()
    check_integrity(root)
    selected=resolve_node(node, root) if install else None
    if install:
        install_tools(root,selected)
    python=tool_python(root) if install else Path(sys.executable)
    setup=run_command(root,[str(python),'scripts/agent_platform_compat.py','setup','--json'])
    if not setup.get('ok'):
        raise RuntimeError('Skill 入口未配置成功，请保留冲突内容并按用户指南处理。')
    demo=run_command(root,[str(python),'spider.py','run','experiments/example_local/collector.py',
                           '--task','experiments/example_local/task.example.json'])
    if (demo.get('status'),demo.get('completeness'),demo.get('records')) != ('completed','complete',3):
        raise RuntimeError('离线示例未达到三条完整结果，安装验收未通过。')
    run_dir=Path(demo['run_dir'])
    validation=json.loads((run_dir/'validation.json').read_text(encoding='utf-8'))
    if not validation.get('passed'):
        raise RuntimeError('示例数据校验未通过。')
    report={
        'passed':True,'generated_at':datetime.now(timezone.utc).isoformat(),
        'mode':'tools' if install else 'demo','tools_installed_this_run':bool(install),
        'skill_discovery_links_created':True,
        'demo':{'records':3,'validation_passed':True,'run_dir':str(run_dir),
                'data_file':str(run_dir/'normalized.jsonl')},
        'tool_python':str(python),
        'generated_mcp_config':str(root/'runs/_mcp/generated/mcp_config.json') if install else None,
        'browser_connection_verified':False,'agent_mcp_loading_verified':False,
        'external_targets_tested':False,'next_guide':'docs/USER_GUIDE.md',
    }
    output=root/'outputs/onboarding.json'
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile('w',encoding='utf-8',dir=output.parent,delete=False) as stream:
        temporary=Path(stream.name)
        json.dump(report,stream,ensure_ascii=False,indent=2)
        stream.write('\n')
    try:
        os.replace(temporary,output)
    finally:
        temporary.unlink(missing_ok=True)
    return report


def main():
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, 'reconfigure', None)
        if callable(reconfigure):
            reconfigure(encoding='utf-8', errors='replace')
    parser=argparse.ArgumentParser(description='首次使用：默认离线体验；--install 安装隔离工具链并生成 MCP 定义。')
    parser.add_argument('--install',action='store_true',help='联网安装本项目工具依赖，需要完整 Node24+/npm')
    parser.add_argument('--node',type=Path,help='可选：Node程序绝对路径；默认从PATH发现')
    args=parser.parse_args()
    try:
        result=onboard(ROOT,install=args.install,node=args.node)
        print('\n离线体验通过：3 条合成记录，数据校验通过。')
        print('结果文件：'+result['demo']['data_file'])
        print('本次报告：'+str(ROOT/'outputs/onboarding.json'))
        if args.install:
            print('工具依赖安装完成，MCP 启动定义已生成。浏览器连接与 Agent 加载仍需按指南完成。')
        else:
            print('本次未联网安装依赖、未启动浏览器；需要完整工具时运行同一命令并加 --install。')
        print('下一步：Agent 继续执行 scripts/deploy.py 的待验收阶段，见 docs/INSTALL_WITH_AGENT.md；无需重复发送安装提示词。')
        return 0
    except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as error:
        message=str(error) if isinstance(error,(ValueError,RuntimeError)) else type(error).__name__
        print('未完成：'+message,file=sys.stderr)
        print('请查看 docs/USER_GUIDE.md 的常见问题；不要删除已有任务或配置。',file=sys.stderr)
        return 1


if __name__=='__main__':
    raise SystemExit(main())
