import { useState, useEffect } from 'react'
import { ArrowLeft, CheckCircle2, Loader2, BookOpen } from 'lucide-react'
import QuestionInterface from './QuestionInterface'
import { API_BASE } from '../config/api'

interface Question {
  id: string
  type: 'multiple_choice' | 'true_false' | 'fill_blank' | 'short_answer' | 'free_recall'
  question: string
  options?: string[]
  answer: string
  explanation?: string
  contentId: string
  difficulty: 'easy' | 'medium' | 'hard'
}

interface QuestionTypeStats {
  total: number
  correct: number
}

interface ContentQuestions {
  contentId: string
  displayName: string
  questions: Question[]
}

/**
 * Practice component provides interactive question-answering interface.
 * Features multiple question types, progress tracking, and real-time polling.
 * 
 * Question types supported:
 * - Multiple choice
 * - Fill in the blank
 * - Short answer
 * - Free recall
 * 
 * @param props - Component props
 * @param props.onBack - Callback to navigate back to main menu
 * @param props.onNavigate - Callback to navigate to other views (e.g., learn)
 */
const Practice = ({ onBack, onNavigate }: { onBack: () => void, onNavigate: (view: 'learn') => void }) => {
  const [contentQuestions, setContentQuestions] = useState<ContentQuestions[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedType, setSelectedType] = useState<string | null>(null)
  const [currentQuestion, setCurrentQuestion] = useState<Question | null>(null)
  const [questionStats, setQuestionStats] = useState<{[key: string]: QuestionTypeStats}>({})
  const [filteredQuestions, setFilteredQuestions] = useState<Question[]>([])
  
  // Status tracking states
  const [practiceStatus, setPracticeStatus] = useState<{
    has_accessed_content: boolean
    content_accessed: string[]
    questions_available: number
    generation_status: string
    message: string
  } | null>(null)
  

  // Format display name from filename
  const formatDisplayName = (name: string) => {
    return name
      .replace(/_/g, ' ')
      .replace(/\b\w/g, l => l.toUpperCase())
  }

  // Load practice status with smart messaging
  const loadPracticeStatus = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/practice/status`)
      if (response.ok) {
        const data = await response.json()
        // Received practice status
        setPracticeStatus(data)
        // Set practice status state
      }
    } catch (error) {
      // Error loading practice status
    }
  }

  // Load practice questions from backend
  const loadPracticeQuestions = async () => {
    try {
      setLoading(true)
      const response = await fetch(`${API_BASE}/api/practice/list`)
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      const data = await response.json()
      setContentQuestions(data)
      
      // Calculate initial stats (will be updated with progress data)
      calculateQuestionStats(data)
    } catch (error) {
      // Error loading practice questions
      setContentQuestions([])
    } finally {
      setLoading(false)
    }
  }

  // Load progress data from backend and calculate statistics
  const loadProgressStats = async () => {
    // Start with current question totals (preserve the correct totals from calculateQuestionStats)
    const currentStats = {...questionStats}
    
    // Reset correct counts to 0, but keep total counts
    Object.keys(currentStats).forEach(type => {
      currentStats[type].correct = 0
    })

    // Load progress data for each content
    for (const content of contentQuestions) {
      try {
        const response = await fetch(`${API_BASE}/api/practice/progress/${content.contentId}`)
        if (response.ok) {
          const progressData = await response.json()
          
          // Only update correct counts from backend progress data
          Object.keys(currentStats).forEach(type => {
            if (progressData[type]) {
              currentStats[type].correct += progressData[type].correct || 0  // Only update correct count
              // Keep the total count from calculateQuestionStats - don't overwrite it
            }
          })
        }
      } catch (error) {
        // Error loading progress for content
      }
    }

    // Updated progress stats
    setQuestionStats(currentStats)
  }

  // Calculate basic question counts (fallback)
  const calculateQuestionStats = (data: ContentQuestions[]) => {
    const stats: {[key: string]: QuestionTypeStats} = {
      'multiple_choice': { total: 0, correct: 0 },
      'fill_blank': { total: 0, correct: 0 },
      'short_answer': { total: 0, correct: 0 },
      'free_recall': { total: 0, correct: 0 }
    }

    data.forEach(content => {
      content.questions.forEach(question => {
        if (stats[question.type]) {
          stats[question.type].total++
        }
      })
    })

    setQuestionStats(stats)
  }

  // Get color for question type cards
  const getQuestionTypeColor = (type: string) => {
    const colors = {
      'multiple_choice': { bg: 'from-green-500 to-green-600', border: 'border-green-200', hover: 'hover:border-green-300', text: 'text-green-600', hexColor: '#16a34a' },
      'fill_blank': { bg: 'from-blue-500 to-blue-600', border: 'border-blue-200', hover: 'hover:border-blue-300', text: 'text-blue-600', hexColor: '#2563eb' },
      'short_answer': { bg: 'from-purple-500 to-purple-600', border: 'border-purple-200', hover: 'hover:border-purple-300', text: 'text-purple-600', hexColor: '#7c3aed' },
      'free_recall': { bg: 'from-orange-500 to-orange-600', border: 'border-orange-200', hover: 'hover:border-orange-300', text: 'text-orange-600', hexColor: '#ea580c' }
    }
    return colors[type] || colors['multiple_choice']
  }

  // Get progress percentage for question type
  const getTypeProgress = (type: string) => {
    const stats = questionStats[type]
    if (!stats || stats.total === 0) return 0
    return Math.round((stats.correct / stats.total) * 100)
  }

  // Get question type display names
  const getTypeDisplayName = (type: string) => {
    const names = {
      'multiple_choice': 'Multiple Choice',
      'fill_blank': 'Fill in the Blank', 
      'short_answer': 'Short Answer',
      'free_recall': 'Free Recall'
    }
    return names[type] || type
  }


  // Handle question type selection with smart filtering
  const handleTypeSelection = async (type: string) => {
    // Get all questions of the selected type from all content
    const typeQuestions: Question[] = []
    contentQuestions.forEach(content => {
      content.questions.forEach(question => {
        if (question.type === type) {
          typeQuestions.push(question)
        }
      })
    })
    
    // Load progress data to filter questions intelligently
    let unansweredQuestions: Question[] = []
    let incorrectQuestions: Question[] = []
    
    for (const content of contentQuestions) {
      try {
        const response = await fetch(`${API_BASE}/api/practice/progress/${content.contentId}`)
        if (response.ok) {
          const progressData = await response.json()
          const typeProgress = progressData[type]
          
          if (typeProgress) {
            const attemptedIds = new Set(typeProgress.attempted_ids || [])
            const correctIds = new Set(typeProgress.correct_ids || [])
            
            // Filter questions for this content
            const contentTypeQuestions = typeQuestions.filter(q => q.contentId === content.contentId)
            
            contentTypeQuestions.forEach(question => {
              if (!attemptedIds.has(question.id)) {
                // Never attempted - priority 1
                unansweredQuestions.push(question)
              } else if (!correctIds.has(question.id)) {
                // Attempted but incorrect - priority 2
                incorrectQuestions.push(question)
              }
            })
          } else {
            // No progress data - all questions are unanswered
            unansweredQuestions.push(...typeQuestions.filter(q => q.contentId === content.contentId))
          }
        }
      } catch (error) {
        // Error loading progress for content
        // Fallback: treat all questions as unanswered
        unansweredQuestions.push(...typeQuestions.filter(q => q.contentId === content.contentId))
      }
    }
    
    // Determine which questions to show
    let questionsToShow: Question[] = []
    
    if (unansweredQuestions.length > 0) {
      // Priority 1: Show unanswered questions
      questionsToShow = unansweredQuestions
      // Showing unanswered questions
    } else if (incorrectQuestions.length > 0) {
      // Priority 2: Show incorrect questions for retry
      questionsToShow = incorrectQuestions
      // Showing incorrect questions for retry
    } else {
      // All questions answered correctly - show completion message or allow review
      // All questions completed correctly
      // For now, show all questions (could be changed to show completion message)
      questionsToShow = typeQuestions
    }
    
    // Shuffle questions to randomize order
    const shuffledQuestions = questionsToShow.sort(() => Math.random() - 0.5)
    
    setFilteredQuestions(shuffledQuestions)
    setSelectedType(type)
  }

  // Handle completion of question session
  const handleQuestionComplete = () => {
    setSelectedType(null)
    setFilteredQuestions([])
    // Reload progress stats to show updated progress bars
    loadProgressStats()
  }

  useEffect(() => {
    loadPracticeQuestions()
    loadPracticeStatus()
  }, [])

  // Load progress stats after content questions are loaded
  useEffect(() => {
    if (contentQuestions.length > 0) {
      loadProgressStats()
    }
  }, [contentQuestions])

  // Polling for new questions (when questions might be generating)
  useEffect(() => {
    // Only start polling if we have very few or no questions
    const totalQuestions = contentQuestions.reduce((total, content) => total + content.questions.length, 0)
    const shouldPoll = contentQuestions.length === 0 || totalQuestions < 8

    if (shouldPoll) {
      // Starting polling for new practice questions
      
      const interval = setInterval(async () => {
        // Polling for new practice questions and status
        const previousTotal = contentQuestions.reduce((total, content) => total + content.questions.length, 0)
        const previousStatus = practiceStatus?.generation_status
        
        // Before polling status logged
        
        await loadPracticeQuestions()
        await loadPracticeStatus() // Also refresh status for smart messaging
        
        // After polling completed
        
        // Use a short delay to let React state update, then check changes
        setTimeout(() => {
          // Check current state after updates
          setContentQuestions(currentQuestions => {
            const currentTotal = currentQuestions.reduce((total, content) => total + content.questions.length, 0)
            if (currentTotal > previousTotal) {
              // New questions detected
            }
            return currentQuestions
          })
          
          setPracticeStatus(currentStatus => {
            if (currentStatus?.generation_status !== previousStatus) {
              // Status changed
            }
            return currentStatus
          })
        }, 1000)
      }, 10000) // Poll every 10 seconds for faster updates
      
      return () => {
        // Stopping polling for new practice questions
        clearInterval(interval)
      }
    }
  }, [contentQuestions.length])

  // If in question mode, show question interface
  if (selectedType && filteredQuestions.length > 0) {
    return (
      <QuestionInterface
        questions={filteredQuestions}
        questionType={selectedType}
        onBack={() => {
          setSelectedType(null)
          setFilteredQuestions([])
        }}
        onComplete={handleQuestionComplete}
        onProgressUpdate={loadProgressStats}  // Pass progress update function
      />
    )
  }

  // Main practice selection view
  return (
    <div className="min-h-full bg-app-bg">
      {/* Header */}
      <header className="grid grid-cols-3 items-center p-4 bg-card-bg shadow-sm">
        <button
          onClick={onBack}
          className="p-2 text-practice-green hover:text-practice-green-dark transition-colors"
        >
          <ArrowLeft className="w-6 h-6" />
        </button>
        
        <h1 className="text-xl font-semibold text-gray-800 text-center">Practice</h1>
        
        <div></div>
      </header>

      {/* Content */}
      <main className="p-6">
        {loading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-practice-green" />
          </div>
        ) : contentQuestions.length === 0 ? (
          // Empty state with smart messaging based on status
          <div className="text-center py-12">
            <div className={`w-16 h-16 mx-auto mb-6 rounded-2xl flex items-center justify-center ${
              practiceStatus?.generation_status === 'in_progress' 
                ? 'bg-gradient-to-br from-blue-500 to-indigo-600' 
                : 'bg-gradient-to-br from-practice-green to-practice-green-dark'
            }`}>
              {practiceStatus?.generation_status === 'in_progress' ? (
                <Loader2 className="w-8 h-8 text-white animate-spin" />
              ) : (
                <BookOpen className="w-8 h-8 text-white" />
              )}
            </div>
            <h2 className="text-xl font-bold text-gray-800 mb-3">
              {practiceStatus?.generation_status === 'in_progress' 
                ? 'Generating New Questions...' 
                : 'No Questions Available Yet'
              }
            </h2>
            <p className="text-gray-600 mb-6 max-w-md mx-auto">
              {practiceStatus?.message || 'Visit the Learn section first to explore some content. Practice questions are automatically generated when you read through topics for the first time!'}
            </p>
            {practiceStatus?.generation_status !== 'in_progress' && (
              <button
                onClick={() => onNavigate('learn')}
                className="bg-practice-green hover:bg-practice-green-dark text-white font-medium px-6 py-3 rounded-xl transition-colors duration-200 shadow-sm"
              >
                Go to Learn
              </button>
            )}
            {practiceStatus?.generation_status === 'in_progress' && (
              <div className="text-sm text-gray-500 mt-2">
                This may take a few minutes...
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            <div className="mb-6">
              <h2 className="text-2xl font-bold text-gray-800 mb-2">Choose Question Type</h2>
              <p className="text-gray-600">Practice what you've learned with different types of questions</p>
            </div>

            {/* Question type cards - ordered by difficulty (easiest to hardest) */}
            {['multiple_choice', 'fill_blank', 'short_answer', 'free_recall'].map((type) => {
              const colors = getQuestionTypeColor(type)
              const progressPercentage = getTypeProgress(type)
              const stats = questionStats[type]
              
              return (
                <div key={type} className="relative">
                  <button
                    onClick={() => handleTypeSelection(type)}
                    disabled={!stats || stats.total === 0}
                    className={`
                      w-full p-6 rounded-2xl shadow-sm transition-all duration-500 text-left relative overflow-hidden
                      ${stats && stats.total > 0
                        ? `bg-white hover:shadow-md hover:-translate-y-0.5 border ${colors.border} ${colors.hover}`
                        : 'bg-gray-50 border border-gray-200 cursor-not-allowed opacity-75'
                      }
                    `}
                  >
                    {/* Progress background */}
                    {stats && stats.total > 0 && stats.correct > 0 && (
                      <div 
                        className="absolute inset-0 rounded-2xl transition-all duration-1000 ease-out"
                        style={{
                          background: `linear-gradient(to right, ${colors.hexColor}, ${colors.hexColor}dd)`,
                          clipPath: `inset(0 ${100 - progressPercentage}% 0 0)`,
                          opacity: 0.8
                        }}
                      />
                    )}

                    {/* Base content layer */}
                    <div className="flex items-center justify-between relative z-10">
                      <div className="flex-1">
                        <h3 
                          className="font-semibold text-lg"
                          style={{ color: colors.hexColor }}
                        >
                          {getTypeDisplayName(type)}
                        </h3>
                      </div>

                      {/* Progress indicator */}
                      <div className="text-right">
                        {stats && stats.total > 0 ? (
                          <div 
                            className="text-2xl font-bold"
                            style={{ color: colors.hexColor }}
                          >
                            {stats.correct}/{stats.total}
                          </div>
                        ) : (
                          <div className="text-gray-400 text-lg">
                            0/0
                          </div>
                        )}
                      </div>
                    </div>

                    {/* White text masking layer - same coordinates as progress bar */}
                    {stats && stats.total > 0 && stats.correct > 0 && (
                      <div 
                        className="absolute inset-0 rounded-2xl transition-all duration-1000 ease-out z-20"
                        style={{
                          maskImage: `linear-gradient(to right, black 0%, black ${progressPercentage}%, transparent ${progressPercentage}%, transparent 100%)`,
                          WebkitMaskImage: `linear-gradient(to right, black 0%, black ${progressPercentage}%, transparent ${progressPercentage}%, transparent 100%)`
                        }}
                      >
                        <div className="p-6 flex items-center justify-between h-full">
                          <div className="flex-1">
                            <h3 className="font-semibold text-lg text-white">
                              {getTypeDisplayName(type)}
                            </h3>
                          </div>
                          <div className="text-right">
                            <div className="text-2xl font-bold text-white">
                              {stats.correct}/{stats.total}
                            </div>
                          </div>
                        </div>
                      </div>
                    )}
                  </button>
                </div>
              )
            })}
          </div>
        )}
      </main>
    </div>
  )
}

export default Practice