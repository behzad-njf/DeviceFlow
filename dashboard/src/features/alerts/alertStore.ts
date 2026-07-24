import { create } from 'zustand'

export type AlertItem = {
  id: string
  severity: string
  title: string
  body: string
  createdAt: number
}

type AlertState = {
  alerts: AlertItem[]
  push: (alert: Omit<AlertItem, 'id' | 'createdAt'>) => void
  dismiss: (id: string) => void
  clear: () => void
}

export const useAlertStore = create<AlertState>((set) => ({
  alerts: [],
  push: (alert) =>
    set((state) => ({
      alerts: [
        {
          ...alert,
          id: crypto.randomUUID(),
          createdAt: Date.now(),
        },
        ...state.alerts,
      ].slice(0, 20),
    })),
  dismiss: (id) =>
    set((state) => ({ alerts: state.alerts.filter((a) => a.id !== id) })),
  clear: () => set({ alerts: [] }),
}))
