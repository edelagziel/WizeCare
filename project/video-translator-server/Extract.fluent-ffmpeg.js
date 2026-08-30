const ffmpeg = require('fluent-ffmpeg');
const path = require('path');





const inputPath = path.join(__dirname, 'videos', 'Try.mp4');
const outputPath = path.join(__dirname, 'output', 'audio.mp3');
ffmpeg(inputPath)
  .noVideo() // מסיר את הווידאו
  .output(outputPath)
  .on('end', () => {
    console.log('🎧 Audio extracted successfully!');
    console.log('Saved to:', outputPath);
  })
  .on('error', (err) => {
    console.error('❌ Error during audio extraction:', err.message);
  })
  .run();