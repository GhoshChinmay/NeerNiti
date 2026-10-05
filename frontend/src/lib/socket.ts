import { io, Socket } from "socket.io-client";

let socket: Socket | null = null;

export const getSocket = (): Socket | null => {
  if (typeof window === "undefined") return null;
  if (!socket) {
    const URL = process.env.NEXT_PUBLIC_WS_URL || "http://127.0.0.1:8000";
    socket = io(URL, {
      autoConnect: false,
      reconnectionAttempts: 5,
    });
  }
  return socket;
};
