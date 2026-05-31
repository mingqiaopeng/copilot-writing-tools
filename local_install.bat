@echo off
chcp 65001 > nul
title 中文文稿写作 Agent 工具集 本地安装
cd /d "%~dp0"
setlocal enabledelayedexpansion

set TARGET_DIR=%USERPROFILE%\.copilot

echo.
echo ============================================
echo   中文文稿写作 Agent 工具集 本地安装
echo ============================================
echo.
echo 安装目标: %TARGET_DIR%
echo 数据来源: %~dp0
echo.

REM ── 创建目录 ──
echo [目录]
mkdir "%TARGET_DIR%\agents" 2>nul
mkdir "%TARGET_DIR%\skills" 2>nul
echo   目录已就绪

REM ── 复制 Agents ──
echo.
echo [Agents]
for %%f in ("agents\*.agent.md") do (
    copy /y "%%f" "%TARGET_DIR%\agents\" > nul 2>&1
    if errorlevel 1 (echo   [FAIL] %%f) else (echo   [OK] %%f)
)

REM ── 复制 Skills ──
echo.
echo [Skills]
for /d %%d in ("skills\*") do (
    if exist "%%d\SKILL.md" (
        if not exist "%TARGET_DIR%\skills\%%~nxd" mkdir "%TARGET_DIR%\skills\%%~nxd"
        copy /y "%%d\SKILL.md" "%TARGET_DIR%\skills\%%~nxd\" > nul 2>&1
        if errorlevel 1 (echo   [FAIL] %%~nxd) else (echo   [OK] %%~nxd)
    )
)

REM ── 复制 README ──
echo.
echo [README]
if exist "README.md" (
    copy /y "README.md" "%TARGET_DIR%\copilot-writing-tools-README.md" > nul 2>&1
    if errorlevel 1 (echo   [FAIL] README.md) else (echo   [OK] copilot-writing-tools-README.md)
)

REM ── Python 依赖（量化分析 Skill 需要 jieba）──
echo.
echo [Python 依赖] jieba — 量化分析 Skill 分词引擎
echo   正在安装 jieba (pip install jieba)...
pip install jieba > nul 2>&1
if errorlevel 1 (echo   [WARN] pip install jieba 失败，请手动安装: pip install jieba) else (echo   [OK] jieba 安装完成)

REM ── 高级功能（可选：档案员 + 神来之笔）──
echo.
echo ============================================
echo   [可选] 高级功能 — 档案员 + 神来之笔
echo ============================================
echo.
echo 档案员（本地知识库检索）和神来之笔（修辞句子库搜索）依赖：
echo   - Everything (es.exe) — 文件名极速搜索
echo   - ripgrep (rg) — 文件内容搜索
echo   - MCP 服务器 — 桥接工具与修辞库
echo   仅推荐有命令行经验且已搭建本地知识库的用户安装。
echo.

set installAdvanced=n
set /p installAdvanced=是否安装高级功能（档案员 + 神来之笔）？(y/n，默认 n):

if /i "!installAdvanced!"=="y" (

    REM ── 档案员 Agent ──
    echo.
    echo [档案员 Agent]
    if exist "agents\档案员.agent.md" (
        copy /y "agents\档案员.agent.md" "%TARGET_DIR%\agents\" > nul 2>&1
        if errorlevel 1 (echo   [FAIL] 档案员.agent.md) else (echo   [OK] 档案员.agent.md)
    )

    REM ── 档案员配置（智能合并，不覆盖用户已有值）──
    if exist "agents\档案员.config.json" (
        if exist "%TARGET_DIR%\agents\档案员.config.json" (
            echo   配置已存在，跳过（如需覆盖请手动删除）
        ) else (
            copy /y "agents\档案员.config.json" "%TARGET_DIR%\agents\" > nul 2>&1
            if errorlevel 1 (echo   [FAIL] 档案员.config.json) else (echo   [OK] 档案员.config.json - 请修改 kbRoot 为实际路径)
        )
    )

    REM ── MCP 服务器 ──
    echo.
    echo [MCP 服务器] local-search-mcp-server
    set MCP_DIR=%TARGET_DIR%\local-search-mcp-server
    if not exist "!MCP_DIR!" mkdir "!MCP_DIR!"

    if exist "local-search-mcp-server\index.js" (
        copy /y "local-search-mcp-server\index.js" "!MCP_DIR!\" > nul 2>&1
        echo   [OK] index.js
    )
    if exist "local-search-mcp-server\package.json" (
        copy /y "local-search-mcp-server\package.json" "!MCP_DIR!\" > nul 2>&1
        echo   [OK] package.json
    )

    REM npm install
    echo.
    echo   正在安装 MCP 服务器依赖 (npm install)...
    pushd "!MCP_DIR!"
    call npm install --production
    if errorlevel 1 (
        echo   [WARN] npm install 失败，请手动在 !MCP_DIR! 中执行 npm install
    ) else (
        echo   [OK] 依赖安装完成
    )
    popd

    REM MCP 配置 — 合并到 VS Code 的 mcp.json
    echo.
    echo   正在配置 MCP 服务器...
    if not exist "%APPDATA%\Code\User\" mkdir "%APPDATA%\Code\User"

    powershell -ExecutionPolicy Bypass -Command ^
        "$mcp='%APPDATA%\Code\User\mcp.json';" ^
        "$idx='!MCP_DIR!\index.js';" ^
        "$entry=@{command='node';type='stdio';args=@($idx)};" ^
        "if(test-path $mcp){try{$cfg=gc $mcp -raw -encoding UTF8|ConvertFrom-Json}catch{cp $mcp \"$mcp.bak\" -force;$cfg=@{servers=@{}}};" ^
        "if(-not $cfg.servers){$cfg=@{servers=@{}}};" ^
        "$cfg.servers|Add-Member -MemberType NoteProperty -Name 'local-search-mcp-server' -Value $entry -Force;" ^
        "Copy-Item $mcp \"$mcp.bak\" -Force -ErrorAction SilentlyContinue;" ^
        "$cfg|ConvertTo-Json -Depth 4|Out-File $mcp -Encoding UTF8 -Force;" ^
        "if(test-path $mcp){Write-Host '  [OK] MCP 配置已写入'}else{Write-Host '  [FAIL] 写入失败'}"
)

REM ── 收尾 ──
echo.
echo ============================================
echo   安装完成
echo ============================================
echo.
echo 已部署到: %TARGET_DIR%
echo.

set AGENT_COUNT=0
for %%f in ("%TARGET_DIR%\agents\*.agent.md") do set /a AGENT_COUNT+=1
echo   agents/                          (%AGENT_COUNT% 个 Agent)

set SKILL_COUNT=0
for /d %%d in ("%TARGET_DIR%\skills\*") do set /a SKILL_COUNT+=1
echo   skills/                          (%SKILL_COUNT% 个 Skill)

if /i "!installAdvanced!"=="y" (
    echo   local-search-mcp-server/         MCP 服务器（档案员 + 神来之笔）
    echo   MCP 配置已合并至 %%APPDATA%%\Code\User\mcp.json
)
echo.
echo 重启 VS Code 后生效。
echo.
pause
