import { useState, useCallback } from 'react'
import axios from 'axios'

interface ApiResponse<T> {
  data: T | null
  loading: boolean
  error: string | null
}

export function useApi<T>(url: string, initialData: T | null = null) {
  const [state, setState] = useState<ApiResponse<T>>({
    data: initialData,
    loading: true,
    error: null,
  })

  const fetch = useCallback(async () => {
    try {
      setState((prev) => ({ ...prev, loading: true, error: null }))
      const response = await axios.get<T>(url)
      setState({ data: response.data, loading: false, error: null })
      return response.data
    } catch (error) {
      setState((prev) => ({
        ...prev,
        loading: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      }))
      return null
    }
  }, [url])

  const post = useCallback(async (data: unknown) => {
    try {
      setState((prev) => ({ ...prev, loading: true, error: null }))
      const response = await axios.post<T>(url, data)
      setState({ data: response.data, loading: false, error: null })
      return response.data
    } catch (error) {
      setState((prev) => ({
        ...prev,
        loading: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      }))
      return null
    }
  }, [url])

  return { ...state, fetch, post }
}