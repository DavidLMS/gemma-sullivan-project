import { useState, useEffect, useRef } from 'react'
import { ArrowLeft, Camera, Send, Loader2, CheckCircle, ChevronDown, ChevronUp } from 'lucide-react'
import { API_BASE } from '../config/api'

interface DiscoverProps {
  onBack: () => void
}

interface AnswerOption {
  name: string
  description: string
}

interface RevealData {
  conclusion_intro: string
  answer_options: AnswerOption[]
  completion_message: string
}

type DiscoveryState = 'capture' | 'investigating' | 'thinking' | 'reveal' | 'complete'

/**
 * Discover component provides camera-based investigative learning experience.
 * Students take photos and ask questions to start guided Socratic discussions.
 * 
 * Learning flow:
 * 1. Camera capture and question input
 * 2. AI identifies subject and generates guiding questions
 * 3. Student selects questions to explore (button-based)
 * 4. AI provides answer options for final selection
 * 5. Investigation completion and recording
 * 
 * @param props - Component props
 * @param props.onBack - Callback to navigate back to main menu
 */
const Discover = ({ onBack }: DiscoverProps) => {
  
  // Core state
  const [currentState, setCurrentState] = useState<DiscoveryState>('capture')
  const [investigationId, setInvestigationId] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  // Camera and input state
  const [capturedImage, setCapturedImage] = useState<string | null>(null)
  const [questionText, setQuestionText] = useState('')
  const [hasCamera, setHasCamera] = useState(true)
  const [cameraInitialized, setCameraInitialized] = useState(false)
  const [isInitializingCamera, setIsInitializingCamera] = useState(false)
  
  // Investigation state
  const [subjectIdentified, setSubjectIdentified] = useState('')
  const [contextualIntro, setContextualIntro] = useState('')
  const [currentQuestions, setCurrentQuestions] = useState<string[]>([])
  const [questionCount, setQuestionCount] = useState(0)
  const [questionLimit, setQuestionLimit] = useState(5)
  const [encouragement, setEncouragement] = useState('')
  const [selectedQuestionPath, setSelectedQuestionPath] = useState<string[]>([])
  
  // Thinking and reveal state
  const [isThinking, setIsThinking] = useState(false)
  const [revealData, setRevealData] = useState<RevealData | null>(null)
  const [expandedOption, setExpandedOption] = useState<number | null>(null)
  const [selectedAnswer, setSelectedAnswer] = useState<string>('')
  
  // Refs
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const streamRef = useRef<MediaStream | null>(null)

  // Cleanup camera stream when component unmounts
  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop())
      }
    }
  }, [])

  // Simplified camera activation - called directly from user click
  const activateCamera = () => {
    if (cameraInitialized || isInitializingCamera) return
    
    setIsInitializingCamera(true)
    setError(null)
    // Requesting camera permissions directly from user click
    
    // Call getUserMedia directly in the same call stack as user event
    navigator.mediaDevices.getUserMedia({ 
      video: { facingMode: 'environment' },
      audio: false 
    })
    .then(stream => {
      // Camera permissions granted, setting up video stream
      // videoRef.current exists check
      
      if (videoRef.current) {
        // Setting video srcObject
        videoRef.current.srcObject = stream
        streamRef.current = stream
        
        // Video element setup complete, waiting for metadata
        
        videoRef.current.onloadedmetadata = () => {
          // Video metadata loaded! Setting states
          // Video dimensions logged
          setHasCamera(true)
          setCameraInitialized(true)
          setIsInitializingCamera(false)
          // States updated: hasCamera=true, cameraInitialized=true
        }
        
        // Also try oncanplay as backup
        videoRef.current.oncanplay = () => {
          // Video can play! Setting states as backup
          setHasCamera(true)
          setCameraInitialized(true)
          setIsInitializingCamera(false)
        }
        
        // Fallback timeout
        setTimeout(() => {
          // Video metadata timeout, forcing state update (this always runs)
          setHasCamera(true)
          setCameraInitialized(true)
          setIsInitializingCamera(false)
        }, 2000)
      } else {
        // videoRef.current is null, setting states anyway
        setHasCamera(true)
        setCameraInitialized(true)
        setIsInitializingCamera(false)
      }
    })
    .catch(error => {
      // Error accessing camera
      setHasCamera(false)
      setError('Camera access denied. You can still type your questions.')
      setIsInitializingCamera(false)
    })
  }


  const capturePhoto = () => {
    if (!videoRef.current || !canvasRef.current || !cameraInitialized) {
      // Video, canvas, or camera not ready
      return
    }

    const video = videoRef.current
    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')

    if (!ctx) {
      // Canvas context not available
      return
    }

    // Check if video is ready
    if (video.videoWidth === 0 || video.videoHeight === 0) {
      // Video not ready yet, dimensions logged
      setTimeout(() => capturePhoto(), 500)
      return
    }

    // Capturing photo with dimensions
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    ctx.drawImage(video, 0, 0)

    const imageData = canvas.toDataURL('image/jpeg', 0.8)
    setCapturedImage(imageData)
    // Photo captured successfully
  }


  const startInvestigation = async () => {
    if (!capturedImage || !questionText.trim()) {
      setError('Please capture a photo and add a question.')
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      const response = await fetch(`${API_BASE}/api/discover/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          imageData: capturedImage,
          questionText: questionText.trim(),
        }),
      })

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`)
      }

      const data = await response.json()
      
      if (data.success) {
        setInvestigationId(data.investigation_id)
        setSubjectIdentified(data.subject_identified)
        setContextualIntro(data.contextual_intro)
        setCurrentQuestions(data.guiding_questions)
        setQuestionCount(data.question_count)
        setQuestionLimit(data.question_limit)
        setCurrentState('investigating')
      } else {
        throw new Error('Failed to start investigation')
      }
    } catch (error) {
      // Error starting investigation
      setError('Failed to analyze your photo and question. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  const selectQuestion = async (selectedQuestion: string) => {
    if (!investigationId) return

    setIsThinking(true)
    setError(null)
    setSelectedQuestionPath([...selectedQuestionPath, selectedQuestion])

    // Show thinking state immediately
    setCurrentState('thinking')
    setEncouragement(`Great choice! Take a moment to think about "${selectedQuestion.substring(0, 50)}..."`)

    try {
      const response = await fetch(`${API_BASE}/api/discover/question`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sessionId: investigationId,
          responseText: selectedQuestion,
        }),
      })

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`)
      }

      const data = await response.json()
      
      if (data.success) {
        if (data.should_reveal) {
          // Question limit reached, trigger reveal
          await triggerReveal()
        } else {
          // Continue with more questions
          setEncouragement(data.encouragement)
          setCurrentQuestions(data.guiding_questions)
          setQuestionCount(data.question_count)
          
          // Brief thinking pause, then show new questions
          setTimeout(() => {
            setIsThinking(false)
            setCurrentState('investigating')
          }, 1500)
        }
      } else {
        throw new Error('Failed to process question selection')
      }
    } catch (error) {
      // Error selecting question
      setError('Failed to process your selection. Please try again.')
      setIsThinking(false)
      setCurrentState('investigating')
    }
  }

  const triggerReveal = async () => {
    if (!investigationId) return

    try {
      const response = await fetch(`${API_BASE}/api/discover/reveal`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          investigationId: investigationId,
        }),
      })

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`)
      }

      const data = await response.json()
      
      if (data.success) {
        setRevealData({
          conclusion_intro: data.conclusion_intro,
          answer_options: data.answer_options,
          completion_message: data.completion_message
        })
        setIsThinking(false)
        setCurrentState('reveal')
      } else {
        throw new Error('Failed to generate answer options')
      }
    } catch (error) {
      // Error revealing options
      setError('Failed to generate answer options. Please try again.')
      setIsThinking(false)
      setCurrentState('investigating')
    }
  }

  const completeInvestigation = async () => {
    if (!investigationId || !selectedAnswer) return

    setIsLoading(true)
    setError(null)

    try {
      const response = await fetch(`${API_BASE}/api/discover/complete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          investigationId: investigationId,
          selectedAnswer: selectedAnswer,
        }),
      })

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`)
      }

      const data = await response.json()
      
      if (data.success) {
        setCurrentState('complete')
      } else {
        throw new Error('Failed to complete investigation')
      }
    } catch (error) {
      // Error completing investigation
      setError('Failed to record your discovery. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  const resetDiscovery = () => {
    // Stop camera stream if active
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop())
      streamRef.current = null
    }
    
    setCurrentState('capture')
    setInvestigationId(null)
    setCapturedImage(null)
    setQuestionText('')
    setSubjectIdentified('')
    setContextualIntro('')
    setCurrentQuestions([])
    setQuestionCount(0)
    setEncouragement('')
    setSelectedQuestionPath([])
    setIsThinking(false)
    setRevealData(null)
    setExpandedOption(null)
    setSelectedAnswer('')
    setError(null)
    setCameraInitialized(false)
    setIsInitializingCamera(false)
  }

  return (
    <div className="min-h-screen bg-app-bg">
      {/* Header */}
      <header className="grid grid-cols-3 items-center p-4 bg-card-bg shadow-sm">
        <button
          onClick={onBack}
          className="p-2 text-primary hover:text-primary-dark transition-colors"
        >
          <ArrowLeft className="w-6 h-6" />
        </button>
        
        <h1 className="text-xl font-semibold text-gray-800 text-center">Discover</h1>
        
        <div></div>
      </header>

      {/* Error Display */}
      {error && (
        <div className="mx-4 mt-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center space-x-2">
          <span className="text-red-700">{error}</span>
        </div>
      )}

      {/* Main Content */}
      <div className="p-4">
        {currentState === 'capture' && (
          <div className="space-y-6">
            <div className="text-center">
              <h2 className="text-2xl font-bold text-gray-800 mb-2">Start Your Discovery</h2>
              <p className="text-gray-600">Take a photo of something that interests you and ask a question about it!</p>
            </div>

            {/* Camera Interface - Only show when no image captured */}
            {!capturedImage && (
              <div className="bg-white rounded-xl shadow-lg overflow-hidden">
                {/* Debug render states */}
                <div className="relative">
                  {/* Video element - always present in DOM */}
                  <video
                    ref={videoRef}
                    autoPlay
                    playsInline
                    className="w-full h-64 object-cover bg-gray-100"
                  />
                  <canvas ref={canvasRef} className="hidden" />
                  
                  {/* Overlay states */}
                  {!cameraInitialized ? (
                    // Show activate button overlay
                    <div className="absolute inset-0 bg-gray-100 flex items-center justify-center">
                      <div className="text-center">
                        <Camera className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                        <p className="text-gray-700 font-medium mb-2">Ready to take a photo?</p>
                        <p className="text-sm text-gray-500 mb-4">Click the camera button to start</p>
                        <button
                          onClick={activateCamera}
                          disabled={isInitializingCamera}
                          className="bg-primary hover:bg-primary-600 disabled:bg-gray-400 text-white px-6 py-3 rounded-lg transition-all flex items-center space-x-2 mx-auto"
                        >
                          {isInitializingCamera ? (
                            <>
                              <Loader2 className="w-5 h-5 animate-spin" />
                              <span>Starting Camera...</span>
                            </>
                          ) : (
                            <>
                              <Camera className="w-5 h-5" />
                              <span>Activate Camera</span>
                            </>
                          )}
                        </button>
                      </div>
                    </div>
                  ) : hasCamera ? (
                    // Show capture button overlay
                    <div className="absolute inset-0 flex items-center justify-center">
                      <button
                        onClick={capturePhoto}
                        className="bg-white bg-opacity-90 hover:bg-opacity-100 p-4 rounded-full shadow-lg transition-all transform hover:scale-105"
                      >
                        <Camera className="w-8 h-8 text-gray-700" />
                      </button>
                    </div>
                  ) : (
                    // Show error overlay
                    <div className="absolute inset-0 bg-gray-100 flex items-center justify-center">
                      <div className="text-center">
                        <Camera className="w-12 h-12 text-gray-400 mx-auto mb-2" />
                        <p className="text-gray-500">Camera not available</p>
                        <p className="text-sm text-gray-400">You can still type your questions</p>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Captured Image Preview */}
            {capturedImage && (
              <div className="bg-white rounded-xl shadow-lg overflow-hidden">
                <img src={capturedImage} alt="Captured" className="w-full h-64 object-cover" />
                <div className="p-4 flex justify-between items-center">
                  <span className="text-green-600 flex items-center space-x-2">
                    <CheckCircle className="w-5 h-5" />
                    <span>Photo captured!</span>
                  </span>
                  <button
                    onClick={() => setCapturedImage(null)}
                    className="text-gray-500 hover:text-gray-700"
                  >
                    Retake
                  </button>
                </div>
              </div>
            )}

            {/* Question Input */}
            <div className="bg-white rounded-xl shadow-lg p-4">
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    What do you want to know about it?
                  </label>
                  <textarea
                    value={questionText}
                    onChange={(e) => setQuestionText(e.target.value)}
                    placeholder="Type your question here... (e.g., 'What kind of tree is this?')"
                    className="w-full h-24 p-3 border border-gray-300 rounded-lg resize-none focus:ring-2 focus:ring-primary focus:border-transparent"
                  />
                </div>


                {/* Submit Button */}
                <button
                  onClick={startInvestigation}
                  disabled={!capturedImage || !questionText.trim() || isLoading}
                  className="w-full flex items-center justify-center space-x-2 px-6 py-3 bg-gradient-to-r from-primary to-primary-dark text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:from-primary-dark hover:to-gray-800 transition-all"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="w-5 h-5 animate-spin" />
                      <span>Starting Investigation...</span>
                    </>
                  ) : (
                    <>
                      <Send className="w-5 h-5" />
                      <span>Start Discovery</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        )}

        {currentState === 'investigating' && (
          <div className="space-y-6">
            <div className="text-center">
              <h2 className="text-2xl font-bold text-gray-800 mb-2">Investigation: {subjectIdentified}</h2>
              <p className="text-gray-600">{contextualIntro}</p>
            </div>

            {/* Question Progress */}
            <div className="bg-white rounded-xl shadow-lg p-4">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold text-gray-800">Choose a question to explore:</h3>
                <span className="text-sm text-gray-500">{questionCount}/{questionLimit} questions</span>
              </div>
              
              {/* Question Selection Buttons */}
              <div className="space-y-3">
                {currentQuestions.map((question, index) => (
                  <button
                    key={index}
                    onClick={() => selectQuestion(question)}
                    className="w-full p-4 text-left bg-gray-50 hover:bg-primary-50 hover:border-primary-200 border border-gray-200 rounded-lg transition-all"
                  >
                    <span className="text-gray-800">{question}</span>
                  </button>
                ))}
              </div>

            </div>
          </div>
        )}

        {currentState === 'thinking' && (
          <div className="space-y-6">
            <div className="text-center">
              <h2 className="text-2xl font-bold text-gray-800 mb-2">Take a Moment to Reflect...</h2>
              <p className="text-gray-600">{encouragement}</p>
            </div>

            <div className="bg-white rounded-xl shadow-lg p-8 text-center">
              <Loader2 className="w-12 h-12 text-primary mx-auto mb-4 animate-spin" />
              <p className="text-gray-600">Think about what you already know and what you'd like to discover...</p>
            </div>
          </div>
        )}

        {currentState === 'reveal' && revealData && (
          <div className="space-y-6">
            <div className="text-center">
              <h2 className="text-2xl font-bold text-gray-800 mb-2">Time to Choose!</h2>
              <p className="text-gray-600">{revealData.conclusion_intro}</p>
            </div>

            {/* Answer Options Accordion */}
            <div className="bg-white rounded-xl shadow-lg overflow-hidden">
              <div className="p-4 bg-gray-50 border-b">
                <h3 className="text-lg font-semibold text-gray-800">What do you think it is?</h3>
              </div>
              
              <div className="divide-y divide-gray-200">
                {revealData.answer_options.map((option, index) => (
                  <div key={index} className="border-b border-gray-200 last:border-b-0">
                    <button
                      onClick={() => setExpandedOption(expandedOption === index ? null : index)}
                      className="w-full p-4 text-left hover:bg-gray-50 transition-colors"
                    >
                      <div className="flex justify-between items-center">
                        <span className="font-medium text-gray-800">{option.name}</span>
                        {expandedOption === index ? (
                          <ChevronUp className="w-5 h-5 text-gray-500" />
                        ) : (
                          <ChevronDown className="w-5 h-5 text-gray-500" />
                        )}
                      </div>
                    </button>
                    
                    {expandedOption === index && (
                      <div className="px-4 pb-4">
                        <p className="text-gray-600 mb-4">{option.description}</p>
                        <button
                          onClick={() => setSelectedAnswer(option.name)}
                          className={`px-4 py-2 rounded-lg transition-colors ${
                            selectedAnswer === option.name
                              ? 'bg-primary text-white'
                              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                          }`}
                        >
                          {selectedAnswer === option.name ? 'Selected' : 'Choose This'}
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Complete Investigation Button */}
            {selectedAnswer && (
              <div className="bg-white rounded-xl shadow-lg p-4">
                <p className="text-gray-600 mb-4">{revealData.completion_message}</p>
                <button
                  onClick={completeInvestigation}
                  disabled={isLoading}
                  className="w-full flex items-center justify-center space-x-2 px-6 py-3 bg-gradient-to-r from-green-500 to-green-600 text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:from-green-600 hover:to-green-700 transition-all"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="w-5 h-5 animate-spin" />
                      <span>Recording Discovery...</span>
                    </>
                  ) : (
                    <>
                      <CheckCircle className="w-5 h-5" />
                      <span>Complete Discovery</span>
                    </>
                  )}
                </button>
              </div>
            )}
          </div>
        )}

        {currentState === 'complete' && (
          <div className="space-y-6">
            <div className="text-center">
              <h2 className="text-2xl font-bold text-gray-800 mb-2">Discovery Complete!</h2>
              <p className="text-gray-600">Great investigation work!</p>
            </div>

            <div className="bg-white rounded-xl shadow-lg p-6 text-center">
              <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
              <h3 className="text-xl font-semibold text-gray-800 mb-2">Your Discovery is Recorded</h3>
              <p className="text-gray-600 mb-4">
                You chose: <span className="font-medium text-primary">{selectedAnswer}</span>
              </p>
              <p className="text-gray-500 text-sm mb-6">
                Your investigation has been saved for your tutor to review.
              </p>
              <button
                onClick={resetDiscovery}
                className="px-6 py-3 bg-gradient-to-r from-primary to-primary-dark text-white rounded-lg hover:from-primary-dark hover:to-gray-800 transition-all"
              >
                Discover Something New
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default Discover