import React, { useState, useEffect } from 'react'
import { 
  ArrowLeft, 
  Folder, 
  File, 
  Download, 
  Eye, 
  X, 
  ChevronRight,
  FileText,
  Image,
  Calendar,
  HardDrive,
  Loader2
} from 'lucide-react'

interface FileItem {
  name: string
  type: 'file' | 'directory'
  path: string
  size?: number
  modified: string | null
  mime_type?: string | null
}

interface BrowseResponse {
  success: boolean
  type?: 'file' | 'directory'
  path: string
  items?: FileItem[]
  parent?: string | null
  name?: string
  size?: number
  modified?: string
  mime_type?: string
}

interface FileContentResponse {
  success: boolean
  type?: 'text' | 'image'
  content?: string
  mime_type?: string
  download_url?: string
  error?: string
}

interface FileBrowserProps {
  studentId: string
  studentName: string
  initialFolder: 'students' | 'reports'
  onClose: () => void
}

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001'

const FileBrowser: React.FC<FileBrowserProps> = ({ 
  studentId, 
  studentName, 
  initialFolder, 
  onClose 
}) => {
  const [currentPath, setCurrentPath] = useState<string>('')
  const [items, setItems] = useState<FileItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedFile, setSelectedFile] = useState<FileItem | null>(null)
  const [fileContent, setFileContent] = useState<FileContentResponse | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [breadcrumbs, setBreadcrumbs] = useState<Array<{name: string, path: string}>>([])

  // Initialize with the selected folder
  useEffect(() => {
    const initPath = initialFolder === 'reports' ? 'reports' : 'students'
    setCurrentPath(initPath)
    loadDirectory(initPath)
  }, [initialFolder, studentId])

  // Update breadcrumbs when path changes
  useEffect(() => {
    updateBreadcrumbs(currentPath)
  }, [currentPath])

  const updateBreadcrumbs = (path: string) => {
    const crumbs: Array<{name: string, path: string}> = [
      { name: 'Root', path: '' }
    ]
    
    if (path) {
      const parts = path.split('/')
      let accumPath = ''
      
      parts.forEach((part) => {
        accumPath = accumPath ? `${accumPath}/${part}` : part
        const displayName = part === 'students' ? `Student (${studentName})` : 
                           part === 'reports' ? `Reports (${studentName})` : part
        crumbs.push({
          name: displayName,
          path: accumPath
        })
      })
    }
    
    setBreadcrumbs(crumbs)
  }

  const loadDirectory = async (path: string) => {
    setLoading(true)
    setError(null)
    
    try {
      const response = await fetch(`${API_BASE}/api/files/browse/${studentId}?path=${encodeURIComponent(path)}`)
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      
      const data: BrowseResponse = await response.json()
      
      if (!data.success) {
        throw new Error('Failed to load directory')
      }
      
      setItems(data.items || [])
      setCurrentPath(path)
      
    } catch (err) {
      console.error('Error loading directory:', err)
      setError(err instanceof Error ? err.message : 'Failed to load directory')
    } finally {
      setLoading(false)
    }
  }

  const handleItemClick = (item: FileItem) => {
    if (item.type === 'directory') {
      loadDirectory(item.path)
    } else {
      setSelectedFile(item)
      loadFilePreview(item)
    }
  }

  const loadFilePreview = async (file: FileItem) => {
    setPreviewLoading(true)
    setFileContent(null)
    
    try {
      const response = await fetch(`${API_BASE}/api/files/content/${studentId}?path=${encodeURIComponent(file.path)}`)
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      
      const data: FileContentResponse = await response.json()
      setFileContent(data)
      
    } catch (err) {
      console.error('Error loading file preview:', err)
      setFileContent({
        success: false,
        error: err instanceof Error ? err.message : 'Failed to load file preview'
      })
    } finally {
      setPreviewLoading(false)
    }
  }

  const navigateUp = () => {
    if (currentPath) {
      const parts = currentPath.split('/')
      if (parts.length > 1) {
        const parentPath = parts.slice(0, -1).join('/')
        loadDirectory(parentPath)
      } else {
        loadDirectory('')
      }
    }
  }

  const navigateToBreadcrumb = (path: string) => {
    loadDirectory(path)
  }

  const downloadFile = (file: FileItem) => {
    const downloadUrl = `${API_BASE}/api/files/download/${studentId}?path=${encodeURIComponent(file.path)}`
    window.open(downloadUrl, '_blank')
  }

  const formatFileSize = (bytes?: number): string => {
    if (!bytes) return '-'
    
    const units = ['B', 'KB', 'MB', 'GB']
    let size = bytes
    let unitIndex = 0
    
    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024
      unitIndex++
    }
    
    return `${size.toFixed(unitIndex > 0 ? 1 : 0)} ${units[unitIndex]}`
  }

  const formatDate = (dateString: string | null): string => {
    if (!dateString) return '-'
    
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      })
    } catch {
      return dateString
    }
  }

  const getFileIcon = (item: FileItem) => {
    if (item.type === 'directory') {
      return <Folder className="w-5 h-5 text-blue-500" />
    }
    
    if (item.mime_type?.startsWith('image/')) {
      return <Image className="w-5 h-5 text-green-500" />
    }
    
    if (item.mime_type?.startsWith('text/') || item.name.endsWith('.json') || item.name.endsWith('.log')) {
      return <FileText className="w-5 h-5 text-gray-600" />
    }
    
    return <File className="w-5 h-5 text-gray-500" />
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-6xl h-5/6 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex items-center space-x-3">
            <HardDrive className="w-6 h-6 text-primary" />
            <h2 className="text-xl font-semibold text-gray-800">
              File Browser - {studentName}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-gray-100 text-gray-600 transition-colors"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Breadcrumbs */}
        <div className="px-6 py-3 bg-gray-50 border-b border-gray-200">
          <div className="flex items-center space-x-2 text-sm">
            {breadcrumbs.map((crumb, index) => (
              <React.Fragment key={index}>
                {index > 0 && <ChevronRight className="w-4 h-4 text-gray-400" />}
                <button
                  onClick={() => navigateToBreadcrumb(crumb.path)}
                  className={`px-2 py-1 rounded hover:bg-gray-200 transition-colors ${
                    index === breadcrumbs.length - 1
                      ? 'text-primary font-medium'
                      : 'text-gray-600 hover:text-gray-800'
                  }`}
                >
                  {crumb.name}
                </button>
              </React.Fragment>
            ))}
          </div>
        </div>

        <div className="flex flex-1 overflow-hidden">
          {/* File List */}
          <div className="flex-1 flex flex-col">
            {/* Toolbar */}
            <div className="px-6 py-3 bg-gray-50 border-b border-gray-200 flex items-center justify-between">
              <button
                onClick={navigateUp}
                disabled={!currentPath}
                className="flex items-center space-x-2 px-3 py-2 rounded-lg bg-white border border-gray-300 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <ArrowLeft className="w-4 h-4" />
                <span className="text-sm">Up</span>
              </button>
              
              <div className="text-sm text-gray-600">
                {items.length} items
              </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-auto">
              {loading ? (
                <div className="flex items-center justify-center h-full">
                  <div className="text-center">
                    <Loader2 className="w-8 h-8 animate-spin text-primary mx-auto mb-4" />
                    <p className="text-gray-600">Loading directory...</p>
                  </div>
                </div>
              ) : error ? (
                <div className="flex items-center justify-center h-full">
                  <div className="text-center">
                    <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
                      <X className="w-8 h-8 text-red-500" />
                    </div>
                    <p className="text-red-600 font-medium mb-2">Error loading directory</p>
                    <p className="text-gray-600 text-sm">{error}</p>
                    <button
                      onClick={() => loadDirectory(currentPath)}
                      className="mt-4 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-dark transition-colors"
                    >
                      Retry
                    </button>
                  </div>
                </div>
              ) : (
                <div className="divide-y divide-gray-200">
                  {items.map((item, index) => (
                    <div
                      key={index}
                      onClick={() => handleItemClick(item)}
                      className={`flex items-center space-x-3 p-4 hover:bg-gray-50 cursor-pointer transition-colors ${
                        selectedFile?.path === item.path ? 'bg-blue-50 border-l-4 border-l-primary' : ''
                      }`}
                    >
                      <div className="flex-shrink-0">
                        {getFileIcon(item)}
                      </div>
                      
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-2">
                          <p className="text-sm font-medium text-gray-900 truncate">
                            {item.name}
                          </p>
                          {item.type === 'directory' && (
                            <ChevronRight className="w-4 h-4 text-gray-400" />
                          )}
                        </div>
                        <div className="flex items-center space-x-4 mt-1 text-xs text-gray-500">
                          <span className="flex items-center space-x-1">
                            <Calendar className="w-3 h-3" />
                            <span>{formatDate(item.modified)}</span>
                          </span>
                          {item.type === 'file' && (
                            <span>{formatFileSize(item.size)}</span>
                          )}
                        </div>
                      </div>
                      
                      {item.type === 'file' && (
                        <div className="flex items-center space-x-2">
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              setSelectedFile(item)
                              loadFilePreview(item)
                            }}
                            className="p-2 rounded-lg hover:bg-gray-200 text-gray-600 transition-colors"
                            title="Preview"
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              downloadFile(item)
                            }}
                            className="p-2 rounded-lg hover:bg-gray-200 text-gray-600 transition-colors"
                            title="Download"
                          >
                            <Download className="w-4 h-4" />
                          </button>
                        </div>
                      )}
                    </div>
                  ))}
                  
                  {items.length === 0 && (
                    <div className="flex items-center justify-center h-64">
                      <div className="text-center">
                        <Folder className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                        <p className="text-gray-500">This folder is empty</p>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* File Preview Panel */}
          {selectedFile && (
            <div className="w-1/2 border-l border-gray-200 flex flex-col">
              <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
                <div className="flex items-center justify-between">
                  <h3 className="font-medium text-gray-800">File Preview</h3>
                  <button
                    onClick={() => setSelectedFile(null)}
                    className="p-1 rounded hover:bg-gray-200 text-gray-600"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
                <p className="text-sm text-gray-600 mt-1 truncate">{selectedFile.name}</p>
              </div>
              
              <div className="flex-1 overflow-auto p-6">
                {previewLoading ? (
                  <div className="flex items-center justify-center h-full">
                    <Loader2 className="w-6 h-6 animate-spin text-primary" />
                  </div>
                ) : fileContent ? (
                  fileContent.success ? (
                    fileContent.type === 'text' ? (
                      <pre className="text-sm text-gray-800 whitespace-pre-wrap font-mono bg-gray-50 p-4 rounded-lg border">
                        {fileContent.content}
                      </pre>
                    ) : fileContent.type === 'image' ? (
                      <div className="text-center">
                        <img
                          src={`${API_BASE}${fileContent.download_url}`}
                          alt={selectedFile.name}
                          className="max-w-full max-h-96 mx-auto rounded-lg shadow-md"
                        />
                      </div>
                    ) : (
                      <div className="text-center text-gray-500">
                        <File className="w-16 h-16 mx-auto mb-4 text-gray-300" />
                        <p>Preview not available for this file type</p>
                        <button
                          onClick={() => downloadFile(selectedFile)}
                          className="mt-4 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-dark transition-colors flex items-center space-x-2 mx-auto"
                        >
                          <Download className="w-4 h-4" />
                          <span>Download</span>
                        </button>
                      </div>
                    )
                  ) : (
                    <div className="text-center text-red-600">
                      <X className="w-16 h-16 mx-auto mb-4 text-red-300" />
                      <p className="font-medium">Preview Error</p>
                      <p className="text-sm text-gray-600 mt-2">{fileContent.error}</p>
                    </div>
                  )
                ) : (
                  <div className="text-center text-gray-500">
                    <Eye className="w-16 h-16 mx-auto mb-4 text-gray-300" />
                    <p>Select a file to preview</p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default FileBrowser