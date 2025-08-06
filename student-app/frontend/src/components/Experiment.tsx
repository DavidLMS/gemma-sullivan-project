import { useState, useEffect, useRef } from 'react'
import { ArrowLeft, Loader2, BookOpen, X, Check, Type, Palette, Upload, Send, Trash2, Undo, Eye } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { API_BASE } from '../config/api'

interface Challenge {
  id: string
  title: string
  description: string
  learning_goals: string
  deliverables: string
  type: string
}

interface ExperimentProgress {
  accepted: string[]
  rejected: string[]
  accepted_count: number
  rejected_count: number
  last_session: string | null
}

// Parser to convert HTML tags to Markdown format
const parseHtmlToMarkdown = (content: string): string => {
  return content
    // Convert code blocks containing tables to proper GFM tables (FIRST PRIORITY)
    .replace(/```\n(.*?\|.*?\n(?:.*?\n)*?)```/gs, (match, tableContent) => {
      // Check if the content looks like a table (has | and --- separator)
      if (tableContent.includes('|') && tableContent.includes('---')) {
        // Remove the code block and convert to proper table format
        return tableContent
          .split('\n')
          .map(line => {
            const trimmed = line.trim()
            if (!trimmed) return ''
            
            if (trimmed.includes('|')) {
              // Ensure proper GFM table format
              if (!trimmed.startsWith('|')) {
                return `| ${trimmed} |`
              }
              if (!trimmed.endsWith('|')) {
                return `${trimmed} |`
              }
              return trimmed
            }
            
            // Handle separator lines (--- | --- | ---)
            if (trimmed.includes('---')) {
              if (!trimmed.startsWith('|')) {
                // Convert "--- | --- | ---" to "|---|---|---|"
                const separated = trimmed.split('|').map(part => part.trim().replace(/\s+/g, '-'))
                return `|${separated.join('|')}|`
              }
              return trimmed
            }
            
            return line
          })
          .join('\n') + '\n\n'
      }
      return match
    })
    
    // Convert HTML tables to GFM tables
    .replace(/<table[^>]*>(.*?)<\/table>/gs, (match, tableContent) => {
      const rows = tableContent.match(/<tr[^>]*>(.*?)<\/tr>/gs) || []
      if (rows.length === 0) return match
      
      const processedRows = rows.map((row, index) => {
        const cells = row.match(/<t[hd][^>]*>(.*?)<\/t[hd]>/gs) || []
        const cellContents = cells.map(cell => {
          const content = cell.replace(/<t[hd][^>]*>(.*?)<\/t[hd]>/s, '$1').trim()
          return content.replace(/<[^>]*>/g, '') // Remove any nested HTML
        })
        
        if (cellContents.length === 0) return ''
        
        const formattedRow = `| ${cellContents.join(' | ')} |`
        
        // Add separator after header row
        if (index === 0) {
          const separator = `|${cellContents.map(() => '---').join('|')}|`
          return `${formattedRow}\n${separator}`
        }
        
        return formattedRow
      })
      
      return '\n' + processedRows.filter(row => row).join('\n') + '\n\n'
    })
    
    // Convert ordered lists to proper markdown format
    .replace(/<ol[^>]*>(.*?)<\/ol>/gs, (match, listContent) => {
      const items = listContent.match(/<li[^>]*>(.*?)<\/li>/gs) || []
      const processedItems = items
        .map((item, index) => {
          const cleanItem = item.replace(/<li[^>]*>(.*?)<\/li>/s, '$1').trim()
          return `${index + 1}. ${cleanItem}`
        })
        .join('\n')
      
      return processedItems + '\n\n'
    })
    
    // Convert unordered lists to proper markdown format  
    .replace(/<ul[^>]*>(.*?)<\/ul>/gs, (match, listContent) => {
      const processedItems = listContent
        .match(/<li>(.*?)<\/li>/gs)
        ?.map(item => {
          const cleanItem = item.replace(/<li>(.*?)<\/li>/s, '$1').trim()
          return `- ${cleanItem}`
        })
        .join('\n') || ''
      
      return processedItems + '\n\n'
    })
    // Convert standalone li tags (outside of ol/ul) to bulleted items
    .replace(/<li>(.*?)<\/li>/gs, '- $1\n')
    
    // Convert table format to proper GFM format
    .replace(/(^.*?\|.*?\n^---.*?\n(?:^.*?\|.*?\n)*)/gm, (tableBlock) => {
      return tableBlock
        .split('\n')
        .map(line => {
          const trimmed = line.trim()
          if (!trimmed) return line
          
          if (trimmed.includes('|')) {
            // Add | at start and end if not present
            if (!trimmed.startsWith('|')) {
              return `| ${trimmed} |`
            }
            if (!trimmed.endsWith('|')) {
              return `${trimmed} |`
            }
            return trimmed
          }
          
          // Handle separator lines (--- | --- | ---)
          if (trimmed.includes('---')) {
            if (!trimmed.startsWith('|')) {
              // Convert "--- | --- | ---" to "|---|---|---|"
              const separated = trimmed.split('|').map(part => part.trim().replace(/\s+/g, '-'))
              return `|${separated.join('|')}|`
            }
            return trimmed
          }
          
          return line
        })
        .join('\n') + '\n\n'
    })
    
    // Clean up: Remove any remaining HTML tags that might have been missed
    .replace(/<[^>]*>/g, '')
    // Remove any extra whitespace and normalize line breaks
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}

/**
 * Experiment component handles challenge-based learning with multimodal submissions.
 * Supports text, drawings, and file uploads with async AI feedback.
 * 
 * Features:
 * - Challenge browsing and selection
 * - Multi-modal submission (text, canvas, files)
 * - Async feedback generation with polling
 * - Session persistence and restoration
 * - Real-time challenge updates via SSE
 * 
 * @param props - Component props  
 * @param props.onBack - Callback to navigate back to main menu
 * @param props.onNavigate - Callback to navigate to other views
 */
const Experiment = ({ onBack, onNavigate }: { onBack: () => void, onNavigate: (view: 'learn') => void }) => {
  const [challenges, setChallenges] = useState<Challenge[]>([])
  const [loading, setLoading] = useState(true)
  const [currentChallenge, setCurrentChallenge] = useState<Challenge | null>(null)
  const [progress, setProgress] = useState<ExperimentProgress | null>(null)
  const [showingChallenge, setShowingChallenge] = useState(false)
  const [acceptedChallenge, setAcceptedChallenge] = useState<Challenge | null>(null)
  
  // Delivery interface states
  const [activeTab, setActiveTab] = useState<'text' | 'draw' | 'upload'>('text')
  const [textContent, setTextContent] = useState('')
  const [currentCanvas, setCurrentCanvas] = useState<string | null>(null) // Single Base64 canvas state
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([])
  const [existingFiles, setExistingFiles] = useState<{filename: string, size: number, lastModified: string}[]>([])
  const [saveStatus, setSaveStatus] = useState<'saved' | 'saving' | 'idle'>('idle')
  const [isInitializing, setIsInitializing] = useState(true)
  
  // Challenge feedback states
  const [feedback, setFeedback] = useState<any>(null)
  const [showingFeedback, setShowingFeedback] = useState(false)
  const [isEvaluating, setIsEvaluating] = useState(false)
  
  // Async feedback states
  const [feedbackTaskId, setFeedbackTaskId] = useState<string | null>(null)
  const [feedbackStatus, setFeedbackStatus] = useState<'idle' | 'pending' | 'processing' | 'completed' | 'error'>('idle')
  const [feedbackMessage, setFeedbackMessage] = useState<string>('')
  const [queuePosition, setQueuePosition] = useState<number>(0)
  const [estimatedWaitMinutes, setEstimatedWaitMinutes] = useState<number>(0)
  
  // Status tracking states
  const [experimentStatus, setExperimentStatus] = useState<{
    has_accessed_content: boolean
    content_accessed: string[]
    challenges_available: number
    generation_status: string
    message: string
  } | null>(null)
  
  // Canvas drawing states
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [isDrawing, setIsDrawing] = useState(false)
  const [brushSize, setBrushSize] = useState(3)
  const [brushColor, setBrushColor] = useState('#000000')
  const [canvasHistory, setCanvasHistory] = useState<string[]>([])
  const [historyIndex, setHistoryIndex] = useState(-1)
  

  // Load session data on component mount
  const loadSession = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/experiment/session`)
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      const session = await response.json()
      
      if (session.hasSession) {
        // Find the challenge for this session
        const challengesResponse = await fetch(`${API_BASE}/api/experiment/list`)
        if (challengesResponse.ok) {
          const availableChallenges = await challengesResponse.json()
          const sessionChallenge = availableChallenges.find(c => c.id === session.challengeId)
          
          if (sessionChallenge) {
            // Restore session state
            setAcceptedChallenge(sessionChallenge)
            setTextContent(session.textContent)
            // Always start with text tab (workaround for Canvas loading issue)
            // setActiveTab(session.activeTab) // Commented out - always start with 'text'
            setCurrentCanvas(session.currentCanvas || null)
            setUploadedFiles([]) // Reset new uploads
            setShowingChallenge(false)
            
            // Load existing files for this challenge
            try {
              const filesResponse = await fetch(`${API_BASE}/api/experiment/files/${session.challengeId}`)
              if (filesResponse.ok) {
                const filesData = await filesResponse.json()
                setExistingFiles(filesData.files || [])
                // Loaded existing files
              }
            } catch (error) {
              // Error loading existing files
              setExistingFiles([])
            }
            
            // Restored session for challenge
            return true // Session restored
          }
        }
      }
      return false // No session to restore
    } catch (error) {
      // Error loading session
      return false
    }
  }

  // Load async feedback task from localStorage
  const loadFeedbackTask = async () => {
    try {
      const storedTaskId = localStorage.getItem('feedbackTask')
      if (storedTaskId) {
        setFeedbackTaskId(storedTaskId)
        // Found stored feedback task
        // Check the status immediately
        await checkFeedbackStatus(storedTaskId)
      }
    } catch (error) {
      // Error loading feedback task
    }
  }

  // Check feedback status for a task
  const checkFeedbackStatus = async (taskId: string) => {
    try {
      const response = await fetch(`${API_BASE}/api/experiment/feedback/${taskId}`)
      if (response.ok) {
        const result = await response.json()
        
        setFeedbackStatus(result.status)
        setFeedbackMessage(result.message || '')
        setQueuePosition(result.queue_position || 0)
        setEstimatedWaitMinutes(result.estimated_wait_minutes || 0)
        
        if (result.status === 'completed' && result.feedback) {
          setFeedback(result.feedback)
          // Don't auto-show feedback - let user click to see it
          // Async feedback completed and ready to show
        } else if (result.status === 'error') {
          // Async feedback failed
          // Clear the task from localStorage on error
          localStorage.removeItem('feedbackTask')
          setFeedbackTaskId(null)
        }
        
        // Feedback task status logged
      } else if (response.status === 404) {
        // Task not found, clear from localStorage
        localStorage.removeItem('feedbackTask')
        setFeedbackTaskId(null)
        setFeedbackStatus('idle')
      }
    } catch (error) {
      // Error checking feedback status
    }
  }

  // Load available challenges from backend
  const loadChallenges = async () => {
    try {
      setLoading(true)
      const response = await fetch(`${API_BASE}/api/experiment/list`)
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      const data = await response.json()
      setChallenges(data)
      
      // First try to restore existing session
      const sessionRestored = await loadSession()
      
      // Load any pending feedback task
      await loadFeedbackTask()
      
      // If no session and there are challenges, show a random one
      if (!sessionRestored && data.length > 0) {
        const randomIndex = Math.floor(Math.random() * data.length)
        setCurrentChallenge(data[randomIndex])
        setShowingChallenge(true)
      }
      
    } catch (error) {
      // Error loading challenges
      setChallenges([])
    } finally {
      setLoading(false)
      setIsInitializing(false) // Mark initialization as complete
    }
  }

  // Load progress data
  const loadProgress = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/experiment/progress`)
      if (response.ok) {
        const data = await response.json()
        setProgress(data)
      }
    } catch (error) {
      // Error loading progress
    }
  }

  // Load experiment status with smart messaging
  const loadExperimentStatus = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/experiment/status`)
      if (response.ok) {
        const data = await response.json()
        // Received experiment status
        setExperimentStatus(data)
        // Set experiment status state
      }
    } catch (error) {
      // Error loading experiment status
    }
  }

  // Handle challenge decision (accept/reject)
  const handleDecision = async (decision: 'accepted' | 'rejected') => {
    if (!currentChallenge) return

    try {
      const response = await fetch(`${API_BASE}/api/experiment/decision`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          challengeId: currentChallenge.id,
          decision: decision
        })
      })

      if (response.ok) {
        // Challenge decision recorded
        
        // If accepted, show the delivery interface
        if (decision === 'accepted') {
          setAcceptedChallenge(currentChallenge)
          setShowingChallenge(false)
          // Save initial session state
          saveSession(currentChallenge.id, textContent, activeTab, uploadedFiles, currentCanvas)
          return
        }
        
        // If rejected, clear any existing session and load new challenges
        await clearSession()
        await loadChallenges()
        await loadProgress()
        await loadExperimentStatus() // Also refresh status after rejection
        
      } else {
        // Failed to record decision
      }
    } catch (error) {
      // Error recording decision
    }
  }

  // Check if delivery has content
  const hasContent = () => {
    return textContent.trim().length > 0 || currentCanvas !== null || uploadedFiles.length > 0 || existingFiles.length > 0
  }

  // Auto-save session data
  const saveSession = async (challengeId: string, content: string, tab: string, files: File[] = [], canvasData: string | null = null) => {
    try {
      setSaveStatus('saving')
      const response = await fetch(`${API_BASE}/api/experiment/save-session`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          challengeId,
          textContent: content,
          activeTab: tab,
          uploadedFiles: files.map(f => f.name), // For now, just save filenames
          currentCanvas: canvasData
        })
      })

      if (response.ok) {
        setSaveStatus('saved')
        // Session auto-saved
        // Reset to idle after 2 seconds
        setTimeout(() => setSaveStatus('idle'), 2000)
      }
    } catch (error) {
      // Error saving session
      setSaveStatus('idle')
    }
  }

  // Clear session data
  const clearSession = async () => {
    try {
      await fetch(`${API_BASE}/api/experiment/session`, {
        method: 'DELETE'
      })
      // Clear local state
      setExistingFiles([])
      setCurrentCanvas(null)
      setCanvasHistory([])
      setHistoryIndex(-1)
      // Session cleared
    } catch (error) {
      // Error clearing session
    }
  }

  // Handle challenge submission (async version)
  const handleAsyncSubmission = async () => {
    if (!acceptedChallenge || !hasContent()) return

    // Clear any previous error state
    if (feedbackStatus === 'error') {
      clearFeedbackTask()
    }

    try {
      const response = await fetch(`${API_BASE}/api/experiment/submit-async`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          challengeId: acceptedChallenge.id,
          textContent,
          canvasData: currentCanvas
        })
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const result = await response.json()
      
      if (result.success) {
        const taskId = result.task_id
        setFeedbackTaskId(taskId)
        setFeedbackStatus('pending')
        setFeedbackMessage('Feedback is being generated...')
        
        // Store task ID in localStorage
        localStorage.setItem('feedbackTask', taskId)
        
        // Async feedback task created
        
        // Start checking status immediately
        await checkFeedbackStatus(taskId)
      } else {
        throw new Error('Failed to create feedback task')
      }
      
    } catch (error) {
      // Error submitting challenge
      alert('Error creating feedback task. Please try again.')
    }
  }

  // Legacy synchronous submission (kept for compatibility)
  const handleSubmission = async () => {
    if (!acceptedChallenge || !hasContent()) return

    setIsEvaluating(true)
    
    try {
      const response = await fetch(`${API_BASE}/api/experiment/submit`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          challengeId: acceptedChallenge.id,
          textContent,
          canvasData: currentCanvas
        })
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const result = await response.json()
      
      if (result.success) {
        setFeedback(result.feedback)
        setShowingFeedback(true)
        // Challenge feedback received
      } else {
        throw new Error('Failed to get feedback')
      }
      
    } catch (error) {
      // Error submitting challenge
      alert('Error getting feedback. Please try again.')
    } finally {
      setIsEvaluating(false)
    }
  }

  // Handle user decision on feedback
  const handleFeedbackDecision = async (continueRefining: boolean) => {
    // Record student's decision for xAPI logging
    if (feedbackTaskId && acceptedChallenge) {
      try {
        await fetch(`${API_BASE}/api/experiment/feedback-decision`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            challengeId: acceptedChallenge.id,
            taskId: feedbackTaskId,
            continueRefining: continueRefining
          })
        })
        // Decision recorded
      } catch (error) {
        // Error recording feedback decision
      }
    }
    
    if (continueRefining) {
      // User wants to keep working - close feedback and reset for new submission
      setShowingFeedback(false)
      setFeedback(null)
      clearFeedbackTask() // Reset feedback state so button shows "Send Challenge" again
      // Student chose to continue refining submission
    } else {
      // User is done - complete the challenge
      setShowingFeedback(false)
      setFeedback(null)
      
      // Clear async feedback task
      clearFeedbackTask()
      
      // Clear session and reset for new challenge
      await clearSession()
      
      // Reset states and load new challenges
      setAcceptedChallenge(null)
      setTextContent('')
      setCurrentCanvas(null)
      setUploadedFiles([])
      setExistingFiles([])
      setActiveTab('text')
      setCanvasHistory([])
      setHistoryIndex(-1)
      await loadChallenges()
      await loadProgress()
      
      // Challenge completed successfully
    }
  }

  // Show async feedback when ready
  const showAsyncFeedback = () => {
    if (feedback) {
      setShowingFeedback(true)
    }
  }

  // Clear async feedback task
  const clearFeedbackTask = () => {
    localStorage.removeItem('feedbackTask')
    setFeedbackTaskId(null)
    setFeedbackStatus('idle')
    setFeedbackMessage('')
    setFeedback(null)
  }

  // Handle file upload
  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files
    if (files && acceptedChallenge) {
      // Add files to local state immediately
      const newFiles = Array.from(files)
      setUploadedFiles(prev => [...prev, ...newFiles])
      
      // Upload each file to backend
      for (const file of newFiles) {
        try {
          const formData = new FormData()
          formData.append('file', file)
          
          const response = await fetch(`${API_BASE}/api/experiment/upload?challengeId=${acceptedChallenge.id}`, {
            method: 'POST',
            body: formData
          })
          
          if (response.ok) {
            const result = await response.json()
            // File uploaded successfully
            
            // Remove from uploading state
            setUploadedFiles(prev => prev.filter(f => f.name !== file.name))
            
            // Refresh existing files list
            const filesResponse = await fetch(`${API_BASE}/api/experiment/files/${acceptedChallenge.id}`)
            if (filesResponse.ok) {
              const filesData = await filesResponse.json()
              setExistingFiles(filesData.files || [])
            }
          } else {
            const errorData = await response.json().catch(() => ({}))
            // Failed to upload file
            alert(`Error uploading ${file.name}: ${errorData.detail || 'Unknown error'}`)
            
            // Remove from uploading state since it failed
            setUploadedFiles(prev => prev.filter(f => f.name !== file.name))
          }
        } catch (error) {
          // Network error uploading file
          alert(`Network error uploading ${file.name}. Please try again.`)
          
          // Remove from uploading state since it failed
          setUploadedFiles(prev => prev.filter(f => f.name !== file.name))
        }
      }
      
      // Clear the input
      event.target.value = ''
    }
  }

  // Remove uploaded file (local, not yet uploaded)
  const removeFile = (index: number) => {
    setUploadedFiles(prev => prev.filter((_, i) => i !== index))
  }

  // Remove existing file from backend
  const removeExistingFile = async (filename: string) => {
    if (!acceptedChallenge) return
    
    try {
      const response = await fetch(`${API_BASE}/api/experiment/files/${acceptedChallenge.id}/${filename}`, {
        method: 'DELETE'
      })
      
      if (response.ok) {
        // File deleted successfully
        // Remove from local state
        setExistingFiles(prev => prev.filter(file => file.filename !== filename))
      } else {
        const errorData = await response.json().catch(() => ({}))
        // Failed to delete file
        alert(`Error deleting ${filename}: ${errorData.detail || 'Unknown error'}`)
      }
    } catch (error) {
      // Network error deleting file
      alert(`Network error deleting ${filename}. Please try again.`)
    }
  }

  // Canvas drawing functions
  const saveCanvasState = () => {
    const canvas = canvasRef.current
    if (!canvas) return
    
    const dataURL = canvas.toDataURL()
    const newHistory = canvasHistory.slice(0, historyIndex + 1)
    newHistory.push(dataURL)
    setCanvasHistory(newHistory)
    setHistoryIndex(newHistory.length - 1)
  }

  const getCanvasCoordinates = (e: React.MouseEvent<HTMLCanvasElement> | React.TouchEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current
    if (!canvas) return { x: 0, y: 0 }

    const rect = canvas.getBoundingClientRect()
    
    // Get raw coordinates
    const clientX = 'touches' in e ? e.touches[0].clientX : e.clientX
    const clientY = 'touches' in e ? e.touches[0].clientY : e.clientY
    
    // Calculate scale factors
    const scaleX = canvas.width / rect.width
    const scaleY = canvas.height / rect.height
    
    // Apply scale to get actual canvas coordinates
    const x = (clientX - rect.left) * scaleX
    const y = (clientY - rect.top) * scaleY
    
    return { x, y }
  }

  const startDrawing = (e: React.MouseEvent<HTMLCanvasElement> | React.TouchEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current
    if (!canvas) return

    setIsDrawing(true)
    const { x, y } = getCanvasCoordinates(e)

    const ctx = canvas.getContext('2d')
    if (ctx) {
      ctx.beginPath()
      ctx.moveTo(x, y)
    }
  }

  const draw = (e: React.MouseEvent<HTMLCanvasElement> | React.TouchEvent<HTMLCanvasElement>) => {
    if (!isDrawing) return
    
    const canvas = canvasRef.current
    if (!canvas) return

    const { x, y } = getCanvasCoordinates(e)

    const ctx = canvas.getContext('2d')
    if (ctx) {
      ctx.lineTo(x, y)
      ctx.strokeStyle = brushColor
      ctx.lineWidth = brushSize
      ctx.lineCap = 'round'
      ctx.stroke()
    }
  }

  const stopDrawing = () => {
    if (!isDrawing) return
    setIsDrawing(false)
    saveCanvasState()
    
    // Auto-save canvas to session
    const canvas = canvasRef.current
    if (canvas && acceptedChallenge) {
      const dataURL = canvas.toDataURL()
      setCurrentCanvas(dataURL)
    }
  }

  const clearCanvas = () => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (ctx) {
      ctx.fillStyle = 'white'
      ctx.fillRect(0, 0, canvas.width, canvas.height)
      saveCanvasState()
      
      // Clear from session too
      setCurrentCanvas(null)
    }
  }

  const undoCanvas = () => {
    if (historyIndex > 0) {
      const canvas = canvasRef.current
      if (!canvas) return

      const ctx = canvas.getContext('2d')
      if (ctx) {
        const img = new Image()
        img.onload = () => {
          ctx.clearRect(0, 0, canvas.width, canvas.height)
          ctx.drawImage(img, 0, 0)
          
          // Update current canvas state
          const dataURL = canvas.toDataURL()
          setCurrentCanvas(dataURL)
        }
        img.src = canvasHistory[historyIndex - 1]
        setHistoryIndex(historyIndex - 1)
      }
    }
  }


  // Initialize canvas
  const initializeCanvas = () => {
    const canvas = canvasRef.current
    if (!canvas) {
      // Canvas ref not available
      return
    }

    const ctx = canvas.getContext('2d')
    if (ctx) {
      // Initializing canvas
      
      // Clear canvas first
      ctx.fillStyle = 'white'
      ctx.fillRect(0, 0, canvas.width, canvas.height)
      
      // Load saved canvas if exists
      if (currentCanvas) {
        // Loading saved canvas data
        const img = new Image()
        img.onload = () => {
          // Saved canvas data loaded successfully
          ctx.drawImage(img, 0, 0)
          saveCanvasState()
        }
        img.onerror = () => {
          // Failed to load saved canvas data
          saveCanvasState()
        }
        img.src = currentCanvas
      } else {
        // No saved canvas data, starting with blank canvas
        saveCanvasState()
      }
    }
  }

  useEffect(() => {
    loadChallenges()
    loadProgress()
    loadExperimentStatus()
  }, [])

  // Polling for new challenges (when challenges might be generating)
  useEffect(() => {
    // Only start polling if we have no challenges available
    const shouldPoll = challenges.length === 0 && !acceptedChallenge && !isInitializing

    if (shouldPoll) {
      // Starting polling for new experiment challenges
      
      const interval = setInterval(async () => {
        // Polling for new experiment challenges and status
        const previousCount = challenges.length
        const previousStatus = experimentStatus?.generation_status
        
        // Before polling status logged
        
        await loadChallenges()
        await loadExperimentStatus() // Also refresh status for smart messaging
        
        // After polling completed
        
        // Use a short delay to let React state update, then check changes
        setTimeout(() => {
          // Check current state after updates
          setChallenges(currentChallenges => {
            if (currentChallenges.length > previousCount) {
              // New challenges detected
            }
            return currentChallenges
          })
          
          setExperimentStatus(currentStatus => {
            if (currentStatus?.generation_status !== previousStatus) {
              // Status changed
            }
            return currentStatus
          })
        }, 1000)
      }, 10000) // Poll every 10 seconds for faster updates
      
      return () => {
        // Stopping polling for new experiment challenges
        clearInterval(interval)
      }
    }
  }, [challenges.length, acceptedChallenge, isInitializing])

  // Auto-save when text content changes (with debouncing)
  useEffect(() => {
    if (acceptedChallenge && textContent.length > 0) {
      const saveTimer = setTimeout(() => {
        saveSession(acceptedChallenge.id, textContent, activeTab, uploadedFiles, currentCanvas)
      }, 2000) // 2 second debounce

      return () => clearTimeout(saveTimer)
    }
  }, [textContent, acceptedChallenge, currentCanvas])

  // Auto-save when active tab changes
  useEffect(() => {
    if (acceptedChallenge) {
      saveSession(acceptedChallenge.id, textContent, activeTab, uploadedFiles, currentCanvas)
    }
  }, [activeTab, acceptedChallenge, currentCanvas])

  // Polling for async feedback status
  useEffect(() => {
    if (feedbackTaskId && feedbackStatus !== 'completed' && feedbackStatus !== 'error' && feedbackStatus !== 'idle') {
      // Starting polling for feedback task
      
      const interval = setInterval(async () => {
        // Polling feedback status for task
        await checkFeedbackStatus(feedbackTaskId)
      }, 30000) // Poll every 30 seconds
      
      return () => {
        // Stopping polling for feedback task
        clearInterval(interval)
      }
    }
  }, [feedbackTaskId, feedbackStatus])

  // Auto-save when files are uploaded
  useEffect(() => {
    if (acceptedChallenge && uploadedFiles.length > 0) {
      saveSession(acceptedChallenge.id, textContent, activeTab, uploadedFiles, currentCanvas)
    }
  }, [uploadedFiles, acceptedChallenge, currentCanvas])

  // Auto-save when canvas changes (with debouncing)
  useEffect(() => {
    if (acceptedChallenge && currentCanvas) {
      const saveTimer = setTimeout(() => {
        saveSession(acceptedChallenge.id, textContent, activeTab, uploadedFiles, currentCanvas)
      }, 2000) // 2 second debounce

      return () => clearTimeout(saveTimer)
    }
  }, [currentCanvas, acceptedChallenge])

  // Clear session when challenge is rejected (but not during initialization)
  useEffect(() => {
    if (!isInitializing && !acceptedChallenge && !currentChallenge) {
      clearSession()
    }
  }, [acceptedChallenge, currentChallenge, isInitializing])

  // Initialize canvas when draw tab is selected
  useEffect(() => {
    if (activeTab === 'draw' && canvasRef.current) {
      // Canvas useEffect triggered
      setTimeout(initializeCanvas, 100) // Small delay to ensure canvas is rendered
    }
  }, [activeTab])


  // Main experiment view
  return (
    <div className="min-h-full bg-app-bg">
      {/* Header */}
      <header className="grid grid-cols-3 items-center p-4 bg-card-bg shadow-sm">
        <button
          onClick={onBack}
          className="p-2 text-orange-600 hover:text-orange-700 transition-colors"
        >
          <ArrowLeft className="w-6 h-6" />
        </button>
        
        <h1 className="text-xl font-semibold text-gray-800 text-center">Experiment</h1>
        
        <div></div>
      </header>

      {/* Content */}
      <main className="p-6">
        {loading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-orange-600" />
          </div>
        ) : challenges.length === 0 ? (
          // Empty state with smart messaging based on status
          <div className="text-center py-12">
            <div className={`w-16 h-16 mx-auto mb-6 rounded-2xl flex items-center justify-center ${
              experimentStatus?.generation_status === 'in_progress' 
                ? 'bg-gradient-to-br from-blue-500 to-indigo-600' 
                : 'bg-gradient-to-br from-orange-500 to-amber-600'
            }`}>
              {experimentStatus?.generation_status === 'in_progress' ? (
                <Loader2 className="w-8 h-8 text-white animate-spin" />
              ) : (
                <BookOpen className="w-8 h-8 text-white" />
              )}
            </div>
            <h2 className="text-xl font-bold text-gray-800 mb-3">
              {experimentStatus?.generation_status === 'in_progress' 
                ? 'Generating New Challenges...' 
                : 'No Challenges Available Yet'
              }
            </h2>
            <p className="text-gray-600 mb-6 max-w-md mx-auto">
              {experimentStatus?.message || 'Visit the Learn section first to explore some content. Experiment challenges are automatically generated when you read through topics for the first time!'}
            </p>
            {experimentStatus?.generation_status !== 'in_progress' && (
              <button
                onClick={() => onNavigate('learn')}
                className="bg-orange-600 hover:bg-orange-700 text-white font-medium px-6 py-3 rounded-xl transition-colors duration-200 shadow-sm"
              >
                Go to Learn
              </button>
            )}
            {experimentStatus?.generation_status === 'in_progress' && (
              <div className="text-sm text-gray-500 mt-2">
                This may take a few minutes...
              </div>
            )}
          </div>
        ) : showingChallenge && currentChallenge ? (
          // Challenge presentation view
          <div className="space-y-6">
            <div className="mb-6">
              <h2 className="text-2xl font-bold text-gray-800 mb-2">Challenge Available</h2>
              <p className="text-gray-600">A new experimental challenge is ready for you!</p>
            </div>

            {/* Challenge card */}
            <div className="bg-white rounded-2xl shadow-sm p-6 border border-gray-200">
              <div className="mb-4">
                <h3 className="text-xl font-bold text-gray-800 mb-2">{currentChallenge.title}</h3>
                <div className="prose prose-lg max-w-none text-gray-600 leading-relaxed mb-4">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      p: ({children}) => <p className="mb-4">{children}</p>,
                      strong: ({children}) => <strong className="font-bold text-gray-800">{children}</strong>,
                      em: ({children}) => <em className="italic text-gray-500">{children}</em>,
                      code: ({children}) => <code className="bg-gray-100 px-2 py-1 rounded text-sm font-mono text-gray-800">{children}</code>,
                      h1: ({children}) => <h1 className="text-2xl font-bold mb-4 mt-6 text-gray-800">{children}</h1>,
                      h2: ({children}) => <h2 className="text-xl font-semibold mb-3 mt-5 text-gray-800">{children}</h2>,
                      h3: ({children}) => <h3 className="text-lg font-medium mb-2 mt-4 text-gray-800">{children}</h3>,
                      ul: ({children}) => <ul className="list-disc pl-6 mb-4 space-y-1">{children}</ul>,
                      ol: ({children}) => <ol className="list-decimal pl-6 mb-4 space-y-1">{children}</ol>,
                      li: ({children}) => <li className="text-gray-600">{children}</li>,
                      blockquote: ({children}) => <blockquote className="border-l-4 border-gray-300 pl-4 py-2 mb-4 bg-gray-50 rounded text-gray-600">{children}</blockquote>,
                      table: ({children}) => <table className="min-w-full border-collapse border border-gray-200 mb-4">{children}</table>,
                      thead: ({children}) => <thead className="bg-gray-50">{children}</thead>,
                      tbody: ({children}) => <tbody>{children}</tbody>,
                      tr: ({children}) => <tr className="border-b border-gray-200">{children}</tr>,
                      th: ({children}) => <th className="border border-gray-200 px-4 py-2 text-left font-semibold text-gray-800 bg-gray-50">{children}</th>,
                      td: ({children}) => <td className="border border-gray-200 px-4 py-2 text-gray-600">{children}</td>
                    }}
                  >
                    {parseHtmlToMarkdown(currentChallenge.description)}
                  </ReactMarkdown>
                </div>
                  
                <div>
                  <h4 className="font-semibold text-gray-800 mb-1">What you need to deliver:</h4>
                  <div className="prose prose-sm max-w-none text-gray-600">
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      components={{
                        p: ({children}) => <p className="mb-2">{children}</p>,
                        strong: ({children}) => <strong className="font-bold text-gray-800">{children}</strong>,
                        em: ({children}) => <em className="italic text-gray-500">{children}</em>,
                        code: ({children}) => <code className="bg-gray-100 px-1 py-0.5 rounded text-xs font-mono text-gray-800">{children}</code>,
                        ul: ({children}) => <ul className="list-disc pl-4 mb-2 space-y-0.5">{children}</ul>,
                        ol: ({children}) => <ol className="list-decimal pl-4 mb-2 space-y-0.5">{children}</ol>,
                        li: ({children}) => <li className="text-gray-600 text-sm">{children}</li>,
                        table: ({children}) => <table className="min-w-full border-collapse border border-gray-200 mb-2 text-sm">{children}</table>,
                        thead: ({children}) => <thead className="bg-gray-50">{children}</thead>,
                        tbody: ({children}) => <tbody>{children}</tbody>,
                        tr: ({children}) => <tr className="border-b border-gray-200">{children}</tr>,
                        th: ({children}) => <th className="border border-gray-200 px-2 py-1 text-left font-semibold text-gray-800 bg-gray-50 text-xs">{children}</th>,
                        td: ({children}) => <td className="border border-gray-200 px-2 py-1 text-gray-600 text-xs">{children}</td>
                      }}
                    >
                      {parseHtmlToMarkdown(currentChallenge.deliverables)}
                    </ReactMarkdown>
                  </div>
                </div>
              </div>

              {/* Decision interface */}
              <div className="border-t pt-4 mt-6">
                <h3 className="text-lg font-semibold text-gray-800 mb-4 text-center">
                  Do you accept the challenge?
                </h3>
                
                <div className="flex justify-center space-x-4">
                  <button
                    onClick={() => handleDecision('rejected')}
                    className="flex items-center space-x-2 px-6 py-3 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-xl transition-colors duration-200 font-medium"
                  >
                    <X className="w-5 h-5" />
                    <span>No</span>
                  </button>
                  
                  <button
                    onClick={() => handleDecision('accepted')}
                    className="flex items-center space-x-2 px-6 py-3 bg-gradient-to-r from-orange-500 to-amber-600 hover:from-orange-600 hover:to-amber-700 text-white rounded-xl transition-all duration-200 font-medium shadow-sm"
                  >
                    <Check className="w-5 h-5" />
                    <span>Yes</span>
                  </button>
                </div>
              </div>
            </div>

          </div>
        ) : acceptedChallenge ? (
          // Challenge delivery interface
          <div className="space-y-6">
            {/* Challenge header */}
            <div className="bg-white rounded-2xl shadow-sm p-6 border border-gray-200">
              <div className="flex items-start space-x-4">
                <div className="flex-1">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h3 className="text-xl font-bold text-gray-800 mb-2">{acceptedChallenge.title}</h3>
                      <div className="prose prose-sm max-w-none text-gray-600 mb-3">
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm]}
                          components={{
                            p: ({children}) => <p className="mb-2 text-sm">{children}</p>,
                            strong: ({children}) => <strong className="font-bold text-gray-800">{children}</strong>,
                            em: ({children}) => <em className="italic text-gray-500">{children}</em>,
                            code: ({children}) => <code className="bg-gray-100 px-1 py-0.5 rounded text-xs font-mono text-gray-800">{children}</code>,
                            ul: ({children}) => <ul className="list-disc pl-4 mb-2 space-y-0.5">{children}</ul>,
                            ol: ({children}) => <ol className="list-decimal pl-4 mb-2 space-y-0.5">{children}</ol>,
                            li: ({children}) => <li className="text-gray-600 text-sm">{children}</li>,
                            table: ({children}) => <table className="min-w-full border-collapse border border-gray-200 mb-2 text-xs">{children}</table>,
                            thead: ({children}) => <thead className="bg-gray-50">{children}</thead>,
                            tbody: ({children}) => <tbody>{children}</tbody>,
                            tr: ({children}) => <tr className="border-b border-gray-200">{children}</tr>,
                            th: ({children}) => <th className="border border-gray-200 px-2 py-1 text-left font-semibold text-gray-800 bg-gray-50 text-xs">{children}</th>,
                            td: ({children}) => <td className="border border-gray-200 px-2 py-1 text-gray-600 text-xs">{children}</td>
                          }}
                        >
                          {parseHtmlToMarkdown(acceptedChallenge.description)}
                        </ReactMarkdown>
                      </div>
                      <div className="text-sm">
                        <div className="font-semibold text-gray-800 mb-1">What to deliver:</div>
                        <div className="prose prose-sm max-w-none text-gray-600">
                          <ReactMarkdown
                            remarkPlugins={[remarkGfm]}
                            components={{
                              p: ({children}) => <p className="mb-1 text-sm">{children}</p>,
                              strong: ({children}) => <strong className="font-bold text-gray-800">{children}</strong>,
                              em: ({children}) => <em className="italic text-gray-500">{children}</em>,
                              code: ({children}) => <code className="bg-gray-100 px-1 py-0.5 rounded text-xs font-mono text-gray-800">{children}</code>,
                              ul: ({children}) => <ul className="list-disc pl-4 space-y-0.5">{children}</ul>,
                              ol: ({children}) => <ol className="list-decimal pl-4 space-y-0.5">{children}</ol>,
                              li: ({children}) => <li className="text-gray-600 text-sm">{children}</li>,
                              table: ({children}) => <table className="min-w-full border-collapse border border-gray-200 mb-1 text-xs">{children}</table>,
                              thead: ({children}) => <thead className="bg-gray-50">{children}</thead>,
                              tbody: ({children}) => <tbody>{children}</tbody>,
                              tr: ({children}) => <tr className="border-b border-gray-200">{children}</tr>,
                              th: ({children}) => <th className="border border-gray-200 px-2 py-1 text-left font-semibold text-gray-800 bg-gray-50 text-xs">{children}</th>,
                              td: ({children}) => <td className="border border-gray-200 px-2 py-1 text-gray-600 text-xs">{children}</td>
                            }}
                          >
                            {parseHtmlToMarkdown(acceptedChallenge.deliverables)}
                          </ReactMarkdown>
                        </div>
                      </div>
                    </div>
                    
                    {/* Save status indicator removed */}
                    <div className="flex items-center space-x-2 text-sm">
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Delivery tabs */}
            <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
              {/* Tab headers */}
              <div className="flex border-b border-gray-200">
                <button
                  onClick={() => setActiveTab('text')}
                  className={`flex-1 flex items-center justify-center space-x-2 py-4 px-6 text-sm font-medium transition-colors ${
                    activeTab === 'text'
                      ? 'bg-orange-50 text-orange-600 border-b-2 border-orange-600'
                      : 'text-gray-500 hover:text-gray-700'
                  }`}
                >
                  <Type className="w-4 h-4" />
                  <span>Text</span>
                </button>
                
                <button
                  onClick={() => setActiveTab('draw')}
                  className={`flex-1 flex items-center justify-center space-x-2 py-4 px-6 text-sm font-medium transition-colors ${
                    activeTab === 'draw'
                      ? 'bg-orange-50 text-orange-600 border-b-2 border-orange-600'
                      : 'text-gray-500 hover:text-gray-700'
                  }`}
                >
                  <Palette className="w-4 h-4" />
                  <span>Draw</span>
                </button>
                
                <button
                  onClick={() => setActiveTab('upload')}
                  className={`flex-1 flex items-center justify-center space-x-2 py-4 px-6 text-sm font-medium transition-colors ${
                    activeTab === 'upload'
                      ? 'bg-orange-50 text-orange-600 border-b-2 border-orange-600'
                      : 'text-gray-500 hover:text-gray-700'
                  }`}
                >
                  <Upload className="w-4 h-4" />
                  <span>Upload</span>
                </button>
              </div>

              {/* Tab content */}
              <div className="p-6">
                {activeTab === 'text' && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Write your response:
                    </label>
                    <textarea
                      value={textContent}
                      onChange={(e) => setTextContent(e.target.value)}
                      placeholder="Describe your solution, findings, or approach to this challenge..."
                      className="w-full h-40 p-4 border border-gray-200 rounded-xl resize-none focus:border-orange-500 focus:outline-none"
                    />
                  </div>
                )}

                {activeTab === 'draw' && (
                  <div className="space-y-4">
                    {/* Drawing tools */}
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center space-x-4">
                        <div className="flex items-center space-x-2">
                          <label className="text-sm font-medium text-gray-700">Color:</label>
                          <input
                            type="color"
                            value={brushColor}
                            onChange={(e) => setBrushColor(e.target.value)}
                            className="w-8 h-8 rounded border border-gray-300 cursor-pointer"
                          />
                        </div>
                        <div className="flex items-center space-x-2">
                          <label className="text-sm font-medium text-gray-700">Size:</label>
                          <input
                            type="range"
                            min="1"
                            max="20"
                            value={brushSize}
                            onChange={(e) => setBrushSize(Number(e.target.value))}
                            className="w-20"
                          />
                          <span className="text-sm text-gray-600 w-6">{brushSize}</span>
                        </div>
                      </div>
                      
                      <div className="flex items-center space-x-2">
                        <button
                          onClick={undoCanvas}
                          disabled={historyIndex <= 0}
                          className="p-2 bg-gray-100 hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition-colors"
                          title="Undo"
                        >
                          <Undo className="w-4 h-4" />
                        </button>
                        <button
                          onClick={clearCanvas}
                          className="p-2 bg-red-100 hover:bg-red-200 text-red-600 rounded-lg transition-colors"
                          title="Clear canvas"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>

                    {/* Canvas */}
                    <div className="border border-gray-300 rounded-lg overflow-hidden bg-white">
                      <canvas
                        ref={canvasRef}
                        width={600}
                        height={400}
                        className="block w-full cursor-crosshair touch-none"
                        onMouseDown={startDrawing}
                        onMouseMove={draw}
                        onMouseUp={stopDrawing}
                        onMouseLeave={stopDrawing}
                        onTouchStart={startDrawing}
                        onTouchMove={draw}
                        onTouchEnd={stopDrawing}
                        style={{ maxWidth: '100%', height: 'auto' }}
                      />
                    </div>

                    {/* Canvas info */}
                    <div className="text-center text-sm text-gray-600">
                      <p>Your drawing is automatically saved as you work.</p>
                    </div>
                  </div>
                )}

                {activeTab === 'upload' && (
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Upload photos:
                      </label>
                      <input
                        type="file"
                        multiple
                        accept="image/*"
                        onChange={handleFileUpload}
                        className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-orange-50 file:text-orange-600 hover:file:bg-orange-100"
                      />
                    </div>

                    {/* Existing files (already uploaded) */}
                    {existingFiles.length > 0 && (
                      <div className="space-y-2">
                        <h4 className="text-sm font-medium text-gray-700">Uploaded photos:</h4>
                        {existingFiles.map((file, index) => (
                          <div key={`existing-${index}`} className="flex items-center justify-between bg-green-50 p-3 rounded-lg border border-green-200">
                            <div className="flex-1">
                              <span className="text-sm text-gray-700 font-medium">{file.filename}</span>
                              <div className="text-xs text-gray-500">
                                {(file.size / 1024).toFixed(1)} KB • {new Date(file.lastModified).toLocaleDateString()}
                              </div>
                            </div>
                            <button
                              onClick={() => removeExistingFile(file.filename)}
                              className="text-red-500 hover:text-red-700 ml-2"
                              title="Delete photo"
                            >
                              <X className="w-4 h-4" />
                            </button>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* New files (being uploaded) */}
                    {uploadedFiles.length > 0 && (
                      <div className="space-y-2">
                        <h4 className="text-sm font-medium text-gray-700">Uploading...</h4>
                        {uploadedFiles.map((file, index) => (
                          <div key={`new-${index}`} className="flex items-center justify-between bg-orange-50 p-3 rounded-lg border border-orange-200">
                            <div className="flex items-center space-x-2">
                              <Loader2 className="w-4 h-4 animate-spin text-orange-600" />
                              <span className="text-sm text-gray-600">{file.name}</span>
                            </div>
                            <button
                              onClick={() => removeFile(index)}
                              className="text-red-500 hover:text-red-700"
                            >
                              <X className="w-4 h-4" />
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Submit button */}
            <div className="flex flex-col items-center space-y-3">
              <button
                onClick={feedbackStatus === 'completed' ? showAsyncFeedback : handleAsyncSubmission}
                disabled={!hasContent() || feedbackStatus === 'pending' || feedbackStatus === 'processing'}
                className="flex items-center space-x-2 px-8 py-3 bg-gradient-to-r from-orange-500 to-amber-600 hover:from-orange-600 hover:to-amber-700 disabled:from-gray-300 disabled:to-gray-400 disabled:cursor-not-allowed text-white rounded-xl transition-all duration-200 font-medium shadow-sm"
              >
                {feedbackStatus === 'pending' || feedbackStatus === 'processing' ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    <span>Getting Feedback...</span>
                  </>
                ) : feedbackStatus === 'completed' ? (
                  <>
                    <Eye className="w-5 h-5" />
                    <span>View Feedback</span>
                  </>
                ) : (
                  <>
                    <Send className="w-5 h-5" />
                    <span>Send Challenge</span>
                  </>
                )}
              </button>
              
              {/* Simple informative message */}
              {feedbackStatus !== 'idle' && (
                <p className="text-xs text-gray-500 text-center">
                  You can continue working or come back later while feedback is generated.
                </p>
              )}
            </div>

            {/* Feedback Modal */}
            {showingFeedback && feedback && (
              <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
                <div className="bg-white rounded-2xl max-w-2xl w-full max-h-[80vh] overflow-y-auto">
                  <div className="p-6">
                    <h3 className="text-xl font-bold text-gray-800 mb-4">Challenge Feedback</h3>
                    
                    {/* Strengths */}
                    <div className="mb-4">
                      <h4 className="font-semibold text-green-600 mb-2">✓ What you did well:</h4>
                      <div className="text-gray-700 bg-green-50 p-3 rounded-lg prose prose-sm max-w-none">
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm]}
                          components={{
                            p: ({children}) => <p className="mb-2 text-sm">{children}</p>,
                            strong: ({children}) => <strong className="font-bold text-gray-800">{children}</strong>,
                            em: ({children}) => <em className="italic text-gray-600">{children}</em>,
                            code: ({children}) => <code className="bg-gray-100 px-1 py-0.5 rounded text-xs font-mono text-gray-800">{children}</code>,
                            ul: ({children}) => <ul className="list-disc pl-4 mb-2 space-y-0.5">{children}</ul>,
                            ol: ({children}) => <ol className="list-decimal pl-4 mb-2 space-y-0.5">{children}</ol>,
                            li: ({children}) => <li className="text-gray-700 text-sm">{children}</li>,
                            table: ({children}) => <table className="min-w-full border-collapse border border-gray-200 mb-2 text-xs">{children}</table>,
                            thead: ({children}) => <thead className="bg-gray-50">{children}</thead>,
                            tbody: ({children}) => <tbody>{children}</tbody>,
                            tr: ({children}) => <tr className="border-b border-gray-200">{children}</tr>,
                            th: ({children}) => <th className="border border-gray-200 px-2 py-1 text-left font-semibold text-gray-800 bg-gray-50 text-xs">{children}</th>,
                            td: ({children}) => <td className="border border-gray-200 px-2 py-1 text-gray-700 text-xs">{children}</td>
                          }}
                        >
                          {parseHtmlToMarkdown(feedback.strengths)}
                        </ReactMarkdown>
                      </div>
                    </div>
                    
                    {/* Areas for improvement */}
                    <div className="mb-4">
                      <h4 className="font-semibold text-orange-600 mb-2">📈 Areas for improvement:</h4>
                      <div className="text-gray-700 bg-orange-50 p-3 rounded-lg prose prose-sm max-w-none">
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm]}
                          components={{
                            p: ({children}) => <p className="mb-2 text-sm">{children}</p>,
                            strong: ({children}) => <strong className="font-bold text-gray-800">{children}</strong>,
                            em: ({children}) => <em className="italic text-gray-600">{children}</em>,
                            code: ({children}) => <code className="bg-gray-100 px-1 py-0.5 rounded text-xs font-mono text-gray-800">{children}</code>,
                            ul: ({children}) => <ul className="list-disc pl-4 mb-2 space-y-0.5">{children}</ul>,
                            ol: ({children}) => <ol className="list-decimal pl-4 mb-2 space-y-0.5">{children}</ol>,
                            li: ({children}) => <li className="text-gray-700 text-sm">{children}</li>,
                            table: ({children}) => <table className="min-w-full border-collapse border border-gray-200 mb-2 text-xs">{children}</table>,
                            thead: ({children}) => <thead className="bg-gray-50">{children}</thead>,
                            tbody: ({children}) => <tbody>{children}</tbody>,
                            tr: ({children}) => <tr className="border-b border-gray-200">{children}</tr>,
                            th: ({children}) => <th className="border border-gray-200 px-2 py-1 text-left font-semibold text-gray-800 bg-gray-50 text-xs">{children}</th>,
                            td: ({children}) => <td className="border border-gray-200 px-2 py-1 text-gray-700 text-xs">{children}</td>
                          }}
                        >
                          {parseHtmlToMarkdown(feedback.areas_for_improvement)}
                        </ReactMarkdown>
                      </div>
                    </div>
                    
                    {/* Suggestions */}
                    <div className="mb-4">
                      <h4 className="font-semibold text-blue-600 mb-2">💡 Suggestions:</h4>
                      <div className="text-gray-700 bg-blue-50 p-3 rounded-lg prose prose-sm max-w-none">
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm]}
                          components={{
                            p: ({children}) => <p className="mb-2 text-sm">{children}</p>,
                            strong: ({children}) => <strong className="font-bold text-gray-800">{children}</strong>,
                            em: ({children}) => <em className="italic text-gray-600">{children}</em>,
                            code: ({children}) => <code className="bg-gray-100 px-1 py-0.5 rounded text-xs font-mono text-gray-800">{children}</code>,
                            ul: ({children}) => <ul className="list-disc pl-4 mb-2 space-y-0.5">{children}</ul>,
                            ol: ({children}) => <ol className="list-decimal pl-4 mb-2 space-y-0.5">{children}</ol>,
                            li: ({children}) => <li className="text-gray-700 text-sm">{children}</li>,
                            table: ({children}) => <table className="min-w-full border-collapse border border-gray-200 mb-2 text-xs">{children}</table>,
                            thead: ({children}) => <thead className="bg-gray-50">{children}</thead>,
                            tbody: ({children}) => <tbody>{children}</tbody>,
                            tr: ({children}) => <tr className="border-b border-gray-200">{children}</tr>,
                            th: ({children}) => <th className="border border-gray-200 px-2 py-1 text-left font-semibold text-gray-800 bg-gray-50 text-xs">{children}</th>,
                            td: ({children}) => <td className="border border-gray-200 px-2 py-1 text-gray-700 text-xs">{children}</td>
                          }}
                        >
                          {parseHtmlToMarkdown(feedback.suggestions)}
                        </ReactMarkdown>
                      </div>
                    </div>
                    
                    {/* Overall assessment */}
                    <div className="mb-6">
                      <h4 className="font-semibold text-purple-600 mb-2">📋 Overall assessment:</h4>
                      <div className="text-gray-700 bg-purple-50 p-3 rounded-lg prose prose-sm max-w-none">
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm]}
                          components={{
                            p: ({children}) => <p className="mb-2 text-sm">{children}</p>,
                            strong: ({children}) => <strong className="font-bold text-gray-800">{children}</strong>,
                            em: ({children}) => <em className="italic text-gray-600">{children}</em>,
                            code: ({children}) => <code className="bg-gray-100 px-1 py-0.5 rounded text-xs font-mono text-gray-800">{children}</code>,
                            ul: ({children}) => <ul className="list-disc pl-4 mb-2 space-y-0.5">{children}</ul>,
                            ol: ({children}) => <ol className="list-decimal pl-4 mb-2 space-y-0.5">{children}</ol>,
                            li: ({children}) => <li className="text-gray-700 text-sm">{children}</li>,
                            table: ({children}) => <table className="min-w-full border-collapse border border-gray-200 mb-2 text-xs">{children}</table>,
                            thead: ({children}) => <thead className="bg-gray-50">{children}</thead>,
                            tbody: ({children}) => <tbody>{children}</tbody>,
                            tr: ({children}) => <tr className="border-b border-gray-200">{children}</tr>,
                            th: ({children}) => <th className="border border-gray-200 px-2 py-1 text-left font-semibold text-gray-800 bg-gray-50 text-xs">{children}</th>,
                            td: ({children}) => <td className="border border-gray-200 px-2 py-1 text-gray-700 text-xs">{children}</td>
                          }}
                        >
                          {parseHtmlToMarkdown(feedback.overall_assessment)}
                        </ReactMarkdown>
                      </div>
                    </div>
                    
                    {/* Decision buttons */}
                    <div className="flex justify-center space-x-4">
                      <button
                        onClick={() => handleFeedbackDecision(true)}
                        className="flex items-center space-x-2 px-6 py-3 bg-orange-100 hover:bg-orange-200 text-orange-700 rounded-xl transition-colors duration-200 font-medium"
                      >
                        <span>Continue Improving</span>
                      </button>
                      
                      <button
                        onClick={() => handleFeedbackDecision(false)}
                        className="flex items-center space-x-2 px-6 py-3 bg-gradient-to-r from-green-500 to-green-600 hover:from-green-600 hover:to-green-700 text-white rounded-xl transition-all duration-200 font-medium shadow-sm"
                      >
                        <Check className="w-5 h-5" />
                        <span>Complete Challenge</span>
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        ) : null}
      </main>
    </div>
  )
}

export default Experiment