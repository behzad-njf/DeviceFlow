type Listener = (event: DashboardEvent) => void

export type DashboardEvent = {
  v?: number
  type: string
  ts?: string | null
  payload?: Record<string, unknown>
}

export type WsStatus = 'disconnected' | 'connecting' | 'connected'

export class DashboardSocket {
  private socket: WebSocket | null = null
  private listeners = new Set<Listener>()
  private statusListeners = new Set<(status: WsStatus) => void>()
  private token: string | null = null
  private shouldRun = false
  private retryMs = 1000

  connect(token: string) {
    this.token = token
    this.shouldRun = true
    this.open()
  }

  disconnect() {
    this.shouldRun = false
    this.socket?.close()
    this.socket = null
    this.setStatus('disconnected')
  }

  onEvent(listener: Listener) {
    this.listeners.add(listener)
    return () => {
      this.listeners.delete(listener)
    }
  }

  onStatus(listener: (status: WsStatus) => void) {
    this.statusListeners.add(listener)
    return () => {
      this.statusListeners.delete(listener)
    }
  }

  private setStatus(status: WsStatus) {
    this.statusListeners.forEach((l) => l(status))
  }

  private open() {
    if (!this.token || !this.shouldRun) return
    this.setStatus('connecting')
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const host = window.location.host
    const url = `${proto}://${host}/ws/dashboard/?token=${encodeURIComponent(this.token)}`
    const socket = new WebSocket(url)
    this.socket = socket

    socket.onopen = () => {
      this.retryMs = 1000
      this.setStatus('connected')
      socket.send(JSON.stringify({ type: 'subscribe', payload: { rooms: ['devices'] } }))
    }
    socket.onmessage = (msg) => {
      try {
        const data = JSON.parse(msg.data) as DashboardEvent
        this.listeners.forEach((l) => l(data))
      } catch {
        // ignore malformed frames
      }
    }
    socket.onclose = () => {
      this.setStatus('disconnected')
      if (!this.shouldRun) return
      window.setTimeout(() => this.open(), this.retryMs)
      this.retryMs = Math.min(this.retryMs * 2, 15000)
    }
  }
}

export const dashboardSocket = new DashboardSocket()
