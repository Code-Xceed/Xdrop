type MessageHandler = (message: any) => void;

class WebSocketService {
  private ws: WebSocket | null = null;
  private handlers: Set<MessageHandler> = new Set();
  private reconnectTimeout: number | null = null;
  private pingInterval: number | null = null;
  private isConnecting = false;

  public getIsConnecting(): boolean {
    return this.isConnecting;
  }

  public connect(): void {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }
    this.isConnecting = true;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/ws`;

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        this.isConnecting = false;
        console.log('[ResolveFetch WS] Connected to desktop service.');
        this.startPing();
      };

      this.ws.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data);
          if (parsed?.type === 'PONG') return;
          this.handlers.forEach((handler) => {
            try {
              handler(parsed);
            } catch (err) {
              console.error('[ResolveFetch WS] Handler execution error:', err);
            }
          });
        } catch (e) {
          console.error('[ResolveFetch WS] Failed to parse message:', e);
        }
      };

      this.ws.onclose = () => {
        this.isConnecting = false;
        this.stopPing();
        this.scheduleReconnect();
      };

      this.ws.onerror = (err) => {
        console.warn('[ResolveFetch WS] Connection error:', err);
        this.stopPing();
        this.ws?.close();
      };
    } catch (e) {
      this.isConnecting = false;
      this.stopPing();
      this.scheduleReconnect();
    }
  }

  private startPing(): void {
    this.stopPing();
    this.pingInterval = window.setInterval(() => {
      this.send({ type: 'PING' });
    }, 15000);
  }

  private stopPing(): void {
    if (this.pingInterval !== null) {
      window.clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimeout) return;
    this.reconnectTimeout = window.setTimeout(() => {
      this.reconnectTimeout = null;
      this.connect();
    }, 2500);
  }

  public subscribe(handler: MessageHandler): () => void {
    this.handlers.add(handler);
    return () => {
      this.handlers.delete(handler);
    };
  }

  public send(data: any): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  public isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }
}

export const wsService = new WebSocketService();
