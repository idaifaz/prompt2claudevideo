// Render index.html bingkai demi bingkai, gabung dengan muzik jadi MP4.
// Guna: node render.js [output.mp4] [--frames=a,b,c (PNG sahaja untuk semakan)]
const { chromium } = require('playwright');
const { spawn, execFileSync } = require('child_process');
const path = require('path');

const FPS = 30, DUR = 20, TOTAL = FPS * DUR;
const out = process.argv.find(a => a.endsWith('.mp4')) || path.join(__dirname, 'sinopsis-sijil-teknologi-senibina.mp4');
const only = (process.argv.find(a => a.startsWith('--frames=')) || '').slice(9);

(async () => {
  const browser = await chromium.launch({ args: ['--allow-file-access-from-files'] });
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  await page.goto('file://' + path.join(__dirname, 'index.html') + '?render=1');
  await page.evaluate(() => window.ready);

  if (only) {
    for (const f of only.split(',').map(Number)) {
      await page.evaluate(f => renderFrame(f), f);
      await page.screenshot({ path: path.join(process.env.SNAP_DIR || __dirname, `frame_${f}.png`) });
    }
    return browser.close();
  }

  const wav = path.join(__dirname, 'music.wav');
  execFileSync('python3', [path.join(__dirname, 'music.py'), wav]);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'png', '-i', '-',
    '-i', wav, '-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-pix_fmt', 'yuv420p', '-profile:v', 'high',
    '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', out], { stdio: ['pipe', 'inherit', 'inherit'] });
  for (let f = 0; f < TOTAL; f++) {
    await page.evaluate(f => renderFrame(f), f);
    const buf = await page.screenshot({ type: 'png' });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (f % 60 === 0) process.stdout.write(`frame ${f}/${TOTAL}\n`);
  }
  ff.stdin.end();
  await new Promise(r => ff.on('close', r));
  await browser.close();
  console.log('siap:', out);
})();
