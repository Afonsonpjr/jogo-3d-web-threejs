const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const path = require('path');
const app = express();
const server = http.createServer(app);
const io = new Server(server, { cors: { origin: '*', methods: ['GET', 'POST'] } });
const players = {};
io.on('connection', (socket) => {
    console.log('✅ Cliente conectado:', socket.id);
    socket.on('join', (data) => {
        console.log('👥 Jogador entrou:', data.name, data.id);
        players[data.id] = { id: data.id, name: data.name, x: data.x || 0, y: data.y || 2, z: data.z || 0 };
        io.emit('playerList', players);
        socket.broadcast.emit('playerJoined', data);
    });
    socket.on('playerMove', (data) => {
        if (players[data.id]) { players[data.id].x = data.x; players[data.id].y = data.y; players[data.id].z = data.z; }
        socket.broadcast.emit('playerMove', data);
    });
    socket.on('disconnect', () => {
        console.log('❌ Cliente desconectou:', socket.id);
        for (const id in players) { if (players[id].id === socket.id) { delete players[id]; break; } }
        io.emit('playerList', players);
        io.emit('playerLeft', socket.id);
    });
});
app.use(express.static(path.join(__dirname, '..')));
const PORT = process.env.PORT || 3000;
server.listen(PORT, () => { console.log('🚀 Servidor rodando na porta', PORT); });
