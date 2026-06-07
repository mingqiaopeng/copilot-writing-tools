#!/bin/bash
# VS Code 扩展一键打包脚本

set -e

echo "📦 安装依赖..."
npm install

echo "🔨 编译 TypeScript..."
npm run compile

echo "📦 打包为 .vsix..."
vsce package --no-dependencies --allow-missing-repository

echo "✅ 打包完成！"
ls -lh *.vsix
