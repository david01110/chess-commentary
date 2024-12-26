const express = require('express');
const app = express();
app.use(express.static('.'));
const port = 8000;

app.listen(port, () => console.log(`Server läuft auf http://localhost:${port}`));
