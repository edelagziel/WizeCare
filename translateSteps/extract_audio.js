const fs = require('fs');
const path = require('path');
const { exec } = require('child_process');

// Directory containing the video files to process
const baseDir = __dirname;
function configuredDir(name, fallback) {
    const value = process.env[name];
    return value ? path.resolve(baseDir, value) : path.join(baseDir, fallback);
}
const videosDir = configuredDir('WIZECARE_VIDEO_DIR', 'videos');
// Directory where the extracted audio files will be saved
const outputDir = configuredDir('WIZECARE_AUDIO_DIR', 'audiofile');
// Directory where processed video files will be moved after extraction
const doneDir = configuredDir('WIZECARE_DONE_VIDEO_DIR', 'doneVideos');

/**
 * Extracts the first sequence of digits from a filename.
 * @param {string} filename - The filename to extract the number from.
 * @returns {string|null} - The extracted number as a string, or null if not found.
 */
function extractNumber(filename) {
    const match = filename.match(/\d+/);
    return match ? match[0] : null;
}

/**
 * Finds the most recently modified video file in the given directory.
 * Only considers files with .mp4, .mov, or .avi extensions.
 * @param {string} dir - The directory to search for video files.
 * @returns {string|null} - The name of the latest video file, or null if none found.
 */
function getLatestFile(dir) {
    const files = fs.readdirSync(dir)
        .filter(f => f.endsWith('.mp4') || f.endsWith('.mov') || f.endsWith('.avi'))
        .map(name => ({
            name,
            time: fs.statSync(path.join(dir, name)).mtime.getTime()
        }))
        .sort((a, b) => b.time - a.time);
    return files.length > 0 ? files[0].name : null;
}

/**
 * Extracts audio from the most recently modified video file in the videosDir.
 * The audio is saved as a mono, 16kHz, 16-bit PCM WAV file in outputDir.
 * After extraction, the video file is moved to doneDir.
 */
function extractLatestAudio() 
{
    const latestVideo = getLatestFile(videosDir);
    if (!latestVideo) {
        console.log('No video file found in the folder');
        return;
    }

    // Extract the number from the video filename (if present)
    const number = extractNumber(latestVideo);
    // Construct the output audio filename, including the number if available
    const audioName = number ? `output_${number}.wav` : `output.wav`;
    const inputVideoPath = path.join(videosDir, latestVideo);
    const outputAudioPath = path.join(outputDir, audioName);

    // Build the ffmpeg command to extract audio as mono, 16kHz, 16-bit PCM WAV
    const command = `ffmpeg -i "${inputVideoPath}" -vn -acodec pcm_s16le -ar 16000 -ac 1 "${outputAudioPath}"`;

    // Execute the ffmpeg command
    exec(command, (error, stdout, stderr) => {
        if (error) {
            console.error('ffmpeg error:', error.message);
            return;
        }
        console.log('Audio extracted:', outputAudioPath);

        // Move the processed video to the doneVideos directory
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

// Ensure all required directories exist; create them if they do not
for (const dir of [videosDir, outputDir, doneDir]) {
        if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
}

// Start the audio extraction process
extractLatestAudio();

module.exports = { extractLatestAudio };
