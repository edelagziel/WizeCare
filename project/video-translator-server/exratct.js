const ffmpegPath = require('ffmpeg-static');
const { spawn } = require('child_process');
const fs = require('fs');

const input = 'videos/myvideo.mp4';
const output = 'output/audio.mp3';

// ודא שתיקיית output קיימת
if (!fs.existsSync('output')) fs.mkdirSync('output');

const ffmpeg = spawn(ffmpegPath, [
  '-i', input,
  '-vn',
  '-ar', '44100',
  '-ac', '2',
  '-b:a', '192k',
  output
]);

ffmpeg.stderr.on('data', (data) => {
  console.error(`FFmpeg stderr: ${data}`);
});

ffmpeg.on('close', (code) => {
  if (code === 0) {
    console.log(`🎧 Audio extracted successfully to ${output}`);
  } else {
    console.error(`❌ FFmpeg process exited with code ${code}`);
  }
});
