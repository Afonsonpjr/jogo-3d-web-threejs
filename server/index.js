import express from 'express';
import cors from 'cors';
import { createServer } from 'node:http';
import { Server } from 'socket.io';
const app=express(); app.use(cors());
const http=createServer(app);
const io=new Server(http,{cors:{origin:'*'}});
app.get('/health',(_,res)=>res.json({ok:true,players:io.sockets.sockets.size}));
io.on('connection',socket=>{
  socket.on('player:join',data=>socket.broadcast.emit('player:joined',{id:socket.id,...data}));
  socket.on('player:move',data=>socket.broadcast.emit('player:moved',{id:socket.id,...data}));
  socket.on('voice:signal',data=>socket.broadcast.emit('voice:signal',{id:socket.id,...data}));
  socket.on('disconnect',()=>socket.broadcast.emit('player:left',{id:socket.id}));
});
http.listen(process.env.PORT||3000,()=>console.log('Arena multiplayer em execução'));