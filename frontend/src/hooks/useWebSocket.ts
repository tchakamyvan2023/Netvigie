import { useEffect, useRef, useState } from 'react'

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://192.168.1.40:8000/api/v1/ws/live'

export interface WsMessage {
  type: string
  data: Record<string, unknown>
}

export function useWebSocket(onMessage: (msg: WsMessage) => void) {
  const [connected, setConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const onMessageRef = useRef(onMessage)
  onMessageRef.current = onMessage

  useEffect(() => {
    let reconnectTimeout: ReturnType<typeof setTimeout> | null = null

    const connect = () => {
      const ws = new WebSocket(WS_URL)
      wsRef.current = ws

      ws.onopen = () => setConnected(true)
      ws.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data) as WsMessage
          onMessageRef.current(msg)
        } catch {
          // ignore
        }
      }
      ws.onclose = () => {
        setConnected(false)
        reconnectTimeout = setTimeout(connect, 3000)
      }
      ws.onerror = () => ws.close()
    }

    connect()
    return () => {
      if (reconnectTimeout) clearTimeout(reconnectTimeout)
      wsRef.current?.close()
    }
  }, [])

  return { connected }
}