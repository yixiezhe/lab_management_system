import { spawnSync } from 'node:child_process'
import { createRequire } from 'node:module'

const require = createRequire(import.meta.url)

const packageMap = {
  'win32-x64': '@rollup/rollup-win32-x64-msvc',
  'linux-x64': '@rollup/rollup-linux-x64-gnu',
  'darwin-x64': '@rollup/rollup-darwin-x64',
  'darwin-arm64': '@rollup/rollup-darwin-arm64',
}

const key = `${process.platform}-${process.arch}`
const packageName = packageMap[key]

if (process.env.SKIP_ROLLUP_NATIVE_ENSURE === '1') {
  process.exit(0)
}

// 当前项目主要在 Windows 下运行，自动补包仅在 Windows 开启，避免 WSL/跨平台 node_modules 引发 npm 重命名冲突。
if (process.platform !== 'win32') {
  process.exit(0)
}

if (!packageName) {
  process.exit(0)
}

try {
  require.resolve(packageName)
  process.exit(0)
} catch (_) {
  // fall through to install
}

const result = process.platform === 'win32'
  ? spawnSync(
      process.env.ComSpec || 'cmd.exe',
      ['/d', '/s', '/c', `npm install --no-save ${packageName}`],
      {
        stdio: 'inherit',
        env: process.env,
      }
    )
  : spawnSync(
      'npm',
      ['install', '--no-save', packageName],
      {
        stdio: 'inherit',
        env: process.env,
      }
    )

if (result.error) {
  console.error(`[ensure-rollup-native] install failed: ${result.error.message}`)
  process.exit(1)
}

if (typeof result.status === 'number' && result.status !== 0) {
  process.exit(result.status)
}
