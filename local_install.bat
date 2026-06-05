@echo off
chcp 65001 > nul
title 中文文稿写作 Agent 工具集 本地安装
cd /d "%~dp0"
setlocal enabledelayedexpansion

set TARGET_DIR=%USERPROFILE%\.copilot
set CONTINUE_DIR=%USERPROFILE%\.continue

echo.
echo ============================================
echo   中文文稿写作 Agent 工具集 本地安装
echo ============================================
echo.
echo Copilot 部署目标: %TARGET_DIR%
echo Continue 部署目标: %CONTINUE_DIR%
echo 数据来源: %~dp0
echo.

REM ── 创建目录 ──
echo [目录]
mkdir "%TARGET_DIR%\agents" 2>nul
mkdir "%TARGET_DIR%\skills" 2>nul
mkdir "%CONTINUE_DIR%\prompts" 2>nul
mkdir "%CONTINUE_DIR%\rules" 2>nul
echo   目录已就绪

REM ── 复制 Agents ──
echo.
echo [Copilot] Agents
for %%f in (".copilot\agents\*.agent.md") do (
    copy /y "%%f" "%TARGET_DIR%\agents\" > nul 2>&1
    if errorlevel 1 (echo   [FAIL] %%f) else (echo   [OK] %%~nxf)
)

REM ── 复制工具脚本 ──
echo.
echo [Tools]
if not exist "%TARGET_DIR%\tools\scripts" mkdir "%TARGET_DIR%\tools\scripts"
if exist "tools\scripts\analyze.py" (
    copy /y "tools\scripts\analyze.py" "%TARGET_DIR%\tools\scripts\" > nul 2>&1
    if errorlevel 1 (echo   [FAIL] tools/scripts/analyze.py) else (echo   [OK] tools/scripts/analyze.py)
)

REM ── 复制 Skills ──
echo.
echo [Copilot] Skills
for /d %%d in (".copilot\skills\*") do (
    if exist "%%d\SKILL.md" (
        if not exist "%TARGET_DIR%\skills\%%~nxd" mkdir "%TARGET_DIR%\skills\%%~nxd"
        copy /y "%%d\SKILL.md" "%TARGET_DIR%\skills\%%~nxd\" > nul 2>&1
        if errorlevel 1 (echo   [FAIL] %%~nxd) else (echo   [OK] %%~nxd)
    )
)

REM ── 复制风格模板 ──
echo.
echo [Copilot] 风格模板
if not exist "%TARGET_DIR%\skills\统一风格" mkdir "%TARGET_DIR%\skills\统一风格"
for %%f in (".copilot\skills\统一风格\*.json") do (
    copy /y "%%f" "%TARGET_DIR%\skills\统一风格\" > nul 2>&1
    if errorlevel 1 (echo   [FAIL] %%~nxf) else (echo   [OK] %%~nxf)
)

REM ── 复制 README ──
echo.
echo [README]
if exist "README.md" (
    copy /y "README.md" "%TARGET_DIR%\copilot-writing-tools-README.md" > nul 2>&1
    if errorlevel 1 (echo   [FAIL] README.md) else (echo   [OK] copilot-writing-tools-README.md)
)

REM ── MCP 服务器 ──
echo.
echo [MCP 服务器] local-search-mcp-server
set MCP_SRC_DIR=%~dp0local-search-mcp-server
set MCP_DST_DIR=%TARGET_DIR%\local-search-mcp-server
if not exist "!MCP_DST_DIR!" mkdir "!MCP_DST_DIR!"

if exist "%MCP_SRC_DIR%\index.js" (
    copy /y "%MCP_SRC_DIR%\index.js" "!MCP_DST_DIR!\" > nul 2>&1
    echo   [OK] index.js
)
if exist "%MCP_SRC_DIR%\package.json" (
    copy /y "%MCP_SRC_DIR%\package.json" "!MCP_DST_DIR!\" > nul 2>&1
    echo   [OK] package.json
)

REM 生成 config.json（不存在时从 example 复制）
if not exist "!MCP_DST_DIR!\config.json" (
    if exist "%MCP_SRC_DIR%\config.example.json" (
        copy /y "%MCP_SRC_DIR%\config.example.json" "!MCP_DST_DIR!\config.json" > nul 2>&1
        echo   [OK] config.json（从模板生成）
        echo   ⚠ 请编辑 !MCP_DST_DIR!\config.json 填写本地路径
    )
) else (
    echo   [OK] config.json 已存在，保持原样
)

REM npm install
echo.
echo   正在安装 MCP 服务器依赖 (npm install)...
pushd "!MCP_DST_DIR!"
call npm install --production
if errorlevel 1 (
    echo   [WARN] npm install 失败，请手动在 !MCP_DST_DIR! 中执行 npm install
) else (
    echo   [OK] 依赖安装完成
)
popd

REM MCP 配置 — 合并到 VS Code 的 mcp.json
echo.
echo   正在配置 MCP 服务器到 VS Code...
if not exist "%APPDATA%\Code\User\" mkdir "%APPDATA%\Code\User"

powershell -ExecutionPolicy Bypass -Command ^
    "$mcp='%APPDATA%\Code\User\mcp.json';" ^
    "$idx='!MCP_DST_DIR!\index.js';" ^
    "$entry=@{command='node';type='stdio';args=@($idx)};" ^
    "if(test-path $mcp){try{$cfg=gc $mcp -raw -encoding UTF8|ConvertFrom-Json}catch{cp $mcp \"$mcp.bak\" -force;$cfg=@{servers=@{}}}};" ^
    "if(-not $cfg.servers){$cfg=@{servers=@{}}};" ^
    "$cfg.servers|Add-Member -MemberType NoteProperty -Name 'local-search-mcp-server' -Value $entry -Force;" ^
    "Copy-Item $mcp \"$mcp.bak\" -Force -ErrorAction SilentlyContinue;" ^
    "$cfg|ConvertTo-Json -Depth 4|Out-File $mcp -Encoding UTF8 -Force;" ^
    "if(test-path $mcp){Write-Host '  [OK] MCP 配置已写入'}else{Write-Host '  [FAIL] 写入失败'}"

REM ── 复制 .continue/ 适配层（Continue 端）──
echo.
echo [Continue] 适配层

REM config.yaml — 智能合并
set "_SRC_CFG=%~dp0.continue\config.yaml"
set "_DST_CFG=%CONTINUE_DIR%\config.yaml"
if exist "%_SRC_CFG%" (
    if exist "%_DST_CFG%" (
        echo   检测到已有 config.yaml，正在合并...
        python -c "import yaml, os; tc=os.environ['_DST_CFG']; sc=os.environ['_SRC_CFG']; u=yaml.safe_load(open(tc,'r',encoding='utf-8')) or {}; s=yaml.safe_load(open(sc,'r',encoding='utf-8')) or {}; ms=s.get('mcpServers',{}); [u.setdefault('mcpServers',{}).__setitem__(k,v) for k,v in ms.items() if k not in u.get('mcpServers',{})]; sr=s.get('rules',[]); u.setdefault('rules',[]); ex={r.get('source') for r in u['rules'] if isinstance(r,dict)}; [u['rules'].append(r) or ex.add(r.get('source','')) for r in sr if (r.get('source') if isinstance(r,dict) else str(r)) not in ex]; yaml.dump(u, open(tc,'w',encoding='utf-8'), allow_unicode=True, default_flow_style=False, sort_keys=False)"
        if errorlevel 1 (echo   [FAIL] config.yaml 合并失败) else (echo   [OK] config.yaml 已合并)
    ) else (
        copy /y "%_SRC_CFG%" "%_DST_CFG%" > nul 2>&1
        echo   [OK] config.yaml（新建）
    )
)
for %%f in (".continue\prompts\*.prompt") do (
    copy /y "%%f" "%CONTINUE_DIR%\prompts\" > nul 2>&1
    if errorlevel 1 (echo   [FAIL] %%~nxf) else (echo   [OK] prompts\%%~nxf)
)
for %%f in (".continue\rules\*.mdc") do (
    copy /y "%%f" "%CONTINUE_DIR%\rules\" > nul 2>&1
    if errorlevel 1 (echo   [FAIL] %%~nxf) else (echo   [OK] rules\%%~nxf)
)

REM ── Python 依赖 ──
echo.
echo [Python 依赖] jieba — 量化分析 Skill 分词引擎
echo   正在安装 jieba (pip install jieba)...
pip install jieba > nul 2>&1
if errorlevel 1 (echo   [WARN] pip install jieba 失败，请手动安装: pip install jieba) else (echo   [OK] jieba 安装完成)
echo [Python 依赖] pyyaml — config.yaml 合并
echo   正在安装 pyyaml (pip install pyyaml)...
pip install pyyaml > nul 2>&1
if errorlevel 1 (echo   [WARN] pip install pyyaml 失败，请手动安装: pip install pyyaml) else (echo   [OK] pyyaml 安装完成)

REM ── 收尾 ──
echo.
echo ============================================
echo   安装完成
echo ============================================
echo.
echo Copilot 端已部署到: %TARGET_DIR%
echo.

set AGENT_COUNT=0
for %%f in ("%TARGET_DIR%\agents\*.agent.md") do set /a AGENT_COUNT+=1
echo   agents/                          (%AGENT_COUNT% 个 Agent)

set SKILL_COUNT=0
for /d %%d in ("%TARGET_DIR%\skills\*") do set /a SKILL_COUNT+=1
echo   skills/                          (%SKILL_COUNT% 个 Skill)
echo   local-search-mcp-server/         MCP 服务器（档案员 + 神来之笔）
echo   MCP 配置已合并至 %%APPDATA%%\Code\User\mcp.json
echo.
echo Continue 端已部署到: %CONTINUE_DIR%
echo   config.yaml                      配置
echo   prompts/                         斜杠命令
echo   rules/                           角色规则
echo.
echo ⚠ 首次安装后请务必编辑 MCP 配置：
echo   编辑 !MCP_DST_DIR!\config.json
echo   填写 kbRoot（知识库根路径）和 rhetoricDbPath（好词好句.jsonl 路径）
echo.
echo 重启 VS Code 或 Continue 后生效。
echo.
pause
