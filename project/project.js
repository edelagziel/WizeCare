
const express = require('express');
const app = express();

app.use(express.json()); // allows receiving JSON body


  app.get('/getSTS', async (req, res) => 
    {
        try 
        {
            console.log("welcome");
            const response = await fetch('http://localhost:5000/STS');
            const data = await response.json();
            res.json({ msg: data, message: 'success' });
        } 
        catch (err) 
        {
            res.status(500).json({ error: 'Failed to reach node server' });
        }
    });


app.get('/getSTT', async (req, res) => 
    {
        try 
        {
            console.log("welcome");
            const response = await fetch('http://localhost:6000/STT');
            const data = await response.json();
    
            // בדוק אם יש error בתשובה של פייתון
            if (data.result && data.result.error) 
                {
                res.status(400).json({ error: data.result.error });
            }
             else
              {
                res.json({ msg: data, message: 'success' });
            }
        } 
        catch (err) 
        {
            res.status(500).json({ error: 'Failed to reach Python server' });
        }
    });
    



// Start the server on port 
app.listen(4000, () => 
{
  console.log('Node server listening on port 4000');
});
