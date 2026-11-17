import { useEffect, useRef } from 'react'

export function usePolling(fn: () => Promise<void> | void, intervalMs: number, enabled = true) {
  const fnRef = useRef(fn)
  fnRef.current = fn

  useEffect(() => {
    if (!enabled) return
    let cancelled = false
    const tick = async () => {
      if (cancelled) return
      try {
        await fnRef.current()
      } catch (e) {
        console.error(e)
      }
    }
    tick()
    const id = setInterval(tick, intervalMs)
    return () => {
      cancelled = true
      clearInterval(id)
    }
  }, [intervalMs, enabled])
}