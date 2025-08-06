import React, { useState, useEffect } from 'react'
import { X, FileText, Loader2, AlertCircle } from 'lucide-react'

interface ContentPreviewProps {
  filename: string
  onClose: () => void
}

interface PreviewData {
  success: boolean
  filename: string
  content: string
  size: number
}

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001'

const ContentPreview: React.FC<ContentPreviewProps> = ({ filename, onClose }) => {
  const [previewData, setPreviewData] = useState<PreviewData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const loadPreview = async () => {
      try {
        setLoading(true)
        setError(null)
        
        const response = await fetch(`${API_BASE}/api/content/preview/${encodeURIComponent(filename)}`)
        
        if (!response.ok) {
          const errorData = await response.json().catch(() => ({ detail: 'Failed to load file' }))
          throw new Error(errorData.detail || `HTTP ${response.status}`)
        }
        
        const data = await response.json()
        setPreviewData(data)
      } catch (err) {
        console.error('Error loading preview:', err)
        setError(err instanceof Error ? err.message : 'Failed to load file content')
      } finally {
        setLoading(false)
      }
    }

    loadPreview()
  }, [filename])

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} bytes`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose()
    }
  }

  return (
    <div 
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
      onClick={handleBackdropClick}
    >
      <div className="bg-card-bg rounded-2xl w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <FileText className="w-6 h-6 text-primary" />
            <div>
              <h2 className="text-xl font-semibold text-gray-800">{filename}</h2>
              {previewData && (
                <p className="text-sm text-gray-600">
                  {formatFileSize(previewData.size)} • Text file
                </p>
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-gray-100 text-gray-600 transition-colors"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-6">
          {loading && (
            <div className="flex items-center justify-center h-64">
              <div className="text-center">
                <Loader2 className="w-8 h-8 animate-spin text-primary mx-auto mb-4" />
                <p className="text-gray-600">Loading file content...</p>
              </div>
            </div>
          )}

          {error && (
            <div className="flex items-center justify-center h-64">
              <div className="text-center">
                <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-800 mb-2">Failed to load file</h3>
                <p className="text-gray-600 mb-4">{error}</p>
                <button
                  onClick={onClose}
                  className="px-4 py-2 bg-primary hover:bg-primary-dark text-white rounded-lg transition-colors"
                >
                  Close
                </button>
              </div>
            </div>
          )}

          {previewData && !loading && !error && (
            <pre className="text-sm text-gray-800 whitespace-pre-wrap font-mono bg-gray-50 p-4 rounded-lg border">
              {previewData.content}
            </pre>
          )}
        </div>

        {/* Footer */}
        {previewData && !loading && !error && (
          <div className="p-6 border-t border-gray-200">
            <div className="flex items-center justify-end">
              <button
                onClick={onClose}
                className="px-6 py-2 bg-primary hover:bg-primary-dark text-white rounded-lg font-medium transition-colors"
              >
                Close Preview
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default ContentPreview