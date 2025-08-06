import { useState, useEffect } from 'react'
import { 
  RefreshCw, 
  ChevronRight, 
  ChevronLeft, 
  ChevronsRight, 
  ChevronsLeft,
  X,
  Folder,
  FileText,
  Wifi,
  WifiOff,
  Eye,
  Upload,
  Trash2,
  Edit3
} from 'lucide-react'
import FileBrowser from './components/FileBrowser'
import ContentPreview from './components/ContentPreview'
import FileUpload from './components/FileUpload'

interface Student {
  id: string
  name: string
  display_name?: string
}

interface ContentFile {
  name: string
  checked: boolean
}

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001'

function App() {
  const [students, setStudents] = useState<Student[]>([])
  const [selectedStudent, setSelectedStudent] = useState<Student | null>(null)
  const [showMobileDrawer, setShowMobileDrawer] = useState(false)
  
  const [availableFiles, setAvailableFiles] = useState<ContentFile[]>([])
  const [assignedFiles, setAssignedFiles] = useState<ContentFile[]>([])
  
  // Edit display name state
  const [showEditModal, setShowEditModal] = useState(false)
  const [editingDisplayName, setEditingDisplayName] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isWifiEnabled, setIsWifiEnabled] = useState<boolean>(false)
  
  // File browser state
  const [showFileBrowser, setShowFileBrowser] = useState(false)
  const [fileBrowserConfig, setFileBrowserConfig] = useState<{
    studentId: string
    studentName: string
    initialFolder: 'students' | 'reports'
  } | null>(null)

  // Content preview state
  const [showContentPreview, setShowContentPreview] = useState(false)
  const [previewFilename, setPreviewFilename] = useState<string | null>(null)

  // File upload state
  const [showFileUpload, setShowFileUpload] = useState(false)

  // Load initial data
  useEffect(() => {
    loadStudents()
    loadAvailableFiles()
    checkDiscoveryStatus()
  }, [])

  const checkDiscoveryStatus = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/sync/discovery/status`)
      if (response.ok) {
        const data = await response.json()
        setIsWifiEnabled(data.is_running)
        localStorage.setItem('tutorWifiEnabled', JSON.stringify(data.is_running))
      }
    } catch (error) {
      console.error('Error checking discovery status:', error)
      // Fallback to localStorage
      const savedWifiState = localStorage.getItem('tutorWifiEnabled')
      if (savedWifiState !== null) {
        setIsWifiEnabled(JSON.parse(savedWifiState))
      }
    }
  }

  // Load assigned files when student changes
  useEffect(() => {
    if (selectedStudent) {
      loadAssignedFiles(selectedStudent.id)
    }
  }, [selectedStudent])

  const loadStudents = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/students`)
      if (response.ok) {
        const data = await response.json()
        setStudents(data.students || [])
        if (data.students && data.students.length > 0) {
          setSelectedStudent(data.students[0])
        }
      }
    } catch (error) {
      console.error('Error loading students:', error)
      setError('Failed to load students')
    } finally {
      setLoading(false)
    }
  }

  const loadAvailableFiles = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/content/available`)
      if (response.ok) {
        const data = await response.json()
        setAvailableFiles(data.files?.map((name: string) => ({ name, checked: false })) || [])
      }
    } catch (error) {
      console.error('Error loading available files:', error)
    }
  }

  const loadAssignedFiles = async (studentId: string) => {
    try {
      const response = await fetch(`${API_BASE}/api/students/${studentId}/assigned`)
      if (response.ok) {
        const data = await response.json()
        setAssignedFiles(data.files?.map((name: string) => ({ name, checked: false })) || [])
        
        // Remove assigned files from available list
        setAvailableFiles(prev => prev.filter(file => 
          !data.files?.includes(file.name)
        ))
      }
    } catch (error) {
      console.error('Error loading assigned files:', error)
    }
  }

  const handleEditDisplayName = () => {
    if (selectedStudent) {
      setEditingDisplayName(selectedStudent.display_name || selectedStudent.name)
      setShowEditModal(true)
    }
  }

  const handleSaveDisplayName = async () => {
    if (!selectedStudent || !editingDisplayName.trim()) return

    try {
      const response = await fetch(`${API_BASE}/api/students/${selectedStudent.id}/display-name`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          display_name: editingDisplayName.trim()
        })
      })

      if (response.ok) {
        const result = await response.json()
        // Update local state
        const updatedStudents = students.map(student => 
          student.id === selectedStudent.id 
            ? { ...student, display_name: result.display_name }
            : student
        )
        setStudents(updatedStudents)
        setSelectedStudent({ ...selectedStudent, display_name: result.display_name })
        setShowEditModal(false)
        setEditingDisplayName('')
      } else {
        const errorData = await response.json()
        setError(errorData.detail || 'Failed to update display name')
      }
    } catch (error) {
      console.error('Error updating display name:', error)
      setError('Failed to update display name')
    }
  }

  const handleDeleteStudent = async () => {
    if (!selectedStudent) return

    const studentName = selectedStudent.display_name || selectedStudent.name
    if (!confirm(`Are you sure you want to delete student "${studentName}" (ID: ${selectedStudent.id})?\n\nThis will permanently delete all their assigned content and reports. This action cannot be undone.`)) {
      return
    }

    try {
      const response = await fetch(`${API_BASE}/api/students/${selectedStudent.id}`, {
        method: 'DELETE'
      })

      if (response.ok) {
        // Remove from students list
        const updatedStudents = students.filter(student => student.id !== selectedStudent.id)
        setStudents(updatedStudents)
        
        // Clear selection and assigned files
        setSelectedStudent(updatedStudents.length > 0 ? updatedStudents[0] : null)
        setAssignedFiles([])
        
        // Reload available files to refresh the list
        loadAvailableFiles()
      } else {
        const errorData = await response.json().catch(() => ({ detail: 'Failed to delete student' }))
        setError(errorData.detail || 'Failed to delete student')
      }
    } catch (error) {
      console.error('Error deleting student:', error)
      setError('Failed to delete student')
    }
  }

  const handleMoveToAssigned = async () => {
    const selectedFiles = availableFiles.filter(file => file.checked)
    if (!selectedStudent || selectedFiles.length === 0) return

    try {
      const response = await fetch(`${API_BASE}/api/students/${selectedStudent.id}/assign`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          files: selectedFiles.map(f => f.name)
        })
      })

      if (response.ok) {
        setAssignedFiles([...assignedFiles, ...selectedFiles.map(f => ({ ...f, checked: false }))])
        setAvailableFiles(availableFiles.filter(file => !file.checked))
      }
    } catch (error) {
      console.error('Error assigning files:', error)
    }
  }

  const handleMoveToAvailable = async () => {
    const selectedFiles = assignedFiles.filter(file => file.checked)
    if (!selectedStudent || selectedFiles.length === 0) return

    try {
      const response = await fetch(`${API_BASE}/api/students/${selectedStudent.id}/unassign`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          files: selectedFiles.map(f => f.name)
        })
      })

      if (response.ok) {
        setAvailableFiles([...availableFiles, ...selectedFiles.map(f => ({ ...f, checked: false }))])
        setAssignedFiles(assignedFiles.filter(file => !file.checked))
      }
    } catch (error) {
      console.error('Error unassigning files:', error)
    }
  }

  const handleMoveAllToAssigned = async () => {
    if (!selectedStudent || availableFiles.length === 0) return

    try {
      const response = await fetch(`${API_BASE}/api/students/${selectedStudent.id}/assign`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          files: availableFiles.map(f => f.name)
        })
      })

      if (response.ok) {
        setAssignedFiles([...assignedFiles, ...availableFiles.map(f => ({ ...f, checked: false }))])
        setAvailableFiles([])
      }
    } catch (error) {
      console.error('Error assigning all files:', error)
    }
  }

  const handleMoveAllToAvailable = async () => {
    if (!selectedStudent || assignedFiles.length === 0) return

    try {
      const response = await fetch(`${API_BASE}/api/students/${selectedStudent.id}/unassign`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          files: assignedFiles.map(f => f.name)
        })
      })

      if (response.ok) {
        setAvailableFiles([...availableFiles, ...assignedFiles.map(f => ({ ...f, checked: false }))])
        setAssignedFiles([])
      }
    } catch (error) {
      console.error('Error unassigning all files:', error)
    }
  }

  const openStudentFolder = () => {
    if (selectedStudent) {
      setFileBrowserConfig({
        studentId: selectedStudent.id,
        studentName: selectedStudent.display_name || selectedStudent.name,
        initialFolder: 'students'
      })
      setShowFileBrowser(true)
    }
  }

  const openReportsFolder = () => {
    if (selectedStudent) {
      setFileBrowserConfig({
        studentId: selectedStudent.id,
        studentName: selectedStudent.display_name || selectedStudent.name,
        initialFolder: 'reports'
      })
      setShowFileBrowser(true)
    }
  }

  const closeFileBrowser = () => {
    setShowFileBrowser(false)
    setFileBrowserConfig(null)
  }

  const openContentPreview = (filename: string) => {
    setPreviewFilename(filename)
    setShowContentPreview(true)
  }

  const closeContentPreview = () => {
    setShowContentPreview(false)
    setPreviewFilename(null)
  }

  const openFileUpload = () => {
    setShowFileUpload(true)
  }

  const closeFileUpload = () => {
    setShowFileUpload(false)
  }

  const handleUploadSuccess = () => {
    // Refresh the available files list
    loadAvailableFiles()
  }

  const handleDeleteFile = async (filename: string) => {
    // Confirm deletion
    if (!confirm(`Are you sure you want to delete "${filename}"?`)) {
      return
    }

    try {
      const response = await fetch(`${API_BASE}/api/content/${encodeURIComponent(filename)}`, {
        method: 'DELETE'
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Failed to delete file' }))
        throw new Error(errorData.detail || `HTTP ${response.status}`)
      }

      const result = await response.json()
      console.log('File deleted successfully:', result.message)
      
      // Refresh the available files list
      loadAvailableFiles()
      
    } catch (error) {
      console.error('Error deleting file:', error)
      setError(error instanceof Error ? error.message : 'Failed to delete file')
    }
  }

  const notifyStudentApp = async (syncEnabled: boolean) => {
    try {
      console.log(`Notifying student-app: sync ${syncEnabled ? 'enabled' : 'disabled'}`)
      const response = await fetch('${API_BASE}/api/sync/notify-status-change', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          sync_enabled: syncEnabled
        })
      })
      
      if (response.ok) {
        const data = await response.json()
        console.log('✅ Student-app notified successfully:', data.message)
      } else {
        const errorText = await response.text()
        console.warn('⚠️ Failed to notify student-app:', response.status, errorText)
      }
    } catch (error) {
      console.warn('⚠️ Could not reach student-app for notification:', error)
      // This is not a critical error - student-app might not be running
    }
  }

  const toggleWifi = async () => {
    const newWifiState = !isWifiEnabled
    
    try {
      if (newWifiState) {
        // Start discovery service
        const response = await fetch(`${API_BASE}/api/sync/discovery/start`, {
          method: 'POST'
        })
        if (response.ok) {
          setIsWifiEnabled(true)
          localStorage.setItem('tutorWifiEnabled', JSON.stringify(true))
          console.log('Discovery service started')
          
          // Notify student-app immediately
          await notifyStudentApp(true)
        } else {
          throw new Error('Failed to start discovery service')
        }
      } else {
        // Stop discovery service
        const response = await fetch(`${API_BASE}/api/sync/discovery/stop`, {
          method: 'POST'
        })
        if (response.ok) {
          setIsWifiEnabled(false)
          localStorage.setItem('tutorWifiEnabled', JSON.stringify(false))
          console.log('Discovery service stopped')
          
          // Notify student-app immediately
          await notifyStudentApp(false)
        } else {
          throw new Error('Failed to stop discovery service')
        }
      }
    } catch (error) {
      console.error('Error toggling wifi/sync service:', error)
      setError('Failed to toggle sync service')
    }
  }


  if (loading) {
    return (
      <div className="min-h-screen bg-app-bg flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 animate-spin text-primary mx-auto mb-4" />
          <p className="text-gray-600">Loading tutor console...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-app-bg">
      
      {/* Header */}
      <header className="bg-card-bg border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-6 py-4 grid grid-cols-3 items-center">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center">
              <img 
                src="/logo.svg" 
                alt="Gemma Logo" 
                className="w-8 h-8 object-contain"
              />
            </div>
            <span className="font-medium text-gray-600">Gemma Sullivan Project</span>
          </div>
          
          <h1 className="text-xl font-semibold text-gray-800 text-center">Tutor Console</h1>
          
          <div className="flex items-center justify-end space-x-3">
            {/* Wifi Toggle Button */}
            <button
              onClick={toggleWifi}
              className={`p-2 rounded-lg transition-all duration-300 ${
                isWifiEnabled
                  ? 'bg-green-50 hover:bg-green-100 text-green-600 hover:text-green-700'
                  : 'bg-gray-50 hover:bg-gray-100 text-gray-400 hover:text-gray-500'
              }`}
              title={isWifiEnabled ? 'Sync enabled - Connected' : 'Sync disabled - Click to enable'}
            >
              {isWifiEnabled ? (
                <Wifi className="w-5 h-5" />
              ) : (
                <WifiOff className="w-5 h-5" />
              )}
            </button>
          </div>
        </div>
      </header>

      {/* Error Display */}
      {error && (
        <div className="max-w-6xl mx-auto p-6">
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-center space-x-2">
            <span className="text-red-700">{error}</span>
            <button 
              onClick={() => setError(null)}
              className="text-red-500 hover:text-red-700"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Main Content */}
      <main className="max-w-6xl mx-auto p-6">
        <div className="bg-card-bg rounded-2xl shadow-lg overflow-hidden">
          {/* Gradient Border */}
          <div className="h-1 bg-gradient-to-r from-primary to-primary-light"></div>
          
          <div className="p-8">
            {/* Student Selector Row */}
            <div className="flex items-center gap-3 mb-8">
              <div className="flex-1">
                <select
                  value={selectedStudent?.id || ''}
                  onChange={(e) => {
                    const student = students.find(s => s.id === e.target.value)
                    setSelectedStudent(student || null)
                  }}
                  className="w-full px-4 py-3 rounded-xl border border-gray-300 bg-gray-50 text-gray-900 focus:border-primary focus:ring-2 focus:ring-primary/20 focus:outline-none transition-colors"
                >
                  <option value="">Select student</option>
                  {students.map(student => (
                    <option key={student.id} value={student.id}>
                      {student.id} - {student.display_name || student.name}
                    </option>
                  ))}
                </select>
              </div>
              {selectedStudent && (
                <>
                  <button
                    onClick={handleEditDisplayName}
                    className="p-3 rounded-xl hover:bg-gray-100 text-gray-600 hover:text-gray-800 transition-colors"
                    title={`Edit display name for ${selectedStudent.display_name || selectedStudent.name}`}
                  >
                    <Edit3 size={18} />
                  </button>
                  <button
                    onClick={handleDeleteStudent}
                    className="p-3 rounded-xl hover:bg-red-100 text-gray-600 hover:text-red-600 transition-colors"
                    title={`Delete student ${selectedStudent.display_name || selectedStudent.name}`}
                  >
                    <Trash2 size={18} />
                  </button>
                </>
              )}
            </div>

            {/* Dual List Component - Desktop */}
            <div className="hidden lg:block">
              <div className="grid grid-cols-5 gap-6 h-96">
                {/* Available Files */}
                <div className="col-span-2">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="font-medium text-lg text-gray-800">Available .txt files</h3>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={openFileUpload}
                        className="p-2 rounded-lg hover:bg-gray-100 text-gray-600 transition-colors flex items-center gap-1"
                        title="Upload new content file"
                      >
                        <Upload size={16} />
                        <span className="text-sm">Upload</span>
                      </button>
                      <button
                        onClick={loadAvailableFiles}
                        className="p-2 rounded-lg hover:bg-gray-100 text-gray-600 transition-colors"
                        title="Refresh file list"
                      >
                        <RefreshCw size={16} />
                      </button>
                    </div>
                  </div>
                  <div className="border border-gray-200 rounded-xl p-4 h-80 overflow-y-auto bg-gray-50">
                    {availableFiles.map((file, index) => (
                      <div key={index} className="flex items-center gap-3 p-3 rounded-lg hover:bg-white transition-colors">
                        <input
                          type="checkbox"
                          checked={file.checked}
                          onChange={(e) => {
                            const updated = [...availableFiles]
                            updated[index].checked = e.target.checked
                            setAvailableFiles(updated)
                          }}
                          className="w-4 h-4 text-primary rounded focus:ring-2 focus:ring-primary/20"
                        />
                        <span className="flex-1 text-sm text-gray-700">{file.name}</span>
                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => openContentPreview(file.name)}
                            className="p-1 rounded hover:bg-gray-200 text-gray-500 hover:text-gray-700 transition-colors"
                            title={`Preview ${file.name}`}
                          >
                            <Eye size={16} />
                          </button>
                          <button
                            onClick={() => handleDeleteFile(file.name)}
                            className="p-1 rounded hover:bg-red-100 text-gray-500 hover:text-red-600 transition-colors"
                            title={`Delete ${file.name}`}
                          >
                            <Trash2 size={16} />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Center Controls */}
                <div className="col-span-1 flex flex-col items-center justify-center gap-3">
                  <button
                    onClick={handleMoveToAssigned}
                    disabled={!availableFiles.some(f => f.checked) || !selectedStudent}
                    className="p-3 bg-primary hover:bg-primary-dark disabled:bg-gray-300 disabled:cursor-not-allowed text-white rounded-xl transition-all duration-300 shadow-md hover:shadow-lg"
                  >
                    <ChevronRight size={20} />
                  </button>
                  <button
                    onClick={handleMoveToAvailable}
                    disabled={!assignedFiles.some(f => f.checked) || !selectedStudent}
                    className="p-3 bg-primary hover:bg-primary-dark disabled:bg-gray-300 disabled:cursor-not-allowed text-white rounded-xl transition-all duration-300 shadow-md hover:shadow-lg"
                  >
                    <ChevronLeft size={20} />
                  </button>
                  <div className="w-full h-px bg-gray-300 my-2"></div>
                  <button
                    onClick={handleMoveAllToAssigned}
                    disabled={availableFiles.length === 0 || !selectedStudent}
                    className="p-3 bg-practice-green hover:bg-practice-green-dark disabled:bg-gray-300 disabled:cursor-not-allowed text-white rounded-xl transition-all duration-300 shadow-md hover:shadow-lg"
                  >
                    <ChevronsRight size={20} />
                  </button>
                  <button
                    onClick={handleMoveAllToAvailable}
                    disabled={assignedFiles.length === 0 || !selectedStudent}
                    className="p-3 bg-experiment-orange hover:bg-experiment-orange-dark disabled:bg-gray-300 disabled:cursor-not-allowed text-white rounded-xl transition-all duration-300 shadow-md hover:shadow-lg"
                  >
                    <ChevronsLeft size={20} />
                  </button>
                </div>

                {/* Assigned Files */}
                <div className="col-span-2">
                  <h3 className="font-medium text-lg mb-4 text-gray-800">Assigned to student</h3>
                  <div className="border border-gray-200 rounded-xl p-4 h-80 overflow-y-auto bg-gray-50">
                    {assignedFiles.map((file, index) => (
                      <div key={index} className="flex items-center gap-3 p-3 rounded-lg hover:bg-white transition-colors">
                        <input
                          type="checkbox"
                          checked={file.checked}
                          onChange={(e) => {
                            const updated = [...assignedFiles]
                            updated[index].checked = e.target.checked
                            setAssignedFiles(updated)
                          }}
                          className="w-4 h-4 text-primary rounded focus:ring-2 focus:ring-primary/20"
                        />
                        <span className="flex-1 text-sm text-gray-700">{file.name}</span>
                        <button
                          onClick={() => openContentPreview(file.name)}
                          className="p-1 rounded hover:bg-gray-200 text-gray-500 hover:text-gray-700 transition-colors"
                          title={`Preview ${file.name}`}
                        >
                          <Eye size={16} />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* Mobile/Tablet Layout */}
            <div className="lg:hidden space-y-6">
              {/* Available Files */}
              <div>
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-medium text-lg text-gray-800">Available .txt files</h3>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={openFileUpload}
                      className="p-2 rounded-lg hover:bg-gray-100 text-gray-600 transition-colors flex items-center gap-1"
                      title="Upload new content file"
                    >
                      <Upload size={16} />
                      <span className="text-sm">Upload</span>
                    </button>
                    <button
                      onClick={loadAvailableFiles}
                      className="p-2 rounded-lg hover:bg-gray-100 text-gray-600 transition-colors"
                      title="Refresh file list"
                    >
                      <RefreshCw size={16} />
                    </button>
                    <button
                      onClick={() => setShowMobileDrawer(true)}
                      className="px-3 py-2 bg-primary hover:bg-primary-dark text-white rounded-lg text-sm font-medium transition-all duration-300"
                    >
                      Assigned ({assignedFiles.length})
                    </button>
                  </div>
                </div>
                <div className="border border-gray-200 rounded-xl p-4 h-64 overflow-y-auto bg-gray-50">
                  {availableFiles.map((file, index) => (
                    <div key={index} className="flex items-center gap-3 p-3 rounded-lg hover:bg-white transition-colors">
                      <input
                        type="checkbox"
                        checked={file.checked}
                        onChange={(e) => {
                          const updated = [...availableFiles]
                          updated[index].checked = e.target.checked
                          setAvailableFiles(updated)
                        }}
                        className="w-4 h-4 text-primary rounded focus:ring-2 focus:ring-primary/20"
                      />
                      <span className="flex-1 text-sm text-gray-700">{file.name}</span>
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => openContentPreview(file.name)}
                          className="p-1 rounded hover:bg-gray-200 text-gray-500 hover:text-gray-700 transition-colors"
                          title={`Preview ${file.name}`}
                        >
                          <Eye size={16} />
                        </button>
                        <button
                          onClick={() => handleDeleteFile(file.name)}
                          className="p-1 rounded hover:bg-red-100 text-gray-500 hover:text-red-600 transition-colors"
                          title={`Delete ${file.name}`}
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Mobile Control Buttons */}
              <div className="flex gap-2">
                <button
                  onClick={handleMoveToAssigned}
                  disabled={!availableFiles.some(f => f.checked) || !selectedStudent}
                  className="flex-1 px-4 py-2 bg-primary hover:bg-primary-dark disabled:bg-gray-300 disabled:cursor-not-allowed text-white rounded-lg transition-all duration-300 flex items-center justify-center gap-2"
                >
                  <span className="text-sm">Assign →</span>
                </button>
                <button
                  onClick={handleMoveAllToAssigned}
                  disabled={availableFiles.length === 0 || !selectedStudent}
                  className="px-4 py-2 bg-practice-green hover:bg-practice-green-dark disabled:bg-gray-300 disabled:cursor-not-allowed text-white rounded-lg transition-all duration-300 flex items-center gap-2"
                >
                  <span className="text-sm">All →</span>
                </button>
              </div>
            </div>

            {/* Action Links */}
            {selectedStudent && (
              <div className="flex items-center justify-between mt-8 pt-6 border-t border-gray-200">
                <button
                  onClick={openStudentFolder}
                  className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900 transition-colors"
                >
                  <Folder size={16} />
                  Open student folder
                </button>
                <button
                  onClick={openReportsFolder}
                  className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900 transition-colors"
                >
                  <FileText size={16} />
                  Open reports folder
                </button>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Edit Display Name Modal */}
      {showEditModal && selectedStudent && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-card-bg rounded-2xl p-6 w-full max-w-md">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-gray-800">Edit Display Name</h2>
              <button
                onClick={() => {
                  setShowEditModal(false)
                  setEditingDisplayName('')
                }}
                className="p-2 rounded-lg hover:bg-gray-100 text-gray-600 transition-colors"
              >
                <X size={20} />
              </button>
            </div>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2 text-gray-700">Student ID</label>
                <input
                  type="text"
                  value={selectedStudent.id}
                  disabled
                  className="w-full px-4 py-3 rounded-xl border border-gray-300 bg-gray-100 text-gray-500 cursor-not-allowed"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-2 text-gray-700">Original Name</label>
                <input
                  type="text"
                  value={selectedStudent.name}
                  disabled
                  className="w-full px-4 py-3 rounded-xl border border-gray-300 bg-gray-100 text-gray-500 cursor-not-allowed"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium mb-2 text-gray-700">Display Name (tutor's view)</label>
                <input
                  type="text"
                  value={editingDisplayName}
                  onChange={(e) => setEditingDisplayName(e.target.value)}
                  className="w-full px-4 py-3 rounded-xl border border-gray-300 bg-gray-50 text-gray-900 focus:border-primary focus:ring-2 focus:ring-primary/20 focus:outline-none transition-colors"
                  placeholder="How you want to see this student"
                  maxLength={100}
                />
                <p className="text-xs text-gray-500 mt-1">
                  This only affects how you see the student. The student will still see their original name.
                </p>
              </div>
            </div>
            
            <div className="flex gap-3 mt-6">
              <button
                onClick={() => {
                  setShowEditModal(false)
                  setEditingDisplayName('')
                }}
                className="flex-1 px-4 py-3 rounded-xl font-medium bg-gray-100 hover:bg-gray-200 text-gray-700 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveDisplayName}
                disabled={!editingDisplayName.trim()}
                className="flex-1 px-4 py-3 bg-primary hover:bg-primary-dark disabled:bg-gray-300 disabled:cursor-not-allowed text-white rounded-xl font-medium transition-all duration-300"
              >
                Save
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Mobile Drawer for Assigned Files */}
      {showMobileDrawer && (
        <div className="fixed inset-0 bg-black/50 z-50 lg:hidden">
          <div className="fixed right-0 top-0 h-full w-80 bg-card-bg p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-gray-800">Assigned Files</h2>
              <button
                onClick={() => setShowMobileDrawer(false)}
                className="p-2 rounded-lg hover:bg-gray-100 text-gray-600 transition-colors"
              >
                <X size={20} />
              </button>
            </div>

            {/* Control Buttons */}
            <div className="flex gap-2 mb-4">
              <button
                onClick={handleMoveToAvailable}
                disabled={!assignedFiles.some(f => f.checked) || !selectedStudent}
                className="flex-1 px-3 py-2 bg-primary hover:bg-primary-dark disabled:bg-gray-300 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium transition-all duration-300"
              >
                ← Remove
              </button>
              <button
                onClick={handleMoveAllToAvailable}
                disabled={assignedFiles.length === 0 || !selectedStudent}
                className="flex-1 px-3 py-2 bg-experiment-orange hover:bg-experiment-orange-dark disabled:bg-gray-300 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium transition-all duration-300"
              >
                ← All
              </button>
            </div>
            
            <div className="border border-gray-200 rounded-xl p-4 h-96 overflow-y-auto bg-gray-50">
              {assignedFiles.map((file, index) => (
                <div key={index} className="flex items-center gap-3 p-3 rounded-lg hover:bg-white transition-colors">
                  <input
                    type="checkbox"
                    checked={file.checked}
                    onChange={(e) => {
                      const updated = [...assignedFiles]
                      updated[index].checked = e.target.checked
                      setAssignedFiles(updated)
                    }}
                    className="w-4 h-4 text-primary rounded focus:ring-2 focus:ring-primary/20"
                  />
                  <span className="flex-1 text-sm text-gray-700">{file.name}</span>
                  <button
                    onClick={() => openContentPreview(file.name)}
                    className="p-1 rounded hover:bg-gray-200 text-gray-500 hover:text-gray-700 transition-colors"
                    title={`Preview ${file.name}`}
                  >
                    <Eye size={16} />
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* File Browser Modal */}
      {showFileBrowser && fileBrowserConfig && (
        <FileBrowser
          studentId={fileBrowserConfig.studentId}
          studentName={fileBrowserConfig.studentName}
          initialFolder={fileBrowserConfig.initialFolder}
          onClose={closeFileBrowser}
        />
      )}

      {/* Content Preview Modal */}
      {showContentPreview && previewFilename && (
        <ContentPreview
          filename={previewFilename}
          onClose={closeContentPreview}
        />
      )}

      {/* File Upload Modal */}
      {showFileUpload && (
        <FileUpload
          onClose={closeFileUpload}
          onUploadSuccess={handleUploadSuccess}
        />
      )}
    </div>
  )
}

export default App