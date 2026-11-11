const express = require('express');
const app = express();
const port = process.env.PORT || 3000;

app.use(express.json());

app.get('/health/liveness', (req, res) => {
    res.status(200).json({ status: 'alive' });
});

app.get('/health/readiness', (req, res) => {
    res.status(200).json({ status: 'ready' });
});

app.get('/api/v1/dispatch', (req, res) => {
    res.json({ service: 'dispatch-service', status: 'operational' });
});

app.listen(port, () => {
    console.log(`Dispatch service listening on port ${port}`);
});