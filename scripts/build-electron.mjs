import * as esbuild from 'esbuild'
import { mkdir } from 'node:fs/promises'
import path from 'node:path'
import process from 'node:process'

const shouldWatch = process.argv.includes('--watch')
const outdir = path.resolve('dist-electron')

await mkdir(outdir, { recursive: true })

const buildOptions = {
  entryPoints: ['src/electron/main.ts', 'src/electron/preload.ts'],
  bundle: true,
  platform: 'node',
  target: 'node18',
  format: 'cjs',
  sourcemap: true,
  outdir,
  external: ['electron'],
  outExtension: { '.js': '.cjs' },
}

const ctx = await esbuild.context(buildOptions)

if (shouldWatch) {
  await ctx.watch()
  console.log('esbuild: watching Electron files...')

  process.on('SIGINT', async () => {
    await ctx.dispose()
    process.exit(0)
  })
} else {
  await ctx.rebuild()
  await ctx.dispose()
}
