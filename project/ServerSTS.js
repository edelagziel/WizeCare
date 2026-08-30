
const { extractLatestAudio } = require('./cd video-translator-server/ExractAudio');


const express = require('express');
const app = express();

app.use(express.json()); // allows receiving JSON body

// Basic GET route
app.get('/STS', (req, res) => 
{
    extractLatestAudio();
    res.json({ message: 'success' });
});



// Start the server on port 5000
app.listen(5000, () => 
{
  console.log('Node server listening on port 5000');
});
