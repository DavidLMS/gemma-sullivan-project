import React, { useState, useRef, useCallback } from 'react'
import { X, Upload, FileText, AlertCircle, CheckCircle, Loader2 } from 'lucide-react'

interface FileUploadProps {
  onClose: () => void
  onUploadSuccess: () => void
}

interface UploadState {
  status: 'idle' | 'uploading' | 'success' | 'error'
  message: string
  progress?: number
}

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001'

const FileUpload: React.FC<FileUploadProps> = ({ onClose, onUploadSuccess }) => {
  const [dragOver, setDragOver] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploadState, setUploadState] = useState<UploadState>({ status: 'idle', message: '' })
  const fileInputRef = useRef<HTMLInputElement>(null)

  const validateFile = (file: File): string | null => {
    // Check file type
    if (!file.name.toLowerCase().endsWith('.txt')) {
      return 'Only .txt files are allowed'
    }

    // Check file size (10MB max)
    if (file.size > 10 * 1024 * 1024) {
      return 'File size must be less than 10MB'
    }

    // Check for valid filename
    if (file.name.includes('..') || file.name.includes('/') || file.name.includes('\\')) {
      return 'Invalid filename. Please use a simple filename without special characters.'
    }

    return null
  }

  const handleFileSelect = useCallback((file: File) => {
    const error = validateFile(file)
    if (error) {
      setUploadState({ status: 'error', message: error })
      setSelectedFile(null)
      return
    }

    setSelectedFile(file)
    setUploadState({ status: 'idle', message: '' })
  }, [])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)

    const files = Array.from(e.dataTransfer.files)
    if (files.length === 0) return

    if (files.length > 1) {
      setUploadState({ status: 'error', message: 'Please select only one file at a time' })
      return
    }

    handleFileSelect(files[0])
  }, [handleFileSelect])

  const handleFileInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files && files.length > 0) {
      handleFileSelect(files[0])
    }
  }, [handleFileSelect])

  const handleUpload = async () => {
    if (!selectedFile) return

    try {
      setUploadState({ status: 'uploading', message: 'Uploading file...', progress: 0 })

      const formData = new FormData()
      formData.append('file', selectedFile)

      const response = await fetch(`${API_BASE}/api/content/upload`, {
        method: 'POST',
        body: formData
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Upload failed' }))
        throw new Error(errorData.detail || `HTTP ${response.status}`)
      }

      const result = await response.json()
      setUploadState({ 
        status: 'success', 
        message: `File "${result.filename}" uploaded successfully!`
      })

      // Notify parent component to refresh file list
      setTimeout(() => {
        onUploadSuccess()
        onClose()
      }, 1500)

    } catch (error) {
      console.error('Upload error:', error)
      setUploadState({ 
        status: 'error', 
        message: error instanceof Error ? error.message : 'Upload failed'
      })
    }
  }

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose()
    }
  }

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} bytes`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  return (
    <div 
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
      onClick={handleBackdropClick}
    >
      <div className="bg-card-bg rounded-2xl w-full max-w-2xl shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <Upload className="w-6 h-6 text-primary" />
            <h2 className="text-xl font-semibold text-gray-800">Upload Content File</h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-gray-100 text-gray-600 transition-colors"
            disabled={uploadState.status === 'uploading'}
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {/* Upload Area */}
          <div
            className={`relative border-2 border-dashed rounded-xl p-8 text-center transition-all ${
              dragOver
                ? 'border-primary bg-primary/5'
                : selectedFile
                ? 'border-green-300 bg-green-50'
                : 'border-gray-300 hover:border-gray-400'
            }`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".txt"
              onChange={handleFileInputChange}
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
              disabled={uploadState.status === 'uploading'}
            />

            {!selectedFile ? (
              <div>
                <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-800 mb-2">
                  Drop your .txt file here
                </h3>
                <p className="text-gray-600 mb-4">
                  or click to browse your files
                </p>
                <div className="text-sm text-gray-500">
                  <p>• Only .txt files are supported</p>
                  <p>• Maximum file size: 10MB</p>
                </div>
              </div>
            ) : (
              <div>
                <FileText className="w-12 h-12 text-green-600 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-800 mb-2">
                  {selectedFile.name}
                </h3>
                <p className="text-gray-600 mb-4">
                  {formatFileSize(selectedFile.size)} • Ready to upload
                </p>
                <button
                  onClick={() => {
                    setSelectedFile(null)
                    setUploadState({ status: 'idle', message: '' })
                  }}
                  className="text-sm text-gray-500 hover:text-gray-700 underline"
                  disabled={uploadState.status === 'uploading'}
                >
                  Choose different file
                </button>
              </div>
            )}
          </div>

          {/* Status Messages */}
          {uploadState.message && (
            <div className={`mt-4 p-4 rounded-lg flex items-center gap-3 ${
              uploadState.status === 'error'
                ? 'bg-red-50 text-red-700 border border-red-200'
                : uploadState.status === 'success'
                ? 'bg-green-50 text-green-700 border border-green-200'
                : 'bg-blue-50 text-blue-700 border border-blue-200'
            }`}>
              {uploadState.status === 'uploading' && <Loader2 className="w-5 h-5 animate-spin" />}
              {uploadState.status === 'error' && <AlertCircle className="w-5 h-5" />}
              {uploadState.status === 'success' && <CheckCircle className="w-5 h-5" />}
              <span>{uploadState.message}</span>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-gray-200">
          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="flex-1 px-4 py-3 rounded-xl font-medium bg-gray-100 hover:bg-gray-200 text-gray-700 transition-colors"
              disabled={uploadState.status === 'uploading'}
            >
              Cancel
            </button>
            <button
              onClick={handleUpload}
              disabled={!selectedFile || uploadState.status === 'uploading' || uploadState.status === 'success'}
              className="flex-1 px-4 py-3 bg-primary hover:bg-primary-dark disabled:bg-gray-300 disabled:cursor-not-allowed text-white rounded-xl font-medium transition-all duration-300 flex items-center justify-center gap-2"
            >
              {uploadState.status === 'uploading' ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Uploading...
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4" />
                  Upload File
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default FileUpload