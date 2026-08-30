const fs = require('fs');
const path = require('path');
const { exec } = require('child_process');

// Directory containing the Hebrew video files to process
const baseDir = __dirname;
function configuredDir(name, fallback) {
    const value = process.env[name];
    return value ? path.resolve(baseDir, value) : path.join(baseDir, fallback);
}
const videosDir = configuredDir('WIZECARE_HEBREW_VIDEO_DIR', 'HebVideo');
// Directory where the extracted audio files will be saved
const outputDir = configuredDir('WIZECARE_DONE_ALL_DIR', 'done_all');
// Directory where processed video files will be moved after extraction
const doneDir = configuredDir('WIZECARE_DONE_HEBREW_DIR', 'doneHeb');

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
 * Extracts audio from a given video file and saves it as a WAV file.
 * Moves the processed video to the 'doneHeb' directory.
 * @param {string} videoName - The name of the video file to process.
 */
function extractAudioFromVideo(videoName) {
    if (!videoName) {
        console.log('No video file specified.');
        return;
    }

    const inputVideoPath = path.join(videosDir, videoName);
    if (!fs.existsSync(inputVideoPath)) {
        console.log('Video file does not exist:', inputVideoPath);
        return;
    }

    // Extract the number from the video filename (if present)
    const number = extractNumber(videoName);
    const lang = "he";
    // Construct the output audio filename, including the number if available
    const audioName = number ? `output_${lang}_${number}.wav` : `output_${lang}.wav`;
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

        // Move the processed video to the 'doneHeb' directory
        const doneVideoPath = path.join(doneDir, videoName);
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

// Get the video filename from the command line arguments (e.g., from Python or terminal)
const videoName = process.argv[2];
extractAudioFromVideo(videoName);

module.exports = { extractAudioFromVideo };
