import { useCallback, useEffect, useState } from 'react'

/**
 * Minimal hash-based router. `validIds` constrains which ids are accepted;
 * anything else (or an empty hash) falls back to `fallbackId`. Returns the
 * current id and a `navigate` setter that updates the URL hash.
 */
export function useHashRoute(validIds: Set<string>, fallbackId: string) {
  const read = useCallback((): string => {
    const id = window.location.hash.replace(/^#\/?/, '')
    return validIds.has(id) ? id : fallbackId
  }, [validIds, fallbackId])

  const [currentId, setCurrentId] = useState<string>(read)

  useEffect(() => {
    const onHash = () => setCurrentId(read())
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [read])

  const navigate = useCallback((id: string) => {
    window.location.hash = `/${id}`
    setCurrentId(id)
  }, [])

  return { currentId, navigate }
}
