import { useState } from 'react'
import { ArrowLeft, CheckCircle2, XCircle, ArrowRight, Loader2 } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
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

interface QuestionInterfaceProps {
  questions: Question[]
  questionType: string
  onBack: () => void
  onComplete: () => void
  onProgressUpdate?: () => void  // New callback for progress updates
}

/**
 * QuestionInterface component provides interactive question-answering experience.
 * Supports multiple question types with AI evaluation and progress tracking.
 * 
 * Supported question types:
 * - Multiple choice with instant feedback
 * - True/false questions
 * - Fill in the blank
 * - Short answer with AI evaluation
 * - Free recall with AI evaluation
 * 
 * @param props - Component props
 * @param props.questions - Array of questions to display
 * @param props.questionType - Type of questions for styling
 * @param props.onBack - Callback to go back to previous view
 * @param props.onComplete - Callback when all questions are completed
 * @param props.onProgressUpdate - Callback to update progress in parent
 */
const QuestionInterface = ({ questions, questionType, onBack, onComplete, onProgressUpdate }: QuestionInterfaceProps) => {
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0)
  const [userAnswer, setUserAnswer] = useState('')
  const [selectedOption, setSelectedOption] = useState('')
  const [showFeedback, setShowFeedback] = useState(false)
  const [isCorrect, setIsCorrect] = useState(false)
  const [answeredCorrectly, setAnsweredCorrectly] = useState<boolean[]>([])
  const [isEvaluating, setIsEvaluating] = useState(false)
  const [aiFeedback, setAiFeedback] = useState('')

  const currentQuestion = questions[currentQuestionIndex]
  const isLastQuestion = currentQuestionIndex === questions.length - 1

  // Get question type colors
  const getQuestionTypeColor = (type: string) => {
    const colors = {
      'multiple_choice': { primary: '#16a34a', secondary: '#15803d' },
      'fill_blank': { primary: '#2563eb', secondary: '#1d4ed8' },
      'short_answer': { primary: '#7c3aed', secondary: '#6d28d9' },
      'free_recall': { primary: '#ea580c', secondary: '#c2410c' }
    }
    return colors[type] || colors['multiple_choice']
  }

  const colors = getQuestionTypeColor(questionType)

  // Markdown component configuration (reused from Learn component)
  const markdownComponents = {
    p: ({children}) => <p className="mb-4">{children}</p>,
    strong: ({children}) => <strong className="font-bold text-gray-900">{children}</strong>,
    em: ({children}) => <em className="italic text-gray-600">{children}</em>,
    code: ({children}) => <code className="bg-gray-100 px-2 py-1 rounded text-sm font-mono text-gray-800">{children}</code>,
    h1: ({children}) => <h1 className="text-2xl font-bold mb-4 mt-6 text-gray-900">{children}</h1>,
    h2: ({children}) => <h2 className="text-xl font-semibold mb-3 mt-5 text-gray-900">{children}</h2>,
    h3: ({children}) => <h3 className="text-lg font-medium mb-2 mt-4 text-gray-900">{children}</h3>,
    ul: ({children}) => <ul className="list-disc pl-6 mb-4 space-y-1">{children}</ul>,
    ol: ({children}) => <ol className="list-decimal pl-6 mb-4 space-y-1">{children}</ol>,
    li: ({children}) => <li className="text-gray-700">{children}</li>,
    blockquote: ({children}) => <blockquote className="border-l-4 border-gray-300 pl-4 py-2 mb-4 bg-gray-50 rounded text-gray-700">{children}</blockquote>
  }

  // Send answer to backend for multiple choice/true false
  const recordAnswer = async (isCorrect: boolean, answer: string) => {
    try {
      const response = await fetch(`${API_BASE}/api/practice/answer`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          questionId: currentQuestion.id,
          isCorrect,
          questionType: currentQuestion.type,
          contentId: currentQuestion.contentId,
          userAnswer: answer
        })
      })
      
      if (response.ok) {
        const result = await response.json()
        // Answer recorded with score
        
        // Trigger progress update in parent component
        if (onProgressUpdate) {
          onProgressUpdate()
        }
      }
    } catch (error) {
      // Error recording answer
    }
  }

  // Handle answer submission
  const handleSubmit = async () => {
    setIsEvaluating(true)
    setAiFeedback('')
    
    const answer = currentQuestion.type === 'multiple_choice' ? selectedOption : userAnswer.trim()
    let correct = false
    
    // For multiple choice and true/false, evaluate locally
    if (currentQuestion.type === 'multiple_choice' || currentQuestion.type === 'true_false') {
      correct = selectedOption === currentQuestion.answer
      setIsCorrect(correct)
      setShowFeedback(true)
      setIsEvaluating(false)
      
      // Record answer in backend
      await recordAnswer(correct, answer)
    } else {
      // For open-ended questions, let the backend/AI evaluate
      try {
        const response = await fetch(`${API_BASE}/api/practice/answer`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            questionId: currentQuestion.id,
            isCorrect: false, // Will be overridden by AI evaluation
            questionType: currentQuestion.type,
            contentId: currentQuestion.contentId,
            userAnswer: answer
          })
        })
        
        if (response.ok) {
          const result = await response.json()
          correct = result.isCorrect
          setIsCorrect(correct)
          
          // Set AI feedback if available
          if (result.feedback && result.evaluationMethod === 'ai') {
            setAiFeedback(result.feedback)
          }
          
          // AI evaluation completed
          
          // Trigger progress update in parent component
          if (onProgressUpdate) {
            onProgressUpdate()
          }
        } else {
          // Failed to submit answer
          // Fallback to local evaluation
          correct = answer.toLowerCase() === currentQuestion.answer.toLowerCase()
          setIsCorrect(correct)
        }
      } catch (error) {
        // Error submitting answer
        // Fallback to local evaluation
        correct = answer.toLowerCase() === currentQuestion.answer.toLowerCase()
        setIsCorrect(correct)
      }
      
      setShowFeedback(true)
      setIsEvaluating(false)
    }
    
    // Update answered correctly array
    const newAnsweredCorrectly = [...answeredCorrectly]
    newAnsweredCorrectly[currentQuestionIndex] = correct
    setAnsweredCorrectly(newAnsweredCorrectly)
  }

  // Handle next question
  const handleNext = () => {
    if (isLastQuestion) {
      onComplete()
    } else {
      setCurrentQuestionIndex(currentQuestionIndex + 1)
      setUserAnswer('')
      setSelectedOption('')
      setShowFeedback(false)
      setIsCorrect(false)
      setIsEvaluating(false)
      setAiFeedback('')
    }
  }

  // Render multiple choice options
  const renderMultipleChoice = () => (
    <div className="space-y-3">
      {currentQuestion.options?.map((option, index) => (
        <button
          key={index}
          onClick={() => setSelectedOption(option)}
          disabled={showFeedback}
          className={`
            w-full p-4 text-left rounded-xl border-2 transition-all duration-200
            ${showFeedback
              ? option === currentQuestion.answer
                ? 'border-green-500 bg-green-50 text-green-800'
                : option === selectedOption && option !== currentQuestion.answer
                ? 'border-red-500 bg-red-50 text-red-800'
                : 'border-gray-200 bg-gray-50 text-gray-600'
              : selectedOption === option
              ? `border-[${colors.primary}] bg-blue-50`
              : 'border-gray-200 hover:border-gray-300 bg-white hover:bg-gray-50'
            }
          `}
        >
          <div className="flex items-center space-x-3">
            <div 
              className={`
                w-6 h-6 rounded-full border-2 flex items-center justify-center
                ${showFeedback
                  ? option === currentQuestion.answer
                    ? 'border-green-500 bg-green-500'
                    : option === selectedOption && option !== currentQuestion.answer
                    ? 'border-red-500 bg-red-500'
                    : 'border-gray-300'
                  : selectedOption === option
                  ? `border-[${colors.primary}] bg-[${colors.primary}]`
                  : 'border-gray-300'
                }
              `}
            >
              {showFeedback && option === currentQuestion.answer && (
                <CheckCircle2 className="w-4 h-4 text-white" />
              )}
              {showFeedback && option === selectedOption && option !== currentQuestion.answer && (
                <XCircle className="w-4 h-4 text-white" />
              )}
              {!showFeedback && selectedOption === option && (
                <div className="w-2 h-2 rounded-full bg-white" />
              )}
            </div>
            <div className="font-medium">
              <ReactMarkdown components={markdownComponents}>
                {option}
              </ReactMarkdown>
            </div>
          </div>
        </button>
      ))}
    </div>
  )

  // Render text input for other question types
  const renderTextInput = () => (
    <div className="space-y-4">
      <textarea
        value={userAnswer}
        onChange={(e) => setUserAnswer(e.target.value)}
        disabled={showFeedback}
        placeholder={
          currentQuestion.type === 'fill_blank' 
            ? 'Complete the sentence...'
            : currentQuestion.type === 'short_answer'
            ? 'Write a concise answer...'
            : 'Explain in your own words...'
        }
        className={`
          w-full p-4 border-2 rounded-xl resize-none transition-all duration-200
          ${currentQuestion.type === 'free_recall' ? 'h-32' : 'h-20'}
          ${showFeedback 
            ? isCorrect 
              ? 'border-green-500 bg-green-50' 
              : 'border-red-500 bg-red-50'
            : 'border-gray-200 focus:border-blue-500 focus:outline-none'
          }
        `}
      />
      
      {isEvaluating && (
        <div className="p-4 rounded-xl bg-blue-50 border border-blue-200">
          <div className="flex items-center space-x-2">
            <Loader2 className="w-5 h-5 animate-spin text-blue-600" />
            <span className="font-semibold text-blue-800">
              Evaluating your answer...
            </span>
          </div>
        </div>
      )}
      
      {showFeedback && !isEvaluating && (
        <div className={`p-4 rounded-xl ${isCorrect ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
          <div className="flex items-center space-x-2 mb-2">
            {isCorrect ? (
              <CheckCircle2 className="w-5 h-5 text-green-600" />
            ) : (
              <XCircle className="w-5 h-5 text-red-600" />
            )}
            <span className={`font-semibold ${isCorrect ? 'text-green-800' : 'text-red-800'}`}>
              {isCorrect ? 'Correct!' : 'Not quite right'}
            </span>
          </div>
          
          {/* Show AI feedback if available */}
          {aiFeedback && (
            <div className="text-gray-700 mb-2">
              <ReactMarkdown components={markdownComponents}>
                {aiFeedback}
              </ReactMarkdown>
            </div>
          )}
          
          {/* Show expected answer only if no AI feedback and answer is incorrect */}
          {!isCorrect && !aiFeedback && (
            <div className="text-gray-700 mb-2">
              <strong>Expected answer:</strong>
              <ReactMarkdown components={markdownComponents}>
                {currentQuestion.answer}
              </ReactMarkdown>
            </div>
          )}
          
          {/* Show explanation if available */}
          {currentQuestion.explanation && (
            <div className="text-gray-700">
              <strong>Explanation:</strong>
              <ReactMarkdown components={markdownComponents}>
                {currentQuestion.explanation}
              </ReactMarkdown>
            </div>
          )}
        </div>
      )}
    </div>
  )

  return (
    <div className="min-h-full bg-app-bg">
      {/* Header */}
      <div className="p-4">
        <div 
          className="rounded-2xl shadow-sm p-4 relative overflow-hidden"
          style={{
            background: `linear-gradient(to right, ${colors.primary}, ${colors.secondary})`
          }}
        >
          <div className="flex items-center justify-between relative z-10">
            <button
              onClick={onBack}
              className="p-2 rounded-xl bg-white/20 hover:bg-white/30 transition-all duration-300"
            >
              <ArrowLeft className="w-6 h-6 text-white" />
            </button>
            
            <div className="text-sm font-semibold text-white">
              Question {currentQuestionIndex + 1} of {questions.length}
            </div>
          </div>

          {/* Progress bar */}
          <div className="mt-4 bg-white/20 rounded-full h-2">
            <div 
              className="bg-white h-2 rounded-full transition-all duration-500"
              style={{ width: `${((currentQuestionIndex + 1) / questions.length) * 100}%` }}
            />
          </div>
        </div>
      </div>

      {/* Question content */}
      <main className="px-4 pb-4">
        <div className="bg-white rounded-2xl shadow-sm p-6 border border-gray-200 mb-6">
          <div className="text-xl font-bold text-gray-800 mb-6">
            <ReactMarkdown components={markdownComponents}>
              {currentQuestion.question}
            </ReactMarkdown>
          </div>
          
          {currentQuestion.type === 'multiple_choice' ? renderMultipleChoice() : renderTextInput()}
        </div>

        {/* Action buttons */}
        <div className="flex justify-between items-center">
          <div className="text-sm text-gray-500">
            {questionType.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())} Question
          </div>
          
          {!showFeedback ? (
            <button
              onClick={handleSubmit}
              disabled={isEvaluating || (currentQuestion.type === 'multiple_choice' ? !selectedOption : !userAnswer.trim())}
              className="px-6 py-3 text-white rounded-2xl shadow-sm hover:shadow-md disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-500 flex items-center space-x-2 font-medium"
              style={{
                background: `linear-gradient(to right, ${colors.primary}, ${colors.secondary})`
              }}
            >
              {isEvaluating ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span>Evaluating...</span>
                </>
              ) : (
                <span>Submit Answer</span>
              )}
            </button>
          ) : (
            <button
              onClick={handleNext}
              className="px-6 py-3 text-white rounded-2xl shadow-sm hover:shadow-md transition-all duration-500 flex items-center space-x-2 font-medium"
              style={{
                background: `linear-gradient(to right, ${colors.primary}, ${colors.secondary})`
              }}
            >
              <span>{isLastQuestion ? 'Complete' : 'Next Question'}</span>
              <ArrowRight className="w-5 h-5" />
            </button>
          )}
        </div>
      </main>
    </div>
  )
}

export default QuestionInterface