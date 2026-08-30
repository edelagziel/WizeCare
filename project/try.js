fetch('http://127.0.0.1:6000/STT')
  .then(res => res.json())
  .then(console.log)
  .catch(console.error);
