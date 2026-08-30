const fs = require('fs');
const path = require('path');
const { exec } = require('child_process');

const videosDir = './videos';
const outputDir = './audiofile';
const doneDir = './doneVideos';

// 1. Find the latest video file by modification date
function getLatestFile(dir) {
    const files = fs.readdirSync(dir)
        .filter(f => f.endsWith('.mp4') || f.endsWith('.mov') || f.endsWith('.avi')) // Supported file types
        .map(name => ({
            name,
            time: fs.statSync(path.join(dir, name)).mtime.getTime()
        }))
        .sort((a, b) => b.time - a.time); // Newest to oldest
    return files.length > 0 ? files[0].name : null;
}

function extractLatestAudio() 
{
    const latestVideo = getLatestFile(videosDir);
    if (!latestVideo) {
        console.log('No video file found in the folder');
        return;
    }
    const inputVideoPath = path.join(videosDir, latestVideo);
    const audioName = path.parse(latestVideo).name + 'Audio' + '.wav';
    const outputAudioPath = path.join(outputDir, audioName);

    // ffmpeg command
    const command = `ffmpeg -i "${inputVideoPath}" -vn -acodec pcm_s16le -ar 16000 -ac 1 "${outputAudioPath}"`;

    exec(command, (error, stdout, stderr) => {
        if (error) {
            console.error('ffmpeg error:', error.message);
            return;
        }
        console.log('Audio extracted:', outputAudioPath);

        // Move the video to the doneVideos folder
        const doneVideoPath = path.join(doneDir, latestVideo);
        fs.rename(inputVideoPath, doneVideoPath, (err) => {
            if (err) {
                console.error('Error moving video:', err.message);
            } else {
                console.log('Video moved to:', doneVideoPath);
            }
        });
    });
}

// Ensure all directories exist
for (const dir of [videosDir, outputDir, doneDir]) {
    if (!fs.existsSync(dir)) fs.mkdirSync(dir);
}

// Run!
extractLatestAudio();



module.exports = { extractLatestAudio };




